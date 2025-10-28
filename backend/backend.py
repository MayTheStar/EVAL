from fastapi import FastAPI, File, UploadFile
from pathlib import Path
from pdf_processing import parse_document  

app = FastAPI()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.post("/upload_file")
async def upload_file(file: UploadFile = File(...)):

    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(await file.read())

    
    try:
        extracted_pages = parse_document(str(file_path))
    except ValueError as e:
        return {"error": str(e)}

    
    combined_text = " ".join([page["cleaned_text"] for page in extracted_pages])

    return {"filename": file.filename, "cleaned_text": combined_text, "pages": extracted_pages}
