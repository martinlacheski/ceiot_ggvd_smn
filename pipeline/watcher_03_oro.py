import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pipeline_03_plata_to_oro import procesar_oro

# Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# Rutas
PLATA_DIR    = Path("data") / "plata"
ORO_DIR      = Path("data") / "oro"
MARKER_CSV   = PLATA_DIR / "procesados.csv"
DIARIO_CSV   = PLATA_DIR / "dataset_plata_diario_final.csv"
HORARIO_CSV  = PLATA_DIR / "dataset_plata_horario_final.csv"

def _stable_and_nonempty(p: Path, min_bytes: int = 8, wait: float = 0.4) -> bool:
    # True si el archivo existe, no está vacío y su tamaño se mantiene entre dos lecturas.
    if not p.exists():
        return False
    s1 = p.stat().st_size
    if s1 < min_bytes:
        return False
    time.sleep(wait)
    s2 = p.stat().st_size
    return s1 == s2 and s2 >= min_bytes

def ready_to_process() -> bool:
    # Verifica existencia y finalización de procesamiento de los datos finales de Plata.
    ok = _stable_and_nonempty(DIARIO_CSV) and _stable_and_nonempty(HORARIO_CSV)
    if not ok:
        dsize = DIARIO_CSV.stat().st_size if DIARIO_CSV.exists() else "NA"
        hsize = HORARIO_CSV.stat().st_size if HORARIO_CSV.exists() else "NA"
        logger.warning("⏳ Esperando finalización en Plata. diario=%s | horario=%s", dsize, hsize)
    return ok

class PlataMarkerHandler(FileSystemEventHandler):
    def __init__(self, debounce_sec: float = 0.8):
        super().__init__()
        self.last_run_ts = 0.0
        self.debounce_sec = debounce_sec

    def _maybe_run(self, path: Path):
        # Solo reaccionar al marker exacto
        if path != MARKER_CSV:
            return

        # Debounce
        now = time.time()
        if (now - self.last_run_ts) < self.debounce_sec:
            return
        self.last_run_ts = now

        logger.info("🔔 Marker detectado: %s. Verificando archivos…", MARKER_CSV)

        # Reintento corto para estabilidad total (por si el marker se escribió 1ro)
        for _ in range(8):  # ~3–4s
            if ready_to_process():
                break
            time.sleep(0.5)
        else:
            logger.warning("⚠️ Archivos de Plata no listos. No se ejecuta Oro.")
            return

        try:
            logger.info("🚀 Ejecutando pipeline Oro…")
            procesar_oro()
            logger.info("✅ Procesamiento de Oro completado.")
        except Exception as e:
            logger.exception("❌ Error ejecutando procesar_oro: %s", e)

    def on_modified(self, event):
        if not event.is_directory:
            self._maybe_run(Path(event.src_path))

if __name__ == "__main__":
    PLATA_DIR.mkdir(parents=True, exist_ok=True)
    ORO_DIR.mkdir(parents=True, exist_ok=True)

    observer = Observer()
    # Observamos la carpeta, pero filtramos por el marker en el handler
    observer.schedule(PlataMarkerHandler(), str(PLATA_DIR), recursive=False)
    observer.start()
    logger.info("👂 Watcher de Oro escuchando en: %s", MARKER_CSV)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
