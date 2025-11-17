"""
Vendor Response Parser (Dynamic Upload Version)
Processes vendor response documents (PDF, DOC, DOCX)
using the same chunking pipeline as RFP parsing.

"""

import json
from pathlib import Path
from typing import List, Dict, Union
from parser import (
    chunk_document,
    merge_small_chunks_forward,
    save_json,
    MIN_TOKENS,
    MAX_TOKENS,
    MODEL_ID,
)
from transformers import AutoTokenizer


# ===============================================================
# Process a Single Vendor Response
# ===============================================================
def process_vendor_response(
    vendor_file_path: Union[str, Path],
    vendor_name: str,
    output_dir: Union[str, Path],
    min_tokens: int = MIN_TOKENS,
    max_tokens: int = MAX_TOKENS,
) -> List[Dict]:
    """
    Process a single uploaded vendor response file (PDF, DOC, DOCX).

    Args:
        vendor_file_path: Path to the uploaded vendor response file.
        vendor_name: Name identifier for the vendor (derived from upload).
        output_dir: Directory to save the output JSON file.
        min_tokens: Minimum tokens per chunk.
        max_tokens: Maximum tokens per chunk.

    Returns:
        List of processed chunks with vendor metadata.
    """
    vendor_file_path = Path(vendor_file_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_json_path = output_dir / f"{vendor_name}_chunks.json"
    print(f"\n🔹 Processing uploaded vendor file: {vendor_file_path.name}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

    try:
        # Step 1: Chunk document using same RFP logic
        chunks, _ = chunk_document(str(vendor_file_path), tokenizer, min_tokens, max_tokens)

        # Step 2: Merge small chunks
        merged = merge_small_chunks_forward(chunks, tokenizer, min_tokens, max_tokens)

        # Step 3: Add vendor metadata
        for c in merged:
            # c["source_type"] = "VendorResponse"
            c["vendor_name"] = vendor_name

        # Step 4: Save to JSON output file
        save_json(merged, str(output_json_path))
        print(f"✅ Saved processed chunks for {vendor_name} → {output_json_path}")

        return merged

    except Exception as e:
        print(f"❌ Error processing {vendor_name}: {e}")
        raise


# ===============================================================
# Process Multiple Vendor Responses
# ===============================================================
def process_multiple_vendors(
    vendor_files: List[tuple],
    output_dir: Union[str, Path],
    min_tokens: int = MIN_TOKENS,
    max_tokens: int = MAX_TOKENS,
) -> Dict[str, List[Dict]]:
    """
    Process multiple uploaded vendor files (kept same name for compatibility).

    Args:
        vendor_files: List of tuples (file_path, vendor_name)
                      Example: [("uploads/vendorA.pdf", "VendorA"), ("uploads/vendorB.docx", "VendorB")]
        output_dir: Directory to save output JSON files.
        min_tokens: Minimum tokens per chunk.
        max_tokens: Maximum tokens per chunk.

    Returns:
        Dictionary mapping vendor names to their processed chunks.
    """
    print("📦 Starting dynamic vendor response parsing...")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    for file_path, vendor_name in vendor_files:
        try:
            chunks = process_vendor_response(
                vendor_file_path=file_path,
                vendor_name=vendor_name,
                output_dir=output_dir,
                min_tokens=min_tokens,
                max_tokens=max_tokens,
            )
            results[vendor_name] = chunks
        except Exception as e:
            print(f"⚠️ Skipping {vendor_name} due to error: {e}")
            continue

    print(f"\n🎯 Successfully processed {len(results)} vendor responses!")
    return results


# ===============================================================
# Process Vendor Folder (Legacy Wrapper)
# ===============================================================
def process_vendor_folder(
    vendor_folder: str,
    output_dir: str,
    min_tokens: int = MIN_TOKENS,
    max_tokens: int = MAX_TOKENS,
) -> Dict[str, List[Dict]]:
    """
    Backward-compatible wrapper for older code that expects a folder-based call.
    Instead of scanning folders, this version raises an error to ensure
    dynamic upload workflow is used.
    """
    raise NotImplementedError(
        "⚠️ process_vendor_folder() is deprecated. "
        "Use process_multiple_vendors([(file_path, vendor_name), ...], output_dir) instead."
    )


# ===============================================================
# CLI Entry Point (Disabled)
# ===============================================================
if __name__ == "__main__":
    print("⚠️ CLI mode disabled. This script is designed for dynamic upload usage only.")
