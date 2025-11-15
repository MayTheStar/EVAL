"""
Document Embeddings Generator
Creates vector embeddings for RFP and vendor response chunks using OpenAI embeddings API.
Skips non-compliant vendors based on compliance_checker results.
Stores embeddings in FAISS index with metadata.
"""

import json
import os
from pathlib import Path
from typing import List, Dict
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv


# -----------------------------
# Configuration
# -----------------------------
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"
COMPLIANCE_DIR = "outputs/compliance"  # Default folder where compliance results are stored


class DocumentEmbedder:
    """Handles document embedding and FAISS index creation."""
    
    def __init__(self, api_key: str = None, model: str = DEFAULT_EMBEDDING_MODEL):
        """
        Initialize the embedder.
        
        Args:
            api_key: OpenAI API key (if None, loads from environment)
            model: OpenAI embedding model to use
        """
        if api_key is None:
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY in environment or pass as parameter.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        """
        response = self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding
    
    def embed_texts(self, texts: List[str], batch_size: int = 100) -> np.ndarray:
        """
        Generate embeddings for multiple texts in batches.
        """
        embeddings = []
        total = len(texts)
        
        for i in range(0, total, batch_size):
            batch = texts[i:min(i + batch_size, total)]
            print(f"🔹 Embedding batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}...")
            for text in batch:
                try:
                    embedding = self.embed_text(text)
                    embeddings.append(embedding)
                except Exception as e:
                    print(f"⚠️ Skipping one text due to error: {e}")
        
        return np.array(embeddings).astype("float32")


# -----------------------------
# Helper functions
# -----------------------------

def load_json(file_path: str) -> List[Dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_compliance_results(folder: str = COMPLIANCE_DIR) -> Dict[str, bool]:
    """
    Load vendor compliance results (True = compliant, False = non-compliant).
    """
    compliance_status = {}
    folder_path = Path(folder)
    
    if not folder_path.exists():
        print("⚠️ No compliance folder found. Embedding all vendors by default.")
        return compliance_status
    
    for file in folder_path.glob("*_compliance.json"):
        vendor_name = file.stem.replace("_compliance", "")
        try:
            data = load_json(file)
            compliance_status[vendor_name] = data.get("compliant", False)
        except Exception:
            compliance_status[vendor_name] = False
    
    print(f"📋 Loaded compliance status for {len(compliance_status)} vendors.")
    return compliance_status


def load_chunks_from_json(file_path: str) -> List[Dict]:
    """
    Load chunks from a JSON file.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# -----------------------------
# Embedding creation logic
# -----------------------------

def create_embeddings_and_index(chunk_files: List[str], 
                                vector_db_file: str, 
                                metadata_file: str,
                                compliance_results: Dict[str, bool] = None,
                                api_key: str = None,
                                model: str = DEFAULT_EMBEDDING_MODEL) -> tuple:
    """
    Create embeddings and FAISS index from multiple chunk files, 
    skipping non-compliant vendors.
    """
    print("📌 Loading chunks for embedding...")

    all_chunks = []
    for file_path in chunk_files:
        path_obj = Path(file_path)
        file_name = path_obj.name
        # First file is RFP → mark vendor_name=None
        if file_path == chunk_files[0]:
            vendor_name = None
        else:
            vendor_name = path_obj.stem.replace("_analysis", "").replace("_chunks", "")

        # Skip non-compliant vendors
        if compliance_results and vendor_name in compliance_results and not compliance_results[vendor_name]:
            print(f"⏭️ Skipping {vendor_name} (non-compliant vendor)")
            continue

        if "_analysis" in file_path:
            print(f"⏭️ Skipping analysis file (not chunk file): {file_path}")
            continue

        chunks = load_chunks_from_json(file_path)

        print(f"   ➕ Loaded {len(chunks)} chunks from {file_name}")
        for chunk in chunks:
            if vendor_name:
                chunk["vendor_name"] = vendor_name
            else:
                chunk["vendor_name"] = None
        all_chunks.extend(chunks)
    
    print(f"\n✅ Total included chunks: {len(all_chunks)}")

    # Extract texts
    chunks_text = [
        c.get("contextualized_text") 
        or c.get("summary") 
        or c.get("text", "")
        for c in all_chunks
    ]


    # Generate embeddings
    embedder = DocumentEmbedder(api_key=api_key, model=model)
    print(f"✨ Generating embeddings using model: {model}")
    embeddings = embedder.embed_texts(chunks_text)

    # Create FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    # Save FAISS index
    faiss.write_index(index, str(vector_db_file))
    print(f"✅ FAISS index saved: {vector_db_file}")

    # Save metadata
    metadata = []
    for c in all_chunks:
        metadata.append({
            "text": c.get("contextualized_text") or c.get("summary") or c.get("text", ""),
            "source_type": "Vendor" if c.get("vendor_name") else "RFP",
            "vendor_name": c.get("vendor_name"),
            "page_number": c.get("page_number"),
            "headings": c.get("headings", []),
        })

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"✅ Metadata saved: {metadata_file}")

    print(f"\n🎯 Embedded {len(chunks_text)} total chunks | Dimension: {dimension}")
    return str(vector_db_file), str(metadata_file)



def create_embeddings_from_rfp_and_vendors(rfp_chunks_file: str,
                                           vendor_chunks_files: List[str],
                                           output_dir: str,
                                           vector_db_name: str = "chunks_faiss.index",
                                           metadata_name: str = "chunks_metadata.json",
                                           compliance_dir: str = COMPLIANCE_DIR,
                                           api_key: str = None,
                                           model: str = DEFAULT_EMBEDDING_MODEL) -> tuple:
    """
    Create embeddings from RFP and vendor chunk files, skipping non-compliant vendors.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load compliance results if available
    compliance_results = load_compliance_results(compliance_dir)

    # Include RFP always
    all_files = [rfp_chunks_file]

    # Filter vendor files based on compliance
    for vf in vendor_chunks_files:
        vendor_name = Path(vf).stem.replace("_chunks", "").replace("_analysis", "")
        if compliance_results and vendor_name in compliance_results and not compliance_results[vendor_name]:
            print(f"⏭️ Excluding {vendor_name} due to non-compliance.")
            continue
        all_files.append(vf)

    

    vector_db_file = str(output_path / vector_db_name)
    metadata_file = str(output_path / metadata_name)

    return create_embeddings_and_index(
        all_files,
        vector_db_file,
        metadata_file,
        compliance_results=compliance_results,
        api_key=api_key,
        model=model
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        chunk_files = sys.argv[1:-2]
        vector_db_file = sys.argv[-2]
        metadata_file = sys.argv[-1]
        create_embeddings_and_index(chunk_files, vector_db_file, metadata_file)
    else:
        print("Usage: python embeder.py <chunk_file1> [chunk_file2 ...] <vector_db_file> <metadata_file>")
