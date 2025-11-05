from pathlib import Path
from parser2 import process_pdf
from embeder2 import embed_chunks

import time

# -----------------------
# 1️⃣ Generic parse + embed
# -----------------------
def parse_and_embed(pdf_path: str):
    """
    Parse a PDF into chunks and embed them in FAISS.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        dict: Paths of generated files (chunks, embeddings, metadata)
    """
    pdf_file = Path(pdf_path)
    print(f"\n📄 Processing PDF: {pdf_file.name}")

    # Parse PDF
    chunks_txt, chunks_json = process_pdf(str(pdf_file))

    # Embed chunks
    embed_chunks(chunks_json)
    print(f"✅ Parsed and embedded: {pdf_file.name}")

    return {
        "chunks_txt": chunks_txt,
        "chunks_json": chunks_json,
        "faiss_index": f"{pdf_file.stem}_faiss.index",
        "metadata_json": f"{pdf_file.stem}_metadata.json"
    }

# -----------------------
# 3️⃣ Process Vendor (parse + embed only)
# -----------------------
def process_vendor(vendor_path: str):
    """
    Parse and embed Vendor PDF only.
    """
    return parse_and_embed(vendor_path)

# -----------------------
# Example usage
# -----------------------
if __name__ == "__main__":
    start_time = time.time() 

    vendor_pdf = "/Users/rayana/EVAL/ai_engine/BeamVendor.pdf"


    vendor_files = process_vendor(vendor_pdf)

    elapsed_time = time.time() - start_time
    hours, rem = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(rem, 60)

    print("\nVendor generated files and outputs:")
    for key, val in vendor_files.items():
        print(f"{key}: {val}")

    print(f"\n⏱️ Total processing time: {int(hours)}h {int(minutes)}m {seconds:.2f}s")
