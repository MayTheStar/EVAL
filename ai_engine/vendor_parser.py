import os
import json
from pathlib import Path
from parser import chunk_document, merge_small_chunks_forward, save_json
from transformers import AutoTokenizer
from docling.document_converter import DocumentConverter

# ----------------------------
# Configuration
# ----------------------------
VENDOR_FOLDER = Path("vendor_responses")
OUTPUT_FOLDER = Path("/Users/maybader/EVAL/ai_engine")
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

# ----------------------------
# Helper: Convert DOC/DOCX to PDF or Document object
# ----------------------------
def convert_to_docling_document(file_path: str):
    """Converts any supported document (PDF, DOC, DOCX) into a Docling Document."""
    converter = DocumentConverter()
    doc = converter.convert(file_path).document
    return doc

# ----------------------------
# Main vendor parsing function
# ----------------------------
def parse_vendor_responses():
    print("📦 Starting Vendor Response Parsing...")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    supported_formats = ["*.pdf", "*.doc", "*.docx"]

    # Collect all files (PDF/DOC/DOCX)
    vendor_files = []
    for pattern in supported_formats:
        vendor_files.extend(list(VENDOR_FOLDER.glob(pattern)))

    if not vendor_files:
        print("⚠️ No vendor files found in:", VENDOR_FOLDER)
        return

    # Process each vendor file
    for file_path in vendor_files:
        vendor_name = file_path.stem.replace("_", " ").title().strip()
        print(f"\n🔹 Processing vendor: {vendor_name} ({file_path.suffix})")

        try:
            # Step 1: Use the same logic as RFP parsing
            chunks, _ = chunk_document(str(file_path), tokenizer)

            # Step 2: Merge small chunks
            merged = merge_small_chunks_forward(chunks, tokenizer)

            # Step 3: Add metadata for vendor
            for c in merged:
                c["source_type"] = "VendorResponse"
                c["vendor_name"] = vendor_name

            # Step 4: Save JSON file for this vendor
            output_file = OUTPUT_FOLDER / f"{vendor_name}_chunks.json"
            save_json(merged, output_file)
            print(f"✅ Saved {vendor_name} chunks → {output_file}")

        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")

    print("\n🎯 All vendor responses processed successfully!")


# ----------------------------
# Run
# ----------------------------
if __name__ == "__main__":
    parse_vendor_responses()
