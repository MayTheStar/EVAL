from fastapi import FastAPI, File, UploadFile, HTTPException
from pathlib import Path
from ai_engine.pdf_processing import parse_document
import uvicorn

app = FastAPI()

# Directory to store uploaded files
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.post("/upload_file")
async def upload_file(file: UploadFile = File(...)):
    # Ensure a file was uploaded
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    file_path = UPLOAD_DIR / file.filename

    # Save uploaded file
    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Process the PDF
    try:
        pages = parse_document(str(file_path))
        combined_text = " ".join(page["cleaned_text"] for page in pages)
        return {
            "filename": file.filename,
            "cleaned_text": combined_text,
            "pages": pages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse document: {str(e)}")

# Run the app
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
