"""
RFP Comparative Chatbot (Compliance-Aware)
Tiny safe enhancements – NO pipeline conflicts.
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
_compliance_loaded_once = False

def load_compliance_results(folder: str = COMPLIANCE_DIR) -> Dict[str, Dict]:
    """
    Loads vendor compliance results.
    Returns: { vendor_name: {compliant: bool, missing_requirements: [...] } }
    """
    global _compliance_loaded_once

    results = {}
    folder_path = Path(folder)
    if not folder_path.exists():
        if not _compliance_loaded_once:
            print("⚠️ No compliance folder — assuming all vendors are compliant.")
        _compliance_loaded_once = True
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
            print(f"⚠️ Error loading {file.name}: {e}")

    # Print only once
    if not _compliance_loaded_once:
        print(f"📋 Loaded compliance info for {len(results)} vendors.")
        _compliance_loaded_once = True

    return results

# -----------------------------
# Chatbot Class
# -----------------------------
class RFPChatbot:
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
                raise ValueError("OPENAI_API_KEY not found.")

        self.client = OpenAI(api_key=api_key)
        self.embedding_model = embedding_model
        self.openai_model = openai_model
        self.top_k = top_k
        self.max_tokens = max_tokens

        # Load FAISS
        self.index = faiss.read_index(str(vector_db_file))

        # Load metadata
        with open(metadata_file, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        # Load compliance info
        self.compliance_results = load_compliance_results(compliance_dir)

        print(f"✅ FAISS index loaded with {self.index.ntotal} vectors")
        print(f"✅ Metadata loaded: {len(self.metadata)} entries")
        print(f"🚦 Compliance-aware retrieval active")

    # -----------------------------
    # Retrieval
    # -----------------------------
    def retrieve_chunks(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """Retrieve relevant chunks, skipping non-compliant vendors."""
        if top_k is None:
            top_k = self.top_k

        # Embed query
        emb = self.client.embeddings.create(
            model=self.embedding_model,
            input=query
        ).data[0].embedding

        query_vec = np.array([emb], dtype="float32")
        distances, indices = self.index.search(query_vec, top_k * 3)

        results = []
        for j, idx in enumerate(indices[0]):
            if idx >= len(self.metadata):
                continue

            meta = self.metadata[idx]
            text = meta.get("text", "").strip()
            if not text:
                continue

            vendor_name = meta.get("vendor_name")
            source_type = meta.get("source_type", "RFP")

            # Skip non compliant vendors
            if vendor_name and vendor_name in self.compliance_results:
                if not self.compliance_results[vendor_name]["compliant"]:
                    continue

            label = vendor_name if vendor_name else source_type

            results.append({
                "chunk": text,
                "label": label,
                "vendor_name": vendor_name,
                "source_type": source_type,
                "distance": float(distances[0][j]),
                "index": idx,
            })

            if len(results) >= top_k:
                break

        return results

    # -----------------------------
    # Prompt Construction
    # -----------------------------
    def _build_prompts(self, query: str, chunks: List[Dict]) -> tuple:
        context = "\n\n".join(c["chunk"] for c in chunks)


        # Disqualified vendors section
        disqualified_info = ""
        disqualified = [
            v for v, r in self.compliance_results.items()
            if not r["compliant"]
        ]

        if disqualified:
            disqualified_info = "The following vendors were disqualified:\n"
            for v in disqualified:
                missing = self.compliance_results[v].get("missing_requirements", [])
                disqualified_info += f"• {v}: Missing mandatory requirements such as:\n"
                for m in missing[:3]:
                    disqualified_info += f"   - {m}\n"
            disqualified_info += "\n"

        system_prompt = f"""
You are EVAL — an advanced RFP Evaluation Assistant.
You analyze RFPs and vendor responses with evidence-based reasoning.

Capabilities:
• Access to RFP chunks
• Access to vendor chunks
• Awareness of vendor compliance/disqualification
• Ability to compare compliant vendors only unless requested otherwise

Rules:
1. Mandatory requirements override all other considerations.
2. Disqualified vendors must be excluded from comparisons unless explicitly asked.
3. Always cite evidence from the retrieved chunks.
4. Maintain an expert, objective tone.
5. Never hallucinate. If information is missing in the retrieved context, state it clearly.

{disqualified_info}
"""

        user_prompt = f"""
Context:
{context}

Question:
{query}

Provide a precise, structured answer based ONLY on the above context.
"""

        return system_prompt, user_prompt

    # -----------------------------
    # GPT Call
    # -----------------------------
    def _ask_gpt(self, system_prompt: str, user_prompt: str, stream: bool = True) -> str:
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
        chunks = self.retrieve_chunks(query, top_k)
        system_prompt, user_prompt = self._build_prompts(query, chunks)
        answer = self._ask_gpt(system_prompt, user_prompt, stream)
        return answer, chunks

    # -----------------------------
    # CLI Mode
    # -----------------------------
    def run_interactive(self):
        print("\n🤖 Chatbot ready — ask anything (type 'exit' to quit)\n")
        while True:
            query = input("Your Question: ").strip()
            if query.lower() == "exit":
                break
            if query:
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
