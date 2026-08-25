import os
import uuid
from pathlib import Path

import time

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import aiofiles

from detector import load_model, process_video

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
PROCESSED_DIR = BASE_DIR / "static" / "processed"

UPLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

FILE_EXPIRY_SECONDS = 60 * 60
CLEANUP_INTERVAL = 10 * 60

def cleanup_old_files():
    now = time.time()

    for folder in [UPLOAD_DIR, PROCESSED_DIR]:
        for file in folder.iterdir():

            if not file.is_file():
                continue
            age = now - file.stat().st_mtime

            if age > FILE_EXPIRY_SECONDS:
                try:
                    file.unlink()
                    print(f"Deleted old file: {file.name}")
                except Exception as e:
                    print(f"Coult not delete {file}: {e}")

app = FastAPI(title="People Detector")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

model = load_model("yolov8n.pt")

@app.get("/")
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request":request})

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):

    cleanup_old_files()

    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Only Video files are accepted.")
    
    ext = Path(file.filename).suffix or ".mp4"

    filename = f"{uuid.uuid4().hex}{ext}"
    save_path = UPLOAD_DIR / filename

    async with aiofiles.open(save_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)
    
    return {"filename": filename}

@app.post("/process/{filename}")
async def process(filename: str):

    input_path = UPLOAD_DIR / filename
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded file not found.")
    
    output_name = f"processed_{filename}"
    output_name = Path(output_name).stem + ".mp4"
    output_path = PROCESSED_DIR / output_name

    try:
        max_count = process_video(model, str(input_path), str(output_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "processed_url" : f"/static/processed/{output_name}",
        "max_people" : max_count,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app",host="127.0.0.1", port=8000, reload=True)