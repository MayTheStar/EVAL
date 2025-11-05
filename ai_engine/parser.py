"""
RFP Hybrid Chunker + Token-based Merge Pass + Text Cleaning
- Cleans extracted text BEFORE token counting & merging
- Preserves Docling structural segmentation
- Merges small chunks forward until >= MIN_TOKENS or would exceed MAX_TOKENS
"""

import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from transformers import AutoTokenizer
import argparse


# -----------------------
# Configuration
# -----------------------
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"  # tokenizer for token counts
MIN_TOKENS = 512
MAX_TOKENS = 1024
TXT_OUTPUT = "/Users/maybader/EVAL/ai_engine/output_chunks.txt"
JSON_OUTPUT = "/Users/maybader/EVAL/ai_engine/output_chunks.json"
PDF_PATH = "sample_rfp.pdf"


# -----------------------
# Cleaning Function
# -----------------------
def clean_text(text: str) -> str:
    """Light & safe cleaning that preserves structure."""
    if not text:
        return ""
    # Remove multiple spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)
    # Fix hyphenated word breaks “develop-\nment” → “development”
    text = re.sub(r"-\s*\n\s*", "", text)
    # Normalize line breaks: allow max 2 in a row
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove stray bullet characters
    text = re.sub(r"([•·●]+)\s*", "", text)
    return text.strip()


# -----------------------
# Helpers
# -----------------------
def safe_meta(chunk) -> Dict[str, Any]:
    m = getattr(chunk, "meta", {}) or {}
    if isinstance(m, dict):
        return m
    try:
        return dict(m)
    except Exception:
        return {}


def extract_page_number(chunk) -> Optional[int]:
    meta = safe_meta(chunk)
    if "page_number" in meta:
        return meta["page_number"]
    for alt in ("page", "page_num", "pg", "page_index", "pageno"):
        if alt in meta:
            return meta[alt]
    parent = getattr(chunk, "parent", None)
    while parent is not None:
        pm = safe_meta(parent)
        if "page_number" in pm:
            return pm["page_number"]
        for alt in ("page", "page_num", "pg", "page_index", "pageno"):
            if alt in pm:
                return alt
        parent = getattr(parent, "parent", None)
    return None


def get_parent_headings(chunk, max_levels: int = 10) -> List[str]:
    heading_keys = [
        "heading", "title", "section_title", "heading_text",
        "h1", "h2", "h3", "name", "section", "caption", "headings"
    ]
    headings, seen = [], set()
    meta = safe_meta(chunk)

    for key in heading_keys:
        if key in meta and meta[key]:
            val = " > ".join(val for val in meta[key]) if isinstance(meta[key], (list, tuple)) else str(meta[key])
            val = val.strip()
            if val and val not in seen:
                headings.append(val)
                seen.add(val)

    parent = getattr(chunk, "parent", None)
    levels = 0
    while parent is not None and levels < max_levels:
        pm = safe_meta(parent)
        for key in heading_keys:
            if key in pm and pm[key]:
                val = " > ".join(val for val in pm[key]) if isinstance(pm[key], (list, tuple)) else str(pm[key])
                val = val.strip()
                if val and val not in seen:
                    headings.insert(0, val)
                    seen.add(val)
        parent = getattr(parent, "parent", None)
        levels += 1

    return headings


# -----------------------
# Chunking + Cleaning
# -----------------------
def chunk_document(pdf_path: str, tokenizer) -> List[dict]:
    print(f"📄 Converting document: {pdf_path}")
    converter = DocumentConverter()
    doc = converter.convert(pdf_path).document

    print("🧩 Chunking with HybridChunker...")
    chunker = HybridChunker(tokenizer=tokenizer, max_tokens=MAX_TOKENS, merge_peers=True)

    raw_chunks = list(chunker.chunk(doc))
    chunk_dicts = []

    for idx, ch in enumerate(raw_chunks):
        # CLEAN THE TEXT BEFORE token counting & merging
        raw_text = getattr(ch, "text", "") or ""
        text = clean_text(raw_text)

        try:
            contextual = clean_text(chunker.contextualize(chunk=ch))
        except Exception:
            contextual = text

        try:
            token_ids = tokenizer.encode(text, add_special_tokens=False)
            token_count = len(token_ids)
        except Exception:
            token_count = max(1, len(text.split()))

        chunk_dicts.append({
            "orig_index": idx,
            "text": text,
            "contextualized_text": contextual,
            "token_count": token_count,
            "page_number": extract_page_number(ch),
            "headings": get_parent_headings(ch),
            "orig_chunk": ch
        })

    print(f"✅ Generated {len(chunk_dicts)} raw chunks (cleaned).")
    return chunk_dicts, chunker


