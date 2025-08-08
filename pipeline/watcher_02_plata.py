import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from pipeline_02_bronce_to_plata import procesar_archivos

# Configurar logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# Directorio a observar (data/bronce)
BRONCE_DIR = Path("data") / "bronce"

class BronceWatcherHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        logger.info("🔄 Cambio detectado en Bronce. Ejecutando procesamiento de Plata...")
        procesar_archivos()

if __name__ == "__main__":
    observer = Observer()
    observer.schedule(BronceWatcherHandler(), str(BRONCE_DIR), recursive=True)
    observer.start()
    logger.info(f"👂 Watcher de Plata escuchando en: {BRONCE_DIR}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()