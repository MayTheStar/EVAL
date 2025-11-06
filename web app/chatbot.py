"""
RFP Analysis Chatbot
Interactive chatbot for querying RFP and vendor response documents using RAG (Retrieval Augmented Generation).
"""

import json
import os
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Dict, Optional


# -----------------------------
# Configuration
# -----------------------------
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_TOP_K = 5
DEFAULT_MAX_TOKENS = 1500


class RFPChatbot:
    """Chatbot for querying RFP and vendor documents using vector search and GPT."""
    
    def __init__(self, 
                 vector_db_file: str,
                 metadata_file: str,
                 api_key: str = None,
                 embedding_model: str = DEFAULT_EMBEDDING_MODEL,
                 openai_model: str = DEFAULT_OPENAI_MODEL,
                 top_k: int = DEFAULT_TOP_K,
                 max_tokens: int = DEFAULT_MAX_TOKENS):
        """
        Initialize the chatbot.
        
        Args:
            vector_db_file: Path to FAISS index file
            metadata_file: Path to metadata JSON file
            api_key: OpenAI API key (if None, loads from environment)
            embedding_model: Model for generating query embeddings
            openai_model: Model for generating answers
            top_k: Number of chunks to retrieve
            max_tokens: Maximum tokens in generated response
        """
        # Load API key
        if api_key is None:
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY in environment or pass as parameter.")
        
        self.client = OpenAI(api_key=api_key)
        self.embedding_model = embedding_model
        self.openai_model = openai_model
        self.top_k = top_k
        self.max_tokens = max_tokens
        
        # Load FAISS index and metadata
        self.index = faiss.read_index(vector_db_file)
        with open(metadata_file, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)
        
        print(f"✅ Loaded FAISS index with {self.index.ntotal} vectors")
        print(f"✅ Loaded metadata for {len(self.metadata)} chunks")
    
    def retrieve_chunks(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: Query text
            top_k: Number of chunks to retrieve (uses default if None)
            
        Returns:
            List of retrieved chunks with metadata
        """
        if top_k is None:
            top_k = self.top_k
        
        # Generate query embedding
        emb = self.client.embeddings.create(
            model=self.embedding_model,
            input=query
        ).data[0].embedding
        
        query_vec = np.array([emb], dtype="float32")
        distances, indices = self.index.search(query_vec, top_k)
        
        results = []
        for j, i in enumerate(indices[0]):
            if i >= len(self.metadata):
                continue
            
            source_type = self.metadata[i].get("source_type", "RFP")
            vendor_name = self.metadata[i].get("vendor_name")
            label = f"{vendor_name}" if vendor_name else source_type
            
            results.append({
                "chunk": self.metadata[i]["text"],
                "distance": float(distances[0][j]),
                "index": i,
                "label": label,
                "page_number": self.metadata[i].get("page_number"),
                "headings": self.metadata[i].get("headings", [])
            })
        
        return results
    
    def generate_answer_streaming(self, query: str, chunks: List[Dict]) -> str:
        """
        Generate streaming answer using GPT.
        
        Args:
            query: User query
            chunks: Retrieved chunks
            
        Returns:
            Complete generated answer
        """
        context = "\n\n".join(
            f"({c['label']} - Chunk {c['index']})\n{c['chunk']}"
            for c in chunks
        )
        
        system_prompt = (
            "You are an RFP analysis assistant. "
            "You have access to both the RFP and multiple vendor responses. "
            "When answering, clearly state which document each fact comes from, using the label [RFP] or [VendorA], etc. "
            "If the context lacks information, say 'Not found in the provided documents.'"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"}
        ]
        
        response = self.client.chat.completions.create(
            model=self.openai_model,
            messages=messages,
            max_tokens=self.max_tokens,
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
    
    def generate_answer(self, query: str, chunks: List[Dict]) -> str:
        """
        Generate answer using GPT (non-streaming).
        
        Args:
            query: User query
            chunks: Retrieved chunks
            
        Returns:
            Generated answer
        """
        context = "\n\n".join(
            f"({c['label']} - Chunk {c['index']})\n{c['chunk']}"
            for c in chunks
        )
        
        system_prompt = (
            "You are an RFP analysis assistant. "
            "You have access to both the RFP and multiple vendor responses. "
            "When answering, clearly state which document each fact comes from, using the label [RFP] or [VendorA], etc. "
            "If the context lacks information, say 'Not found in the provided documents.'"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"}
        ]
        
        response = self.client.chat.completions.create(
            model=self.openai_model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=0.1
        )
        
        return response.choices[0].message.content
    
    def query(self, query: str, stream: bool = True, top_k: Optional[int] = None) -> tuple:
        """
        Query the chatbot.
        
        Args:
            query: User query
            stream: Whether to stream the response
            top_k: Number of chunks to retrieve
            
        Returns:
            Tuple of (answer, retrieved_chunks)
        """
        chunks = self.retrieve_chunks(query, top_k)
        
        if stream:
            answer = self.generate_answer_streaming(query, chunks)
        else:
            answer = self.generate_answer(query, chunks)
        
        return answer, chunks
    
    def run_interactive(self):
        """Run interactive chatbot loop."""
        print("\n🤖 Ready! Ask anything – type 'exit' to quit.\n")
        
        while True:
            query = input("Your Question: ").strip()
            if query.lower() == "exit":
                print("👋 Bye!")
                break
            
            if not query:
                continue
            
            retrieved = self.retrieve_chunks(query)
            print("\n📝 Answer:\n")
            self.generate_answer_streaming(query, retrieved)
            print("\n📚 Citations refer to chunk numbers.\n")


def create_chatbot(vector_db_file: str,
                  metadata_file: str,
                  api_key: str = None,
                  embedding_model: str = DEFAULT_EMBEDDING_MODEL,
                  openai_model: str = DEFAULT_OPENAI_MODEL,
                  top_k: int = DEFAULT_TOP_K,
                  max_tokens: int = DEFAULT_MAX_TOKENS) -> RFPChatbot:
    """
    Create a chatbot instance.
    
    Args:
        vector_db_file: Path to FAISS index file
        metadata_file: Path to metadata JSON file
        api_key: OpenAI API key
        embedding_model: Model for generating query embeddings
        openai_model: Model for generating answers
        top_k: Number of chunks to retrieve
        max_tokens: Maximum tokens in generated response
        
    Returns:
        RFPChatbot instance
    """
    return RFPChatbot(
        vector_db_file=vector_db_file,
        metadata_file=metadata_file,
        api_key=api_key,
        embedding_model=embedding_model,
        openai_model=openai_model,
        top_k=top_k,
        max_tokens=max_tokens
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        vector_db_file = sys.argv[1]
        metadata_file = sys.argv[2]
        
        chatbot = create_chatbot(vector_db_file, metadata_file)
        chatbot.run_interactive()
    else:
        print("Usage: python chatbot.py <vector_db_file> <metadata_file>")