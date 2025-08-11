# api/main.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
import logging
import os
import asyncpg
import asyncio
import re
import pandas as pd
from dateutil import tz

app = FastAPI()

UPLOAD_DIR = Path("data/raw/datohorario")
SIMULATE_DIR = Path("data/raw/simulate")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SIMULATE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# --- Config ---
provincia_env = os.getenv("PROVINCIA_OBJETIVO")
if not provincia_env:
    raise RuntimeError("❌ La variable de entorno PROVINCIA_OBJETIVO no está definida")
PROVINCIA_OBJETIVO = provincia_env.strip()

BASE_DIR = Path(".").resolve()
RAW_DIR = BASE_DIR / "data" / "raw"
ESTACIONES_FILE = RAW_DIR / "estaciones" / "estaciones_smn.txt"
LOCAL_TZ = tz.gettz("America/Argentina/Buenos_Aires")
SIM_DELAY_MS = 250

# --- Funciones utilitarias ---
def cargar_estaciones_provincia(provincia):
    with open(ESTACIONES_FILE, "r", encoding="latin1") as f:
        lines = f.readlines()[2:]  # omite encabezados

    pattern = re.compile(
        r"^(?P<nombre>.+?)\s{2,}(?P<provincia>.+?)\s{2,}(?P<lat_gr>-?\d+)\s+(?P<lat_min>\d+)\s+(?P<lon_gr>-?\d+)\s+(?P<lon_min>\d+)\s+(?P<altura_m>\d+)\s+(?P<numero>\d+)\s+(?P<numero_oaci>\S+)\s*$"
    )

    data = [match.groupdict() for line in lines if (match := pattern.match(line))]
    df = pd.DataFrame(data)
    df['provincia'] = df['provincia'].str.strip().str.upper()
    return df[df['provincia'] == provincia.upper()]['nombre'].str.strip().unique()

def leer_y_filtrar_datohorario(archivo_txt: Path, provincia_objetivo: str) -> pd.DataFrame:
    estaciones_prov = cargar_estaciones_provincia(provincia_objetivo)
    logger.info(f"📍 Estaciones en {provincia_objetivo} ({len(estaciones_prov)}): {list(estaciones_prov)}")

    with open(archivo_txt, "r", encoding="latin1") as f:
        lines = f.readlines()

    columnas = re.split(r"\s{2,}", lines[0].strip())
    data = [
        re.split(r"\s{2,}", line.strip(), maxsplit=len(columnas)-1)
        for line in lines[2:]  # omite encabezado + unidades
        if len(line.strip()) > 0 and not line.isspace()
    ]

    df = pd.DataFrame(data, columns=columnas)
    df.columns = df.columns.str.strip()
    df["NOMBRE"] = df["NOMBRE"].str.strip()

    # Filtrar por estaciones de la provincia
    nombres_provincia = set(estaciones_prov)
    df = df[df["NOMBRE"].isin(nombres_provincia)]

    # Datetime: DDMMYYYY + HH (zero-pad)
    df["fecha_hora"] = pd.to_datetime(
        df["FECHA"].astype(str) + df["HORA"].astype(str).str.zfill(2),
        format="%d%m%Y%H",
        errors="coerce",
    )

    # Renombrar a nombres de columnas de la tabla
    df.rename(
        columns={
            "NOMBRE": "estacion_nombre",
            "TEMP": "temp_c",
            "HUM": "hum_pct",
            "PNM": "pnm_hpa",
            "DD": "wind_dir_deg",
            "FF": "wind_speed_kmh",
        },
        inplace=True,
    )

    # ---- Tipar numéricos ----
    for c in ["temp_c", "hum_pct", "pnm_hpa", "wind_dir_deg", "wind_speed_kmh"]:
        df[c] = (
            df[c]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .pipe(pd.to_numeric, errors="coerce")
        )

    # Quitar filas sin fecha válida
    df = df[df["fecha_hora"].notna()]

    return df[
        [
            "estacion_nombre",
            "fecha_hora",
            "temp_c",
            "hum_pct",
            "pnm_hpa",
            "wind_dir_deg",
            "wind_speed_kmh",
        ]
    ]
    
