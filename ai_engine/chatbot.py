import json
import os
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv

# -----------------------------
# CONFIGURATION
# -----------------------------
VECTOR_DB_FILE = "chunks_faiss.index"
METADATA_FILE = "chunks_metadata.json"

EMBEDDING_MODEL = "text-embedding-3-large"
OPENAI_MODEL = "gpt-4o-mini"
TOP_K_CHUNKS = 5
MAX_TOKENS = 1500

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY in .env file")

client = OpenAI(api_key=OPENAI_API_KEY)


# Load FAISS + metadata
index = faiss.read_index(VECTOR_DB_FILE)
with open(METADATA_FILE, "r", encoding="utf-8") as f:
    metadata = json.load(f)


# -----------------------------
# RETRIEVAL
# -----------------------------
def retrieve_chunks(query, top_k=TOP_K_CHUNKS):
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
            "If no context supports the answer, say: Not in the RFP."
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
    for chunk in response:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            print(delta.content, end="", flush=True)
            final_answer += delta.content

    print("\n")
    return final_answer


# -----------------------------
# CHATBOT LOOP
# -----------------------------
def run_chatbot():
    print("\n🤖 Ready! Ask anything — type 'exit' to quit.\n")

    while True:
        query = input("Your Question: ").strip()
        if query.lower() == "exit":
            print("👋 Bye!")
            break

        retrieved = retrieve_chunks(query)
        print("\n📝 Answer:\n")
        generate_answer_streaming(query, retrieved)
        print("\n🔍 Citations refer to chunk numbers.\n")


if __name__ == "__main__":
    run_chatbot()
