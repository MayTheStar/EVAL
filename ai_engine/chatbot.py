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
TOP_K_CHUNKS = 8
MAX_TOKENS = 2000

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY in .env file")

client = OpenAI(api_key=OPENAI_API_KEY)


# -----------------------------
# LOAD INDEX + METADATA
# -----------------------------
index = faiss.read_index(VECTOR_DB_FILE)
with open(METADATA_FILE, "r", encoding="utf-8") as f:
    metadata = json.load(f)


# -----------------------------
# RETRIEVAL
# -----------------------------
def retrieve_chunks(query, top_k=TOP_K_CHUNKS):
    """Retrieve top matching chunks across RFP + Vendor responses."""
    emb = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query
    ).data[0].embedding

    query_vec = np.array([emb], dtype="float32")
    distances, indices = index.search(query_vec, top_k)

    results = []
    for j, i in enumerate(indices[0]):
        if i >= len(metadata):
            continue
        source_type = metadata[i].get("source_type", "RFP")
        vendor_name = metadata[i].get("vendor_name")
        label = vendor_name if vendor_name else source_type
        results.append({
            "chunk": metadata[i]["text"],
            "distance": float(distances[0][j]),
            "index": i,
            "label": label,
            "source_type": source_type,
            "vendor_name": vendor_name
        })
    return results


# -----------------------------
# GPT ANSWER (COMPARISON-AWARE)
# -----------------------------
def generate_answer_streaming(query, chunks):
    """Generate an intelligent comparative answer between RFP and vendor responses."""
    context = "\n\n".join(
        f"[{c['label']} - Chunk {c['index']}]\n{c['chunk']}"
        for c in chunks
    )

    system_prompt = (
        "You are an advanced RFP evaluation assistant. "
        "You have access to an RFP document (with requirements) and multiple vendor responses (with capabilities). "
        "Your job is to interpret and compare them intelligently.\n\n"
        "Guidelines:\n"
        "- When answering, clearly indicate which document each piece of information comes from using tags like [RFP], [VendorA], [VendorB].\n"
        "- If comparing, explicitly mention similarities, differences, and which vendor meets the requirement best.\n"
        "- Use structured reasoning: start with the RFP requirement, then evaluate each vendor’s capability or commitment.\n"
        "- Be objective, concise, and comparison-focused.\n"
        "- If information is missing, say 'Not found in the provided documents.'\n"
    )

    user_prompt = f"""
Context documents:
{context}

Question:
{query}

Now compare and answer based on the RFP requirements and vendor capabilities.
Include reasoning and cite sources as [RFP], [VendorA], etc.
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=MAX_TOKENS,
        temperature=0.2,
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
# HELPER: FILTER BY SOURCE TYPE OR VENDOR
# -----------------------------
def retrieve_filtered_chunks(query, vendor_name=None, only_rfp=False):
    """Optionally filter chunks by vendor or document type."""
    chunks = retrieve_chunks(query)
    if only_rfp:
        return [c for c in chunks if c["source_type"].lower() == "rfp"]
    if vendor_name:
        return [c for c in chunks if c.get("vendor_name") == vendor_name]
    return chunks


# -----------------------------
# CHATBOT LOOP
# -----------------------------
def run_chatbot():
    print("\n🤖 Ready! Ask anything about the RFP or vendor responses — type 'exit' to quit.\n")
   

    while True:
        query = input("Your Question: ").strip()
        if query.lower() == "exit":
            print("👋 Bye!")
            break

        retrieved = retrieve_chunks(query)
        print("\n🧩 Analyzing documents...\n")
        generate_answer_streaming(query, retrieved)
        print("\n🔍 Citations refer to [RFP], [VendorA], etc.\n")


if __name__ == "__main__":
    run_chatbot()
