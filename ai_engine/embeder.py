import json
import os
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv

# -----------------------------
# CONFIGURATION
# -----------------------------
CHUNKS_FILE = "/Users/rayana/EVAL/ai_engine/output_chunks.json"
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
    print("📌 Loading cleaned chunks from JSON...")
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    chunks_text = [c["contextualized_text"] for c in chunks]

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

    metadata = [{"text": t} for t in chunks_text]
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"✅ Embedded {len(chunks_text)} chunks stored in FAISS successfully!")


if __name__ == "__main__":
    embed_chunks()
