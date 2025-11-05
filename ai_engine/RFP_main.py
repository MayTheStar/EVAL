from pathlib import Path
from parser2 import process_pdf
from embeder2 import embed_chunks
import time
from chatbot2 import run_chatbot   # ✅ CALL THE CHATBOT

# -----------------------
# 1️⃣ Generic parse + embed
# -----------------------
def parse_and_embed(pdf_path: str):
    """
    Parse a PDF into chunks and embed them in FAISS.
    """
    pdf_file = Path(pdf_path)
    print(f"\n📄 Processing PDF: {pdf_file.name}")

    chunks_txt, chunks_json = process_pdf(str(pdf_file))
    embed_chunks(chunks_json)

    print(f"✅ Parsed and embedded: {pdf_file.name}")

    return {
        "chunks_txt": chunks_txt,
        "chunks_json": chunks_json,
        "faiss_index": f"{pdf_file.stem.replace(" ", "")}_faiss.index",        # ✅ Already uses PDF name
        "metadata_json": f"{pdf_file.stem.replace(" ", "")}_metadata.json"     # ✅ Already uses PDF name
    }

# -----------------------
# 2️⃣ Process RFP
# -----------------------
def process_rfp(rfp_path: str):
    return parse_and_embed(rfp_path)

# -----------------------
# 🚀 Example usage
# -----------------------
if __name__ == "__main__":
    start_time = time.time()

    rfp_pdf = "/Users/rayana/EVAL/ai_engine/USask RFP.pdf"
    rfp_files = process_rfp(rfp_pdf)

    # 🕒 Time Summary
    elapsed_time = time.time() - start_time
    hours, rem = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(rem, 60)

    print("\n📁 RFP Generated Files:")
    for key, val in rfp_files.items():
        print(f"{key}: {val}")

    print(f"\n⏱️ Total processing time: {int(hours)}h {int(minutes)}m {seconds:.2f}s")

    # ✅ CALL CHATBOT WITH RIGHT FILES (NO NAME CHANGES)
    print("\n🤖 Launching chatbot with FAISS + metadata + chunks...")
    run_chatbot(
        index_file =rfp_files["faiss_index"],
        metadata_file=rfp_files["metadata_json"],
    )
