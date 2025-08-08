import pandas as pd
from pathlib import Path
import logging
import csv
from datetime import datetime

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# Directorios
BASE_DIR = Path(".").resolve()
BRONCE_DIR = BASE_DIR / "data" / "bronce"
PLATA_DIR = BASE_DIR / "data" / "plata"
PLATA_DIR.mkdir(parents=True, exist_ok=True)

# Registro de archivos procesados
REGISTRO_CSV = PLATA_DIR / "procesados.csv"

# Columnas a convertir
COLUMNAS_NUMERICAS = ["TEMP", "HUM", "PNM", "DD", "FF"]

# Cargar archivos ya procesados
def cargar_procesados():
    if not REGISTRO_CSV.exists():
        return set()
    with open(REGISTRO_CSV, newline="") as f:
        return set(row[0] for row in csv.reader(f))

# Registrar nuevo archivo procesado
def registrar_procesado(nombre):
    with open(REGISTRO_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([nombre, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

# Procesamiento de archivos desde Bronce a Plata
def procesar_archivos():
    ya_procesados = cargar_procesados()
    df_total = pd.DataFrame()
    errores = 0

    for carpeta in BRONCE_DIR.iterdir():
        if not carpeta.is_dir():
            continue

        for archivo in carpeta.glob("*.csv"):
            nombre_relativo = f"{carpeta.name}/{archivo.name}"
            if nombre_relativo in ya_procesados:
                continue

            try:
                df = pd.read_csv(archivo)
                df.columns = df.columns.str.strip()
                df["ESTACION"] = carpeta.name.replace("_", " ").upper()

                fecha_archivo = archivo.stem  # formato: 20250601
                fecha_formateada = pd.to_datetime(fecha_archivo, format="%Y%m%d", errors="coerce")
                df["FECHA"] = fecha_formateada

                df_total = pd.concat([df_total, df], ignore_index=True)
                registrar_procesado(nombre_relativo)
            except Exception as e:
                logger.error(f"❌ Error al procesar {nombre_relativo}: {e}")
                errores += 1

    if df_total.empty:
        logger.warning("⚠️ No se procesaron nuevos archivos.")
        return

    df_total.columns = df_total.columns.str.strip()
    df_total = df_total.dropna(subset=["FECHA"])
    df_total["HORA"] = pd.to_numeric(df_total["HORA"], errors="coerce").astype("Int64")

    for col in COLUMNAS_NUMERICAS:
        if col in df_total.columns:
            df_total[col] = pd.to_numeric(df_total[col], errors="coerce")

    df_total.to_csv(PLATA_DIR / "dataset_plata_inicial.csv", index=False)

    df_total[df_total.isnull().any(axis=1)].to_csv(PLATA_DIR / "dataset_intermedio_horario_con_nan.csv", index=False)
    df_total.to_csv(PLATA_DIR / "dataset_intermedio_horario_completo.csv", index=False)

    df_ffill = df_total.sort_values(["ESTACION", "FECHA", "HORA"])
    df_ffill[COLUMNAS_NUMERICAS] = df_ffill.groupby("ESTACION")[COLUMNAS_NUMERICAS].ffill()
    df_ffill.to_csv(PLATA_DIR / "dataset_intermedio_horario_ffill.csv", index=False)
    df_ffill.to_csv(PLATA_DIR / "dataset_plata_horario_final.csv", index=False)

    # Agregaciones para valores diarios
    df_agg = (
        df_ffill.groupby(["ESTACION", df_ffill["FECHA"].dt.date])
        .agg(
            TEMP_MEAN=("TEMP", "mean"), TEMP_MIN=("TEMP", "min"), TEMP_MAX=("TEMP", "max"),
            PNM_MEAN=("PNM", "mean"), PNM_MIN=("PNM", "min"), PNM_MAX=("PNM", "max"),
            HUM_MEAN=("HUM", "mean"), HUM_MIN=("HUM", "min"), HUM_MAX=("HUM", "max"),
            WIND_DIR_MEAN=("DD", "mean"), WIND_DIR_MIN=("DD", "min"), WIND_DIR_MAX=("DD", "max"),
            WIND_SPEED_MEAN=("FF", "mean"), WIND_SPEED_MIN=("FF", "min"), WIND_SPEED_MAX=("FF", "max"),
        )
        .reset_index()
        .rename(columns={"FECHA": "DIA"})
    )

    # Redondeo
    df_agg = df_agg.round({
        "TEMP_MEAN": 1, "TEMP_MIN": 0, "TEMP_MAX": 0,
        "PNM_MEAN": 1, "PNM_MIN": 0, "PNM_MAX": 0,
        "HUM_MEAN": 1, "HUM_MIN": 0, "HUM_MAX": 0,
        "WIND_DIR_MEAN": 1, "WIND_DIR_MIN": 0, "WIND_DIR_MAX": 0,
        "WIND_SPEED_MEAN": 1, "WIND_SPEED_MIN": 0, "WIND_SPEED_MAX": 0,
    })

    # Normalización min-max por variable
    for col in ["TEMP_MEAN", "PNM_MEAN", "HUM_MEAN", "WIND_DIR_MEAN", "WIND_SPEED_MEAN"]:
        min_val = df_agg[col].min()
        max_val = df_agg[col].max()
        col_norm = col + "_NORM"
        df_agg[col_norm] = ((df_agg[col] - min_val) / (max_val - min_val)).round(5)

    df_agg.to_csv(PLATA_DIR / "dataset_plata_diario_final.csv", index=False)

    df_total[df_total["HORA"].isnull()].to_csv(PLATA_DIR / "registros_horarios_atipicos.csv", index=False)

    fechas_faltantes = []
    for nombre, grupo in df_ffill.groupby("ESTACION"):
        fechas = grupo["FECHA"].dt.date.unique()
        fechas_completas = pd.date_range(start=min(fechas), end=max(fechas), freq="D").date
        faltantes = sorted(set(fechas_completas) - set(fechas))
        for f in faltantes:
            fechas_faltantes.append({"estacion": nombre, "fecha_faltante": f})

    pd.DataFrame(fechas_faltantes).to_csv(PLATA_DIR / "fechas_faltantes.txt", index=False)
    df_total[["FECHA", "HORA", "ESTACION"]].to_csv(PLATA_DIR / "horario_archivo.csv", index=False)

    logger.info(f"✅ Exploración completa. Total registros: {len(df_total)} | Errores: {errores}")
    logger.info(f"📁 Archivos generados en: {PLATA_DIR}")

if __name__ == "__main__":
    procesar_archivos()
