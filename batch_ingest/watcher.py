from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import logging
import time
from bronce import procesar_datohorario_txt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

class TxtHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".txt"):
            path = Path(event.src_path)
            logger.info(f"🛰️  Nuevo archivo detectado: {path.name}")
            try:
                procesar_datohorario_txt(path, "data/bronce")
                # Mover a carpeta _procesados
                procesados = path.parent / "_procesados"
                procesados.mkdir(exist_ok=True)
                path.rename(procesados / path.name)
            except Exception as e:
                logger.info(f"❌ Error al procesar {path.name}: {e}")

if __name__ == "__main__":
    path = Path("data/raw/datohorario").resolve()
    observer = Observer()
    observer.schedule(TxtHandler(), path=str(path), recursive=False)
    observer.start()
    logger.info(f"👂 Escuchando cambios en {path} ...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