async def insertar_uno_a_uno_async(df: pd.DataFrame, delay_ms: int = 250, limit: int = 0) -> dict:
    total = len(df) if limit <= 0 else min(limit, len(df))
    insertados = 0
    omitidos = 0
    delay_s = max(0, delay_ms) / 1000.0

    logger.info(f"📡 Conectando a PostgreSQL en {os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}...")
    conn = await asyncpg.connect(
        host=os.getenv("PG_HOST"),
        port=int(os.getenv("PG_PORT")),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        database=os.getenv("PG_DB")
    )
    logger.info(f"✅ Conectado. Insertando {total} registros...")

    sql_insert = """
        INSERT INTO smn_obs (
          estacion_nombre, fecha_hora, temp_c, hum_pct, pnm_hpa, wind_dir_deg, wind_speed_kmh
        ) VALUES (
          $1, $2, $3, $4, $5, $6, $7
        )
        ON CONFLICT (estacion_nombre, fecha_hora) DO NOTHING
    """

    try:
        count = 0
        for _, r in df.iterrows():
            try:
                result = await conn.execute(
                    sql_insert,
                    r["estacion_nombre"],
                    r["fecha_hora"].to_pydatetime(),
                    r.get("temp_c"),
                    r.get("hum_pct"),
                    r.get("pnm_hpa"),
                    r.get("wind_dir_deg"),
                    r.get("wind_speed_kmh")
                )

                # Mensaje detallado por registro
                detalle = (
                    f"🕒 {r['fecha_hora']} | "
                    f"📍 {r['estacion_nombre']} | "
                    f"🌡️ Temp: {r.get('temp_c')}°C | "
                    f"💧 Hum: {r.get('hum_pct')}% | "
                    f"🌬️  Presión: {r.get('pnm_hpa')} hPa | "
                    f"🧭 Dir. viento: {r.get('wind_dir_deg')}° | "
                    f"💨 Vel. viento: {r.get('wind_speed_kmh')} km/h"
                )

                if result and result.startswith("INSERT"):
                    insertados += 1
                    logger.info(f"✅ Insertado → {detalle}")
                else:
                    omitidos += 1
                    logger.info(f"⚠️ Omitido (duplicado/conflicto) → {detalle}")

            except Exception as ex:
                logger.error(f"❌ Error insertando → {detalle} | Error: {ex}")
                omitidos += 1

            count += 1
            if count >= total:
                break

            if delay_s > 0:
                await asyncio.sleep(delay_s)

    finally:
        await conn.close()
        logger.info("🔌 Conexión cerrada.")

    logger.info(f"📊 Resumen final → Procesadas: {total} | Insertadas: {insertados} | Omitidas: {omitidos}")
    return {
        "procesados": total,
        "insertados": insertados,
        "omitidos": omitidos,
        "delay_ms": delay_ms
    }


# --- Endpoints ---
@app.on_event("startup")
async def startup_event():
    logger.info("✅ API iniciada correctamente")
    logger.info("📥 Upload de dato horario: POST /upload/")
    logger.info("⏱️  Simulación tiempo real: POST /simulate/")

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = UPLOAD_DIR / file.filename
        if file_path.exists():
            logger.info(f"⏩ Archivo ya existe, se ignora: {file.filename}")
            return JSONResponse(content={"message": f"Archivo '{file.filename}' ya existe y no fue sobrescrito."})

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"✅ Archivo recibido: {file.filename}")
        return JSONResponse(content={"message": f"Archivo '{file.filename}' subido correctamente."})
    except Exception as e:
        logger.error(f"❌ Error al subir el archivo '{file.filename}': {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/simulate/")
async def simulate_datohorario(file: UploadFile = File(...)):
    tmp_path = SIMULATE_DIR / file.filename
    logger.info(f"📥 Archivo de dato horario recibido: {file.filename}")
    with open(tmp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    logger.info(f"📂 Archivo guardado temporalmente en: {tmp_path}")
    
    df = leer_y_filtrar_datohorario(tmp_path, PROVINCIA_OBJETIVO)
    logger.info(f"📊 Datos procesados: {len(df)} filas")
    df.sort_values("fecha_hora", inplace=True)

    logger.info("⏳ Iniciando inserción en la base de datos...")
    result = await insertar_uno_a_uno_async(df, delay_ms=SIM_DELAY_MS, limit=0)

    tmp_path.unlink(missing_ok=True)
    return JSONResponse(content=result)