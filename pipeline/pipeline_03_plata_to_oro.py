import pandas as pd
from pathlib import Path
import logging
from datetime import date, datetime
import csv


# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# Definir rutas para capas Bronce y Plata y Diccionario
BASE_DIR = Path(".").resolve()
PLATA_DIR = BASE_DIR / "data" / "plata"
ORO_DIR = BASE_DIR / "data" / "oro"
ORO_DIR.mkdir(parents=True, exist_ok=True)
marker_csv_oro = ORO_DIR / "procesados.csv"

# Procesamiento de archivos desde Plata a Oro
def procesar_oro():
    
    ## Carga de Datos

    # Archivos de entrada
    archivo_diario = PLATA_DIR / 'dataset_plata_diario_final.csv'
    archivo_horario = PLATA_DIR / 'dataset_plata_horario_final.csv'

    # Verificar existencia de archivos
    try:
        if not archivo_diario.exists() or not archivo_horario.exists():
            logger.warning("Faltan archivos en Plata. Diario: %s | Horario: %s", archivo_diario.exists(), archivo_horario.exists())
            return

    ## Generación de Variables Derivadas

        # Lectura de datasets
        df_diario = pd.read_csv(archivo_diario, parse_dates=['FECHA'])
        df_horario = pd.read_csv(archivo_horario, parse_dates=['FECHA_HORA'])

        # Variables derivadas diarias
        df_diario['AMP_TERMICA'] = df_diario['TEMP_MAX'] - df_diario['TEMP_MIN']
        df_diario['RANGO_PRESION'] = df_diario['PNM_MAX'] - df_diario['PNM_MIN']
        df_diario['RANGO_HUMEDAD'] = df_diario['HUM_MAX'] - df_diario['HUM_MIN']

        # Redondeo a 1 decimal para consistencia
        cols_derivadas = ['AMP_TERMICA', 'RANGO_PRESION', 'RANGO_HUMEDAD']
        df_diario[cols_derivadas] = df_diario[cols_derivadas].round(1)


        ## Exportación de la Capa Oro

        # Exportación a CSV
        df_diario.to_csv(ORO_DIR / 'dataset_oro_diario.csv', index=False)
        df_horario.to_csv(ORO_DIR / 'dataset_oro_horario.csv', index=False) 
        
        # Rango/filas desde los DataFrames en memoria (ya leídos arriba)
        # Diario Oro (usa FECHA)
        o_d_fecha_min = pd.to_datetime(df_diario["FECHA"]).min()
        o_d_fecha_max = pd.to_datetime(df_diario["FECHA"]).max()
        o_d_rows = int(len(df_diario))

        # Horario Oro (usa FECHA_HORA)
        o_h_fecha_hora_min = pd.to_datetime(df_horario["FECHA_HORA"]).min()
        o_h_fecha_hora_max = pd.to_datetime(df_horario["FECHA_HORA"]).max()
        o_h_rows = int(len(df_horario))

        # Mismo timestamp para ambas filas (una por dataset)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        header = ["timestamp", "dataset", "start", "end", "rows"]
        rows = [
            [ts, "oro_diario",
             o_d_fecha_min.isoformat() if pd.notna(o_d_fecha_min) else None,
             o_d_fecha_max.isoformat() if pd.notna(o_d_fecha_max) else None,
             o_d_rows],
            [ts, "oro_horario",
             o_h_fecha_hora_min.isoformat() if pd.notna(o_h_fecha_hora_min) else None,
             o_h_fecha_hora_max.isoformat() if pd.notna(o_h_fecha_hora_max) else None,
             o_h_rows],
        ]

        # Crear carpeta y escribir en modo append (NO atómico)
        marker_csv_oro.parent.mkdir(parents=True, exist_ok=True)
        write_header = not marker_csv_oro.exists() or marker_csv_oro.stat().st_size == 0
        with open(marker_csv_oro, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(header)
            w.writerows(rows)

        logger.info(
            "📝 Marker de Oro → %s | Diario %s→%s (%s filas), Horario %s→%s (%s filas)",
            marker_csv_oro,
            o_d_fecha_min.date() if pd.notna(o_d_fecha_min) else "NA",
            o_d_fecha_max.date() if pd.notna(o_d_fecha_max) else "NA", o_d_rows,
            o_h_fecha_hora_min, o_h_fecha_hora_max, o_h_rows
        )
    
    except Exception as e:
        logger.exception("❌ Error en procesar_oro: %s", e)
    
if __name__ == "__main__":
    procesar_oro()
