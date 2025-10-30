

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any

import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from docx import Document
import docx2txt
from ai_engine.LLMSecDetector import detect_sections_with_llm
# ----------------------------
# UTILITY FUNCTIONS
# ----------------------------


#-------------------------------------
#check if pdf is scanned and apply OCR if needed
#-------------------------------------
def is_scanned_pdf(file_path: str) -> bool:

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                return False
    return True



#-------------------------------------
#extract scanned PDF using OCR
#-------------------------------------
def ocr_pdf(file_path: str) -> List[str]:

    pages_text = []
    images = convert_from_path(file_path)
    for idx, img in enumerate(images):
        text = pytesseract.image_to_string(img)
        pages_text.append(text)
    return pages_text


#-------------------------------------
#clean text 
#-------------------------------------
def clean_text(text: str) -> str:

    text = text.replace("\n", " ")
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


# ----------------------------
# PDF PARSER
# ----------------------------

def extract_pdf(file_path: str) -> List[Dict[str, Any]]:

    pages_data = []

    if is_scanned_pdf(file_path):
        ocr_texts = ocr_pdf(file_path)
        for idx, txt in enumerate(ocr_texts):
            pages_data.append({
                "page_number": idx + 1,
                "text": txt,
                "tables": []
            })
        return pages_data

    # For digital PDFs
    pdf_doc = fitz.open(file_path)
    with pdfplumber.open(file_path) as pdf:
        for idx, page in enumerate(pdf.pages):
            # Extract text
            text = page.extract_text() or ""
            
            # Extract tables
            tables = page.extract_tables()
            structured_tables = []
            for tidx, table in enumerate(tables):
                structured_tables.append({
                    "table_index": tidx + 1,
                    "rows": len(table),
                    "columns": len(table[0]) if table else 0,
                    "data": table
                })

            pages_data.append({
                "page_number": idx + 1,
                "text": text,
                "tables": structured_tables
            })

    return pages_data


# ----------------------------
# DOCX / DOC PARSER
# ----------------------------

def extract_docx(file_path: str) -> List[Dict[str, Any]]:
    doc = Document(file_path)
    pages_data = []

    text_content = "\n".join([p.text for p in doc.paragraphs])
    tables_content = []
    for t_idx, table in enumerate(doc.tables):
        table_rows = [[cell.text for cell in row.cells] for row in table.rows]
        tables_content.append({
            "table_index": t_idx + 1,
            "rows": len(table_rows),
            "columns": len(table_rows[0]) if table_rows else 0,
            "data": table_rows
        })

    pages_data.append({
        "page_number": 1,
        "text": text_content,
        "tables": tables_content
    })
    return pages_data


def extract_doc(file_path: str) -> List[Dict[str, Any]]:
    text = docx2txt.process(file_path)
    return [{
        "page_number": 1,
        "text": text,
        "tables": []
    }]


# ----------------------------
# CLEANING / NORMALIZATION
# ----------------------------

def clean_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned = []
    for page in pages:
        cleaned.append({
            "page_number": page["page_number"],
            "cleaned_text": clean_text(page["text"]),
            "tables": page.get("tables", [])
        })
    return cleaned


# ----------------------------
# PIPELINE 
# ----------------------------

def parse_document(file_path: str) -> List[Dict[str, Any]]:
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        pages = extract_pdf(file_path)
    elif ext == ".docx":
        pages = extract_docx(file_path)
    elif ext == ".doc":
        pages = extract_doc(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    cleaned_pages = clean_pages(pages)
    return cleaned_pages


# ----------------------------
# SAVE  OUTPUT
# ----------------------------

def save_json(data: List[Dict[str, Any]], output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ----------------------------
# MAIN
# ----------------------------

if __name__ == "__main__":
    FILE_PATH = "/Users/rayana/EVAL/ai_engine/CalRFPexample.pdf"
    OUTPUT_JSON = "rfp_preprocessed.json"
    OUTPUT_SECTIONS = "rfp_sections.json"

    # Parse document and save preprocessed output
    processed_pages = parse_document(FILE_PATH)
    save_json(processed_pages, OUTPUT_JSON)

    # Detect sections using LLM
    sections = detect_sections_with_llm(processed_pages)

    # Save sectioned output
    save_json(sections, OUTPUT_SECTIONS)

    print(f"LLM-based section detection saved to: {OUTPUT_SECTIONS}")
