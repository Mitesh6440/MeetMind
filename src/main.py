from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from services.audio_handler import save_audio_file, AudioValidationError
from services.audio_preprocessing import preprocess_audio_file, AudioPreprocessingError


app = FastAPI(
    title="MeetMind - Meeting Task Assignment",
    version="0.1.0",
    description="API to upload meeting audio and process it step by step.",
)

# Base path for uploads: <project_root>/data/uploads
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
PROCESSED_DIR = UPLOAD_DIR / "processed"

@app.get("/")
def root():
    return {"message": "MeetMind API is running"}

@app.post("/api/v1/audio/upload")
async def upload_audio(file: UploadFile = File(...)):
    """
    Accept an uploaded audio file, validate it, and save it,
    and run preprocessing (normalization + basic noise reduction + conversion).
    """
    try:
        # 1. Read file bytes from UploadFile
        file_bytes = await file.read()

        # 2. Validate + save using our audio handler
        saved_path = save_audio_file(
            original_filename=file.filename,
            file_bytes=file_bytes,
            upload_dir=UPLOAD_DIR,
        )

        # 3. Preprocess audio (normalize, noise reduce, convert to wav 16k mono)
        processed_path = preprocess_audio_file(
            input_path=saved_path,
            output_dir=PROCESSED_DIR,
            enable_noise_reduction=True,   
        )

        # 4. Return info (later we'll feed processed_path to STT module)
        return {
            "message": "Audio uploaded and preprocessed successfully",
            "original_filename": file.filename,
            "saved_path": str(saved_path),
            "processed_path": str(processed_path),
        }

    except AudioValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AudioPreprocessingError as e:
        raise HTTPException(status_code=500, detail=f"Preprocessing error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")