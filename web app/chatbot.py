"""
RFP Comparative Chatbot
========================

This module defines the `RFPChatbot` class — an intelligent chatbot for analyzing
and comparing RFP requirements and multiple vendor responses, including structured
capability analyses.

It integrates with the web app through `create_chatbot()`, which returns a ready-to-use
chatbot instance that can answer user queries via Flask routes.
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
DEFAULT_TOP_K = 8
DEFAULT_MAX_TOKENS = 2000


class RFPChatbot:
    """
    Chatbot for querying and comparing RFP and vendor documents.

    This class uses a Retrieval-Augmented Generation (RAG) approach:
    - Retrieves the most relevant text chunks from FAISS embeddings.
    - Uses OpenAI GPT models to generate structured comparative answers.
    - Integrates both raw document chunks and capability analysis summaries.
    """

    def __init__(
        self,
        vector_db_file: str,
        metadata_file: str,
        api_key: str = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        openai_model: str = DEFAULT_OPENAI_MODEL,
        top_k: int = DEFAULT_TOP_K,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """
        Initialize the chatbot.

        Args:
            vector_db_file (str): Path to FAISS index file.
            metadata_file (str): Path to metadata JSON file.
            api_key (str, optional): OpenAI API key. If None, loads from .env file.
            embedding_model (str): Embedding model used for query encoding.
            openai_model (str): GPT model used for answer generation.
            top_k (int): Number of chunks to retrieve per query.
            max_tokens (int): Maximum token limit for the response.
        """
        if api_key is None:
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment.")

        self.client = OpenAI(api_key=api_key)
        self.embedding_model = embedding_model
        self.openai_model = openai_model
        self.top_k = top_k
        self.max_tokens = max_tokens

        # Load FAISS index + metadata
        self.index = faiss.read_index(vector_db_file)
        with open(metadata_file, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        print(f"✅ Loaded FAISS index with {self.index.ntotal} vectors")
        print(f"✅ Loaded metadata entries: {len(self.metadata)}")

    # -----------------------------
    # Chunk Retrieval
    # -----------------------------
    def retrieve_chunks(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """
        Retrieve the most relevant chunks for a given query.

        Args:
            query (str): User query.
            top_k (int, optional): Number of top chunks to retrieve. Defaults to class value.

        Returns:
            List[Dict]: Retrieved chunks, including metadata such as vendor name and type.
        """
        if top_k is None:
            top_k = self.top_k

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

            meta = self.metadata[i]
            source_type = meta.get("source_type", "RFP")
            vendor_name = meta.get("vendor_name")
            is_capability = meta.get("is_capability_analysis", False)

            if is_capability:
                label = f"{vendor_name or 'Vendor'} (Capability Analysis)"
            else:
                label = vendor_name if vendor_name else source_type

            results.append({
                "chunk": meta.get("text", ""),
                "distance": float(distances[0][j]),
                "index": i,
                "label": label,
                "source_type": source_type,
                "vendor_name": vendor_name,
                "is_capability_analysis": is_capability
            })
        return results

    # -----------------------------
    # Prompt Building
    # -----------------------------
    def _build_prompts(self, query: str, chunks: List[Dict]) -> tuple:
        """
        Build the system and user prompts for GPT based on retrieved chunks.

        Args:
            query (str): User's question.
            chunks (List[Dict]): Retrieved context chunks.

        Returns:
            tuple: (system_prompt, user_prompt)
        """
        context = "\n\n".join(
            f"[{c['label']} - Chunk {c['index']}]\n{c['chunk']}"
            for c in chunks
        )

        system_prompt = (
            "You are an advanced RFP evaluation assistant. "
            "You have access to the RFP document (requirements), vendor responses (capabilities), "
            "and structured capability analyses. "
            "Your job is to interpret and compare them intelligently.\n\n"
            "Guidelines:\n"
            "- Clearly tag each reference as [RFP], [VendorA], [VendorA (Capability Analysis)], etc.\n"
            "- When comparing, discuss similarities, differences, and which vendor fulfills each requirement best.\n"
            "- Start each reasoning block with the RFP requirement, then evaluate vendor responses.\n"
            "- Be factual, concise, and objective.\n"
            "- If the answer is missing, write: 'Not found in the provided documents.'\n"
        )

        user_prompt = f"""
