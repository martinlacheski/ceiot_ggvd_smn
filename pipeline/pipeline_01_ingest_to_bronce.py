import pandas as pd
import re
from pathlib import Path
import logging

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# Parámetros
PROVINCIA_OBJETIVO = "MISIONES" # Cambiar según PROVINCIA elegida
BASE_DIR = Path(".").resolve()
RAW_DIR = BASE_DIR / "data" / "raw"
BRONCE_DIR = BASE_DIR / "data" / "bronce"
ESTACIONES_FILE = RAW_DIR / "estaciones" / "estaciones_smn.txt"

# Crear carpetas si no existen
for path in [BRONCE_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Cargar estaciones de la provincia
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

# Procesar archivo datohorario filtrado por provincia
def procesar_datohorario_txt(archivo_txt, salida_base_dir):
    estaciones_prov = cargar_estaciones_provincia(PROVINCIA_OBJETIVO)
    logger.info(f"📍 Estaciones en {PROVINCIA_OBJETIVO} ({len(estaciones_prov)}): {list(estaciones_prov)}")

    with open(archivo_txt, "r", encoding="latin1") as f:
        lines = f.readlines()

    columnas = re.split(r"\s{2,}", lines[0].strip())
    data = [
        re.split(r"\s{2,}", line.strip(), maxsplit=len(columnas)-1)
        for line in lines[1:]
        if len(line.strip()) > 0 and not line.isspace()
    ]

    df = pd.DataFrame(data, columns=columnas)
    df.columns = df.columns.str.strip()
    df["NOMBRE"] = df["NOMBRE"].str.strip()

    nombres_provincia = set(estaciones_prov)
    df = df[df["NOMBRE"].isin(nombres_provincia)]

    fecha_str = Path(archivo_txt).stem.replace("datohorario", "")

    total_filas = 0
    errores = 0

    for nombre in nombres_provincia:
        df_estacion = df[df["NOMBRE"] == nombre]
        if df_estacion.empty:
            continue

        nombre_clean = nombre.lower().replace(" ", "_")
        path_estacion = Path(salida_base_dir) / nombre_clean
        path_estacion.mkdir(parents=True, exist_ok=True)

        archivo_csv = path_estacion / f"{fecha_str}.csv"
        try:
            df_estacion.to_csv(archivo_csv, index=False)
            total_filas += len(df_estacion)
        except Exception as e:
            errores += 1
            logger.error(f"❌ Error al guardar {archivo_csv}: {e}")

    logger.info(f"[BRONCE] Procesado: {archivo_txt} → {total_filas} filas para {PROVINCIA_OBJETIVO} | errores: {errores}")
