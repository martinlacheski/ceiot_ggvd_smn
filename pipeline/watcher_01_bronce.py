from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import logging
import time
import csv
from datetime import datetime
from pipeline_01_ingest_to_bronce import procesar_datohorario_txt


# Configuración
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

RAW_DIR = Path("data/raw/datohorario")
PROCESADOS_CSV = Path("data/bronce/procesados.csv")
PROCESADOS_DIR = RAW_DIR / "_procesados"
PROCESADOS_DIR.mkdir(parents=True, exist_ok=True)

# Guardar registro con timestamp
def guardar_registro(nombre_archivo):
    PROCESADOS_CSV.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(PROCESADOS_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([nombre_archivo, timestamp])

# Handler
class TxtHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith(".txt"):
            return

        path = Path(event.src_path)
        nombre_archivo = path.name

        logger.info(f"🛰️  Nuevo archivo detectado: {nombre_archivo}")
        try:
            procesar_datohorario_txt(path, "data/bronce")
            guardar_registro(nombre_archivo)

            destino = PROCESADOS_DIR / nombre_archivo
            path.rename(destino)

            logger.info(f"📦 Archivo movido a _procesados: {destino}")
        except Exception as e:
            logger.error(f"❌ Error al procesar {nombre_archivo}: {e}")

# Inicialización
if __name__ == "__main__":
    observer = Observer()
    observer.schedule(TxtHandler(), path=str(RAW_DIR), recursive=False)
    observer.start()
    logger.info(f"👂 Watcher escuchando en: {RAW_DIR}")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