Context documents:
{context}

Question:
{query}

Now provide your comparative evaluation.
Include structured reasoning and citations.
"""

        return system_prompt, user_prompt

    # -----------------------------
    # GPT Response Generation
    # -----------------------------
    def generate_answer_streaming(self, query: str, chunks: List[Dict]) -> str:
        """
        Generate an answer using GPT in streaming mode (prints live tokens).

        Args:
            query (str): User question.
            chunks (List[Dict]): Retrieved chunks for context.

        Returns:
            str: Complete GPT-generated answer.
        """
        system_prompt, user_prompt = self._build_prompts(query, chunks)

        response = self.client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=0.2,
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

    def generate_answer(self, query: str, chunks: List[Dict]) -> str:
        """
        Generate an answer using GPT (non-streaming).

        Args:
            query (str): User question.
            chunks (List[Dict]): Retrieved context chunks.

        Returns:
            str: Final GPT-generated answer text.
        """
        system_prompt, user_prompt = self._build_prompts(query, chunks)

        response = self.client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=0.2
        )
        return response.choices[0].message.content

    # -----------------------------
    # Main Query Interface
    # -----------------------------
    def query(self, query: str, stream: bool = True, top_k: Optional[int] = None) -> tuple:
        """
        Execute a full query — retrieve chunks, run GPT, and return the result.

        Args:
            query (str): User query text.
            stream (bool): Whether to stream GPT output in real-time.
            top_k (int, optional): Number of chunks to retrieve.

        Returns:
            tuple: (answer_text, retrieved_chunks)
        """
        chunks = self.retrieve_chunks(query, top_k)
        answer = (
            self.generate_answer_streaming(query, chunks)
            if stream else
            self.generate_answer(query, chunks)
        )
        return answer, chunks

    # -----------------------------
    # CLI Interactive Loop
    # -----------------------------
    def run_interactive(self):
        """
        Launch an interactive console mode for manual testing.

        The user can type questions and receive comparative answers
        about the RFP and vendor responses.
        """
        print("\n🤖 Ready! Ask anything about the RFP or vendor responses — type 'exit' to quit.\n")
        while True:
            query = input("Your Question: ").strip()
            if query.lower() == "exit":
                print("👋 Bye!")
                break
            if not query:
                continue
            chunks = self.retrieve_chunks(query)
            print("\n🧩 Analyzing documents...\n")
            self.generate_answer_streaming(query, chunks)
            print("\n🔍 Citations refer to [RFP], [VendorA], etc.\n")


# -----------------------------
# Factory Function
# -----------------------------
def create_chatbot(
    vector_db_file: str,
    metadata_file: str,
    api_key: str = None,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    openai_model: str = DEFAULT_OPENAI_MODEL,
    top_k: int = DEFAULT_TOP_K,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> RFPChatbot:
    """
    Factory function that creates and returns a chatbot instance.

    Args:
        vector_db_file (str): Path to FAISS index file.
        metadata_file (str): Path to metadata JSON file.
        api_key (str, optional): OpenAI API key.
        embedding_model (str): Embedding model name.
        openai_model (str): OpenAI GPT model name.
        top_k (int): Number of chunks to retrieve per query.
        max_tokens (int): Max tokens per response.

    Returns:
        RFPChatbot: Fully initialized chatbot instance.
    """
    return RFPChatbot(
        vector_db_file=vector_db_file,
        metadata_file=metadata_file,
        api_key=api_key,
        embedding_model=embedding_model,
        openai_model=openai_model,
        top_k=top_k,
        max_tokens=max_tokens,
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        chatbot = create_chatbot(sys.argv[1], sys.argv[2])
        chatbot.run_interactive()
    else:
        print("Usage: python chatbot.py <vector_db_file> <metadata_file>")
