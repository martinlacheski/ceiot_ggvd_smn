from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
import logging
app = FastAPI()

UPLOAD_DIR = Path("data/raw/datohorario")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

@app.on_event("startup")
async def startup_event():
    logger.info("✅ API iniciada correctamente")
    logger.info("📥 Endpoint para subir archivos: POST http://localhost:8000/upload/")

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