# -----------------------
# Merge pass (same code)
# -----------------------
def merge_small_chunks_forward(chunk_dicts: List[dict],
                               tokenizer,
                               min_tokens: int = MIN_TOKENS,
                               max_tokens: int = MAX_TOKENS) -> List[dict]:

    merged = []
    buffer = None

    def make_buffer_from_chunk(c):
        return {
            "orig_indices": [c["orig_index"]],
            "text": c["text"],
            "contextualized_texts": [c["contextualized_text"]],
            "token_count": c["token_count"],
            "pages": [c["page_number"]] if c["page_number"] else [],
            "headings": list(c["headings"]) if c["headings"] else []
        }

    def finalize_buffer(buf):
        combined_context = "\n\n".join(buf["contextualized_texts"])
        rep_page = buf["pages"][0] if buf["pages"] else None
        uniq_headings = []
        seen = set()
        for h in buf["headings"]:
            if h and h not in seen:
                uniq_headings.append(h)
                seen.add(h)
        return {
            "orig_indices": buf["orig_indices"],
            "text": buf["text"],
            "contextualized_text": combined_context,
            "token_count": buf["token_count"],
            "page_number": rep_page,
            "headings": uniq_headings
        }

    i = 0
    while i < len(chunk_dicts):
        current = chunk_dicts[i]

        if buffer is None:
            buffer = make_buffer_from_chunk(current)
            i += 1
            continue

        if buffer["token_count"] >= min_tokens:
            merged.append(finalize_buffer(buffer))
            buffer = None
            continue

        next_chunk = current
        tentative = buffer["token_count"] + next_chunk["token_count"]

        if tentative <= max_tokens:
            buffer["orig_indices"].append(next_chunk["orig_index"])
            buffer["text"] += "\n\n" + next_chunk["text"]
            buffer["contextualized_texts"].append(next_chunk["contextualized_text"])
            buffer["token_count"] = tentative
            if next_chunk["page_number"]:
                buffer["pages"].append(next_chunk["page_number"])
            buffer["headings"].extend(next_chunk["headings"] or [])
            i += 1
        else:
            merged.append(finalize_buffer(buffer))
            buffer = None

    if buffer:
        merged.append(finalize_buffer(buffer))

    print(f"✅ Merge pass complete: {len(chunk_dicts)} -> {len(merged)} chunks")
    return merged


# -----------------------
# Save outputs (unchanged)
# -----------------------
def save_txt(merged_chunks: List[dict], out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        for idx, mc in enumerate(merged_chunks):
            f.write("="*60 + "\n")
            f.write(f"CHUNK {idx}\n")
            f.write("="*60 + "\n")
            f.write(f"Orig indices: {mc['orig_indices']}\n")
            f.write(f"Page: {mc['page_number']}\n")
            f.write(f"Token Count: {mc['token_count']}\n")
            if mc["headings"]:
                f.write(f"Headings: {' > '.join(mc['headings'])}\n")
            f.write("-"*60 + "\n\n")
            f.write(mc["contextualized_text"] + "\n\n")
    print(f"✅ TXT saved: {out_path}")


def save_json(merged_chunks: List[dict], out_path: str):
    with open(out_path, "w", encoding="utf-8") as jf:
        json.dump(merged_chunks, jf, indent=2, ensure_ascii=False)
    print(f"✅ JSON saved: {out_path}")


# -----------------------
# Main
# -----------------------
def main():
    print("🔁 Loading tokenizer:", MODEL_ID)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

    chunk_dicts, _ = chunk_document(PDF_PATH, tokenizer)

    merged = merge_small_chunks_forward(chunk_dicts, tokenizer)

    save_txt(merged, TXT_OUTPUT)
    save_json(merged, JSON_OUTPUT)

    print("\n🎯 Done — Clean text + better merging ready for RAG ingestion!")


if __name__ == "__main__":
    main()
