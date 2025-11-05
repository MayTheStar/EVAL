import json
import os
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import sys

# -----------------------------
# CONFIGURATION
# -----------------------------
EMBEDDING_MODEL = "text-embedding-3-large"

# Load environment
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY in .env file")

client = OpenAI(api_key=OPENAI_API_KEY)


def embed_chunks(input_file_path):
    input_path = Path(input_file_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"File not found: {input_file_path}")

    # Use input file name to generate output file names
    file_stem = input_path.stem.replace("_chunks", "")
    vector_db_file = f"{file_stem.replace(" ", "")}_faiss.index"
    metadata_file = f"{file_stem.replace(" ", "")}_metadata.json"

    print(f"📌 Loading cleaned chunks from {input_file_path}...")
    with open(input_file_path, "r", encoding="utf-8") as f:
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
    faiss.write_index(index, vector_db_file)

    metadata = [{"text": t} for t in chunks_text]
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"✅ Embedded {len(chunks_text)} chunks stored in FAISS successfully!")
    print(f"Vector index file: {vector_db_file}")
    print(f"Metadata file: {metadata_file}")


