import argparse
import json
import os
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv

# -----------------------------
# DEFAULT CONFIG
# -----------------------------
DEFAULT_INDEX_FILE = "chunks_faiss.index"
DEFAULT_METADATA_FILE = "chunks_metadata.json"
EMBEDDING_MODEL = "text-embedding-3-large"
OPENAI_MODEL = "gpt-4o-mini"
TOP_K_CHUNKS = 5
MAX_TOKENS = 1500

# Load API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY in .env file")

client = OpenAI(api_key=OPENAI_API_KEY)


# -----------------------------
# DYNAMIC LOADING
# -----------------------------
def load_vector_db(index_path, metadata_path):
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"Vector DB file not found: {index_path}")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    index = faiss.read_index(index_path)
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"✅ Loaded index: {index_path}")
    print(f"✅ Loaded metadata: {metadata_path} ({len(metadata)} chunks)")
    return index, metadata


# -----------------------------
# RETRIEVAL
# -----------------------------
def retrieve_chunks(query, index, metadata, top_k=TOP_K_CHUNKS):
    emb = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query
    ).data[0].embedding

    query_vec = np.array([emb], dtype="float32")
    distances, indices = index.search(query_vec, top_k)

    return [
        {"chunk": metadata[i]["text"], "distance": float(distances[0][j]), "index": i}
        for j, i in enumerate(indices[0])
    ]


# -----------------------------
# GPT ANSWER (STREAMING)
# -----------------------------
def generate_answer_streaming(query, chunks):
    context = "\n\n".join(f"(Chunk {c['index']})\n{c['chunk']}" for c in chunks)

    messages = [
        {"role": "system", "content":
            "You are an RFP expert. Only answer using the provided context. "
            "Every claim MUST cite the chunk number like [C3]. "
            "If no context supports the answer → respond: Not in the RFP."
        },
        {"role": "user", "content":
            f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        }
    ]

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=0.1,
        stream=True
    )

    final_answer = ""
    for part in response:
        delta = part.choices[0].delta
        if delta and delta.content:
            print(delta.content, end="", flush=True)
            final_answer += delta.content

    print("\n")
    return final_answer


# -----------------------------
# CHATBOT LOOP
# -----------------------------
def run_chatbot(index_file, metadata_file):
    index, metadata = load_vector_db(index_file, metadata_file)

    print("\n🤖 Ready! Ask anything — type 'exit' to quit.\n")

    while True:
        query = input("Your Question: ").strip()
        if query.lower() == "exit":
            print("👋 Bye!")
            break

        retrieved = retrieve_chunks(query, index, metadata)
        print("\n📝 Answer:\n")
        generate_answer_streaming(query, retrieved)
        print("\n🔍 Citations refer to chunk numbers.\n")


# -----------------------------
# CLI ENTRY
# -----------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chatbot with dynamic vector DB loading")
    parser.add_argument("--db", default=DEFAULT_INDEX_FILE, help="FAISS index file")
    parser.add_argument("--meta", default=DEFAULT_METADATA_FILE, help="Metadata JSON file")
    args = parser.parse_args()

    run_chatbot(index_file=args.db, metadata_file=args.meta)
