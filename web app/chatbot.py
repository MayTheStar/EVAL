"""
RFP Comparative Chatbot (Compliance-Aware)
==========================================

This module defines the `RFPChatbot` class — an intelligent chatbot for analyzing
and comparing RFP requirements and multiple vendor responses, including structured
capability analyses and mandatory-compliance filtering.

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
COMPLIANCE_DIR = "outputs/compliance"


# -----------------------------
# Helper
# -----------------------------
def load_compliance_results(folder: str = COMPLIANCE_DIR) -> Dict[str, Dict]:
    """
    Load compliance results for all vendors.
    Returns a dict: {vendor_name: {"compliant": bool, "missing_requirements": [...]} }
    """
    results = {}
    folder_path = Path(folder)
    if not folder_path.exists():
        print("⚠️ No compliance directory found — assuming all vendors are compliant.")
        return results

    for file in folder_path.glob("*_compliance.json"):
        vendor_name = file.stem.replace("_compliance", "")
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                results[vendor_name] = {
                    "compliant": data.get("compliant", False),
                    "missing_requirements": data.get("missing_requirements", []),
                }
        except Exception as e:
            print(f"⚠️ Error reading compliance file {file.name}: {e}")
    print(f"📋 Loaded compliance info for {len(results)} vendors.")
    return results


# -----------------------------
# Chatbot Class
# -----------------------------
class RFPChatbot:
    """
    Chatbot for querying and comparing RFP and vendor documents.

    This class uses a Retrieval-Augmented Generation (RAG) approach:
    - Retrieves the most relevant text chunks from FAISS embeddings.
    - Skips non-compliant vendors automatically.
    - Uses OpenAI GPT models to generate structured comparative answers.
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
        compliance_dir: str = COMPLIANCE_DIR,
    ):
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

        # Load FAISS + metadata
        self.index = faiss.read_index(vector_db_file)
        with open(metadata_file, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        # Load compliance info
        self.compliance_results = load_compliance_results(compliance_dir)

        print(f"✅ FAISS index loaded with {self.index.ntotal} vectors")
        print(f"✅ Metadata entries: {len(self.metadata)}")
        print(f"✅ Compliance awareness enabled for {len(self.compliance_results)} vendors")

    # -----------------------------
    # Retrieval
    # -----------------------------
    def retrieve_chunks(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """
        Retrieve most relevant chunks for a query, skipping non-compliant vendors.
        """
        if top_k is None:
            top_k = self.top_k

        emb = self.client.embeddings.create(model=self.embedding_model, input=query).data[0].embedding
        query_vec = np.array([emb], dtype="float32")
        distances, indices = self.index.search(query_vec, top_k * 3)  # fetch more, we'll filter later

        results = []
        for j, i in enumerate(indices[0]):
            if i >= len(self.metadata):
                continue
            meta = self.metadata[i]
            vendor_name = meta.get("vendor_name")
            if vendor_name and vendor_name in self.compliance_results:
                if not self.compliance_results[vendor_name]["compliant"]:
                    continue  # skip non-compliant vendors entirely

            label = vendor_name or meta.get("source_type", "RFP")
            results.append({
                "chunk": meta.get("text", ""),
                "distance": float(distances[0][j]),
                "index": i,
                "label": label,
                "source_type": meta.get("source_type", "RFP"),
                "vendor_name": vendor_name,
            })

            if len(results) >= top_k:
                break
        return results

    # -----------------------------
    # Prompt Construction
    # -----------------------------
    def _build_prompts(self, query: str, chunks: List[Dict]) -> tuple:
        """
        Build system/user prompts for GPT.
        """
        context = "\n\n".join(f"[{c['label']} - Chunk {c['index']}]\n{c['chunk']}" for c in chunks)

        # Add awareness of disqualified vendors
        disqualified_info = ""
        disqualified_vendors = [v for v, r in self.compliance_results.items() if not r["compliant"]]
        if disqualified_vendors:
            for v in disqualified_vendors:
                missing = self.compliance_results[v].get("missing_requirements", [])
                disqualified_info += f"\nVendor {v} was disqualified for missing mandatory requirements such as:\n"
                disqualified_info += "\n".join(f" - {m}" for m in missing[:3]) + "\n"

        system_prompt = (
            "You are an advanced RFP evaluation assistant.\n"
            "You have access to the RFP document and vendor responses.\n"
            "Some vendors may have been disqualified for missing mandatory requirements.\n"
            "Answer carefully and mention compliance status where relevant.\n"
            "When comparing vendors, include only compliant ones unless the user explicitly asks about others.\n"
            + disqualified_info
        )

        user_prompt = f"""
Context Documents:
{context}

Question:
{query}

Provide your analysis based on the context above.
If a vendor was disqualified, explain why if relevant.
"""
        return system_prompt, user_prompt

    # -----------------------------
    # GPT Calls
    # -----------------------------
    def _ask_gpt(self, system_prompt: str, user_prompt: str, stream: bool = True) -> str:
        """
        Send prompts to OpenAI GPT and get a response.
        """
        response = self.client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=0.2,
            stream=stream
        )

        answer = ""
        if stream:
            for part in response:
                delta = part.choices[0].delta
                if delta and delta.content:
                    print(delta.content, end="", flush=True)
                    answer += delta.content
            print("\n")
        else:
            answer = response.choices[0].message.content
        return answer

    # -----------------------------
    # Public Interface
    # -----------------------------
    def query(self, query: str, stream: bool = True, top_k: Optional[int] = None) -> tuple:
        """
        Execute a full query: retrieve chunks → send to GPT → return answer.
        """
        chunks = self.retrieve_chunks(query, top_k)
        system_prompt, user_prompt = self._build_prompts(query, chunks)
        answer = self._ask_gpt(system_prompt, user_prompt, stream)
        return answer, chunks

    # -----------------------------
    # CLI Mode
    # -----------------------------
    def run_interactive(self):
        """
        Console mode for testing.
        """
        print("\n🤖 Chatbot ready — ask anything about RFPs or vendors (type 'exit' to quit)\n")
        while True:
            query = input("Your Question: ").strip()
            if query.lower() == "exit":
                print("👋 Goodbye!")
                break
            if not query:
                continue
            self.query(query, stream=True)


# -----------------------------
# Factory
# -----------------------------
def create_chatbot(
    vector_db_file: str,
    metadata_file: str,
    api_key: str = None,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    openai_model: str = DEFAULT_OPENAI_MODEL,
    top_k: int = DEFAULT_TOP_K,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    compliance_dir: str = COMPLIANCE_DIR,
) -> RFPChatbot:
    """Factory function to build a compliance-aware chatbot."""
    return RFPChatbot(
        vector_db_file=vector_db_file,
        metadata_file=metadata_file,
        api_key=api_key,
        embedding_model=embedding_model,
        openai_model=openai_model,
        top_k=top_k,
        max_tokens=max_tokens,
        compliance_dir=compliance_dir,
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        chatbot = create_chatbot(sys.argv[1], sys.argv[2])
        chatbot.run_interactive()
    else:
        print("Usage: python chatbot.py <vector_db_file> <metadata_file>")
