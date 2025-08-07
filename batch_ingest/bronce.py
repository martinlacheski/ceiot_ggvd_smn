
import pandas as pd
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

def procesar_datohorario_txt(archivo_txt, salida_dir):
    salida_dir = Path(salida_dir)
    salida_dir.mkdir(parents=True, exist_ok=True)

    with open(archivo_txt, "r", encoding="latin1") as f:
        lines = f.readlines()

    columnas = re.split(r"\s{2,}", lines[0].strip())
    data = [
        re.split(r"\s{2,}", line.strip(), maxsplit=len(columnas)-1)
        for line in lines[1:]
        if len(line.strip()) > 0 and not line.isspace()
    ]

    df = pd.DataFrame(data, columns=columnas)

    nombre_archivo = Path(archivo_txt).stem + ".csv"
    df.to_csv(salida_dir / nombre_archivo, index=False)
    logger.info(f"[BRONCE] Archivo procesado: {archivo_txt} -> {nombre_archivo}")
