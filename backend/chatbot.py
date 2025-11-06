from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Optional, Dict, Any
import numpy as np
import faiss
import json
import os
import re
import uvicorn

# -----------------------------
# CONFIGURATION
# -----------------------------
VECTOR_DB_FILE = "C:/Users/HP/Desktop/EVAL5/ai_engine/chunks_faiss.index"
METADATA_FILE = "C:/Users/HP/Desktop/EVAL5/ai_engine/chunks_metadata.json"

EMBEDDING_MODEL = "text-embedding-3-large"
OPENAI_MODEL = "gpt-4o-mini"
TOP_K_CHUNKS = 5
MAX_TOKENS = 1500

# Load API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY in .env file")

client = OpenAI(api_key=OPENAI_API_KEY)

# -----------------------------
# FASTAPI APP
# -----------------------------
app = FastAPI(title="RFP Chatbot API", description="AI assistant for Q&A about RFP documents")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# REQUEST/RESPONSE MODELS
# -----------------------------
class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = TOP_K_CHUNKS

class ChunkInfo(BaseModel):
    chunk: str
    distance: float
    index: int

class QueryResponse(BaseModel):
    query: str
    answer: str
    chunks: List[ChunkInfo]
    citations: List[str]


# -----------------------------
# CORE CHATBOT FUNCTIONS
# -----------------------------
def retrieve_chunks(query: str, top_k: int = TOP_K_CHUNKS) -> List[Dict[str, Any]]:
    """Retrieve top-k relevant chunks using FAISS."""
    try:
        index = faiss.read_index(VECTOR_DB_FILE)
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="FAISS or metadata files not found.")

    # Generate query embedding
    emb = client.embeddings.create(model=EMBEDDING_MODEL, input=query).data[0].embedding
    query_vec = np.array([emb], dtype="float32")
    distances, indices = index.search(query_vec, top_k)

    return [
        {"chunk": metadata[i]["text"], "distance": float(distances[0][j]), "index": i}
        for j, i in enumerate(indices[0])
    ]


def generate_answer(query: str, chunks: List[Dict[str, Any]]) -> tuple[str, List[str]]:
    """Generate GPT-based answer with context citations."""
    context = "\n\n".join(f"(Chunk {c['index']})\n{c['chunk']}" for c in chunks)

    messages = [
        {
            "role": "system",
            "content": (
                "You are an RFP expert assistant. "
                "Answer ONLY using the provided context, citing chunks like [C3]. "
                "If the answer isn't found, say: Not in the RFP."
            )
        },
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        }
    ]

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=0.1
    )

    answer = response.choices[0].message.content
    citations = re.findall(r'\[C(\d+)\]', answer)
    return answer, citations


def generate_answer_stream(query: str, chunks: List[Dict[str, Any]]):
    """Stream GPT-based answer gradually."""
    context = "\n\n".join(f"(Chunk {c['index']})\n{c['chunk']}" for c in chunks)

    messages = [
        {
            "role": "system",
            "content": (
                "You are an RFP expert assistant. "
                "Answer ONLY using the provided context, citing chunks like [C3]. "
                "If the answer isn't found, say: Not in the RFP."
            )
        },
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        }
    ]

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=0.1,
        stream=True
    )

    for part in response:
        delta = part.choices[0].delta
        if delta and delta.content:
            yield delta.content


# -----------------------------
# ENDPOINTS
# -----------------------------
@app.post("/chatbot/query", response_model=QueryResponse)
async def chatbot_query(request: QueryRequest):
    """Non-streaming endpoint — returns full answer."""
    try:
        chunks = retrieve_chunks(request.query, request.top_k)
        answer, citations = generate_answer(request.query, chunks)
        return QueryResponse(
            query=request.query,
            answer=answer,
            chunks=[ChunkInfo(**chunk) for chunk in chunks],
            citations=citations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chatbot/query_stream")
async def chatbot_query_stream(request: QueryRequest):
    """Streaming endpoint — returns answer in real-time."""
    try:
        chunks = retrieve_chunks(request.query, request.top_k)
        return StreamingResponse(
            generate_answer_stream(request.query, chunks),
            media_type="text/plain"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":
    print("\n🚀 Starting RFP Chatbot API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
