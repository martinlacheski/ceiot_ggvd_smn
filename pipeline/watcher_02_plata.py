import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pipeline_02_bronce_to_plata import procesar_exploracion_plata, procesar_enriquecimiento_plata

# Configurar logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# Directorio a observar (data/bronce)
BRONCE_DIR = Path("data") / "bronce"
PLATA_DIR = Path("data") / "plata"
PROCESADOS_CSV = BRONCE_DIR / "procesados.csv"

class BronceWatcherHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return

        if "procesados.csv" in event.src_path:
            logger.info("🔄 Se modificó procesados.csv. Ejecutando procesamiento de Plata...")

            procesar_exploracion_plata()

            # Verificar que dataset_plata_inicial.csv exista y no esté vacío
            archivo_plata = PLATA_DIR / "dataset_plata_inicial.csv"
            if not archivo_plata.exists() or archivo_plata.stat().st_size == 0:
                logger.warning("⚠️ El archivo diario aún no está disponible o está vacío")
                return

            procesar_enriquecimiento_plata()
            logger.info("✅ Procesamiento de Plata completado.")

if __name__ == "__main__":
    observer = Observer()
    observer.schedule(BronceWatcherHandler(), str(PROCESADOS_CSV), recursive=True)
    observer.start()
    logger.info(f"👂 Watcher de Plata escuchando en: {BRONCE_DIR}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
