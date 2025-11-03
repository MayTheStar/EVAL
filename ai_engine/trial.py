# main_openai.py
import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from openai import OpenAI
from dotenv import load_dotenv

# -----------------------------
# CONFIGURATION
# -----------------------------
CHUNKS_FILE = "/Users/rayana/EVAL/ai_engine/output_chunks.txt"
VECTOR_DB_FILE = "chunks_faiss.index"
METADATA_FILE = "chunks_metadata.json"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OPENAI_MODEL = "gpt-3.5-turbo"  # Or gpt-4 if available
MAX_TOKENS = 300
TOP_K_CHUNKS = 3

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()  # Load variables from .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found in environment. Please set OPENAI_API_KEY in your .env file.")

# Create client
client = OpenAI(api_key=OPENAI_API_KEY)


# -----------------------------
# STEP 1: Embed chunks
# -----------------------------
def embed_chunks():
    print("📌 Embedding chunks...")
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks_text = [line.strip() for line in f if line.strip()]

    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode(chunks_text, show_progress_bar=True)

    # Create FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings, dtype=np.float32))
    faiss.write_index(index, VECTOR_DB_FILE)

    # Save metadata
    metadata = [{"text": text} for text in chunks_text]
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"✅ Embedded {len(chunks_text)} chunks and saved FAISS index.")
    return model, index, metadata

# -----------------------------
# STEP 2: Retrieve chunks
# -----------------------------
def retrieve_chunks(query, embed_model, index, metadata, top_k=TOP_K_CHUNKS):
    query_emb = embed_model.encode([query])
    distances, indices = index.search(np.array(query_emb, dtype=np.float32), top_k)
    results = []
    for j, i in enumerate(indices[0]):
        chunk_meta = metadata[i]
        results.append({
            "chunk": chunk_meta["text"],
            "distance": float(distances[0][j]),
            "index": i
        })
    return results

# -----------------------------
# STEP 3: Generate answer using OpenAI API
# -----------------------------
def generate_answer(query, chunks):
    context = "\n".join([f"[Chunk {c['index']}]\n{c['chunk']}" for c in chunks])
    prompt = f"""
You are an RFP assistant. Answer the user's question based only on the context below. 
If the context does not contain the answer, say "I could not find the answer in the RFP."

Context:
{context}

Question: {query}
Answer:
"""
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=MAX_TOKENS,
        temperature=0.2,
    )
    answer = response.choices[0].message.content.strip()

    return answer

# -----------------------------
# STEP 4: Chatbot Interface
# -----------------------------
def run_chatbot(embed_model, index, metadata):
    print("🤖 RFP Chatbot using OpenAI is ready. Type 'exit' to quit.\n")
    while True:
        query = input("Your question: ").strip()
        if query.lower() == "exit":
            print("Goodbye!")
            break
        chunks = retrieve_chunks(query, embed_model, index, metadata)
        answer = generate_answer(query, chunks)
        print(f"\nAnswer:\n{answer}\n")

# -----------------------------
# MAIN PIPELINE
# -----------------------------
def main():
    embed_model, index, metadata = embed_chunks()
    run_chatbot(embed_model, index, metadata)

if __name__ == "__main__":
    main()
