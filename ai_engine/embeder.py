import json
import os
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv
import glob
from pathlib import Path  

# -----------------------------
# CONFIGURATION
# -----------------------------
CHUNKS_FILE = "/Users/maybader/EVAL/ai_engine/output_chunks.json"
VECTOR_DB_FILE = "chunks_faiss.index"
METADATA_FILE = "chunks_metadata.json"

EMBEDDING_MODEL = "text-embedding-3-large"

# Load environment
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY in .env file")

client = OpenAI(api_key=OPENAI_API_KEY)


def embed_chunks():
    print("📌 Loading all RFP + Vendor chunks from JSON...")

    # Collect all *_chunks.json files (RFP and Vendors)
    json_files = glob.glob("/Users/maybader/EVAL/ai_engine/*_chunks.json")

    all_chunks = []
    for path in json_files:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            all_chunks.extend(data)
            print(f"   ➕ Loaded {len(data)} chunks from {Path(path).name}")

    print(f"\n✅ Total combined chunks: {len(all_chunks)}")

    chunks_text = [c["contextualized_text"] for c in all_chunks]

    print("✨ Generating OpenAI embeddings...")
    embeddings = []
    for text in chunks_text:
        resp = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        embeddings.append(resp.data[0].embedding)

    embeddings = np.array(embeddings).astype("float32")
    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    faiss.write_index(index, VECTOR_DB_FILE)

    # Save metadata with all sources
    metadata = []
    for c in all_chunks:
        metadata.append({
            "text": c["contextualized_text"],
            "source_type": c.get("source_type", "RFP"),
            "vendor_name": c.get("vendor_name", None)
        })

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Embedded {len(chunks_text)} total chunks (RFP + Vendors)")
    print(f"🗂 FAISS index: {VECTOR_DB_FILE}")
    print(f"🗂 Metadata: {METADATA_FILE}")


if __name__ == "__main__":
    embed_chunks()
