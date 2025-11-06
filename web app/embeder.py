"""
Document Embeddings Generator
Creates vector embeddings for RFP and vendor response chunks using OpenAI embeddings API.
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
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        response = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
    
    def embed_texts(self, texts: List[str], batch_size: int = 100) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            
        Returns:
            Numpy array of embeddings
        """
        embeddings = []
        total = len(texts)
        
        for i in range(0, total, batch_size):
            batch = texts[i:min(i + batch_size, total)]
            print(f"Embedding batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}...")
            
            for text in batch:
                embedding = self.embed_text(text)
                embeddings.append(embedding)
        
        return np.array(embeddings).astype("float32")


def load_chunks_from_json(file_path: str) -> List[Dict]:
    """
    Load chunks from a JSON file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        List of chunk dictionaries
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_embeddings_and_index(chunk_files: List[str], 
                                vector_db_file: str, 
                                metadata_file: str,
                                api_key: str = None,
                                model: str = DEFAULT_EMBEDDING_MODEL) -> tuple:
    """
    Create embeddings and FAISS index from multiple chunk files.
    
    Args:
        chunk_files: List of paths to JSON chunk files
        vector_db_file: Path to save FAISS index
        metadata_file: Path to save metadata JSON
        api_key: OpenAI API key
        model: Embedding model to use
        
    Returns:
        Tuple of (faiss_index, metadata_list)
    """
    print("📌 Loading all chunks from JSON files...")
    
    all_chunks = []
    for file_path in chunk_files:
        chunks = load_chunks_from_json(file_path)
        file_name = Path(file_path).name
        print(f"   ➕ Loaded {len(chunks)} chunks from {file_name}")
        all_chunks.extend(chunks)
    
    print(f"\n✅ Total combined chunks: {len(all_chunks)}")
    
    # Extract texts for embedding
    chunks_text = [c["contextualized_text"] for c in all_chunks]
    
    # Generate embeddings
    print("✨ Generating OpenAI embeddings...")
    embedder = DocumentEmbedder(api_key=api_key, model=model)
    embeddings = embedder.embed_texts(chunks_text)
    
    # Create FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    # Save FAISS index
    faiss.write_index(index, vector_db_file)
    print(f"✅ FAISS index saved: {vector_db_file}")
    
    # Prepare and save metadata
    metadata = []
    for c in all_chunks:
        metadata.append({
            "text": c.get("contextualized_text") or c.get("summary") or c.get("text", ""),
            "source_type": c.get("source_type", "RFP"),
            "vendor_name": c.get("vendor_name", None),
            "page_number": c.get("page_number", None),
            "headings": c.get("headings", []),
            "is_capability_analysis": "_capability_analysis" in str(Path(file_path).name)
        })
    
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"✅ Metadata saved: {metadata_file}")
    
    print(f"\n🎯 Embedded {len(chunks_text)} total chunks")
    print(f"📊 Vector dimension: {dimension}")
    
    return index, metadata


def create_embeddings_from_rfp_and_vendors(rfp_chunks_file: str,
                                           vendor_chunks_files: List[str],
                                           output_dir: str,
                                           vector_db_name: str = "chunks_faiss.index",
                                           metadata_name: str = "chunks_metadata.json",
                                           api_key: str = None,
                                           model: str = DEFAULT_EMBEDDING_MODEL) -> tuple:
    """
    Create embeddings from RFP and vendor chunks.
    
    Args:
        rfp_chunks_file: Path to RFP chunks JSON
        vendor_chunks_files: List of paths to vendor chunks JSON files
        output_dir: Directory to save outputs
        vector_db_name: Name for FAISS index file
        metadata_name: Name for metadata JSON file
        api_key: OpenAI API key
        model: Embedding model to use
        
    Returns:
        Tuple of (faiss_index, metadata_list)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Combine RFP + vendor chunk files + vendor capability analyses (if any)
    all_files = [rfp_chunks_file] + vendor_chunks_files

    # Search for capability analysis files in same directory
    capability_files = []
    for vf in vendor_chunks_files:
        vendor_name = Path(vf).stem.replace("_chunks", "")
        possible_path = Path(vf).parent / f"{vendor_name}_capability_analysis.json"
        if possible_path.exists():
            capability_files.append(str(possible_path))

    if capability_files:
        print(f"➕ Including {len(capability_files)} vendor capability analysis files in embeddings")
        all_files += capability_files

    
    vector_db_file = str(output_path / vector_db_name)
    metadata_file = str(output_path / metadata_name)
    
    return create_embeddings_and_index(
        all_files,
        vector_db_file,
        metadata_file,
        api_key,
        model
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        chunk_files = sys.argv[1:-2]  # All but last 2 args are chunk files
        vector_db_file = sys.argv[-2]
        metadata_file = sys.argv[-1]
        
        create_embeddings_and_index(
            chunk_files,
            vector_db_file,
            metadata_file
        )
    else:
        print("Usage: python embeder.py <chunk_file1> [chunk_file2 ...] <vector_db_file> <metadata_file>")