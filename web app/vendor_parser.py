"""
Vendor Response Parser
Processes vendor response documents (PDF, DOC, DOCX) using the same chunking pipeline as RFP parsing.
"""

import json
from pathlib import Path
from typing import List, Dict
from parser import chunk_document, merge_small_chunks_forward, save_json, MIN_TOKENS, MAX_TOKENS, MODEL_ID
from transformers import AutoTokenizer


def process_vendor_response(vendor_file_path: str, vendor_name: str, output_json_path: str,
                            min_tokens: int = MIN_TOKENS, max_tokens: int = MAX_TOKENS) -> List[Dict]:
    """
    Process a single vendor response document.
    
    Args:
        vendor_file_path: Path to vendor response file (PDF, DOC, DOCX)
        vendor_name: Name identifier for the vendor
        output_json_path: Path to save the output JSON
        min_tokens: Minimum tokens per chunk
        max_tokens: Maximum tokens per chunk
        
    Returns:
        List of processed chunks with vendor metadata
    """
    print(f"\n🔹 Processing vendor: {vendor_name}")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    
    try:
        # Step 1: Use the same chunking logic as RFP parsing
        chunks, _ = chunk_document(vendor_file_path, tokenizer, min_tokens, max_tokens)
        
        # Step 2: Merge small chunks
        merged = merge_small_chunks_forward(chunks, tokenizer, min_tokens, max_tokens)
        
        # Step 3: Add metadata for vendor
        for c in merged:
            c["source_type"] = "VendorResponse"
            c["vendor_name"] = vendor_name
        
        # Step 4: Save JSON file for this vendor
        save_json(merged, output_json_path)
        print(f"✅ Saved {vendor_name} chunks → {output_json_path}")
        
        return merged
        
    except Exception as e:
        print(f"❌ Error processing {vendor_name}: {e}")
        raise


def process_multiple_vendors(vendor_files: List[tuple], output_dir: str,
                             min_tokens: int = MIN_TOKENS, max_tokens: int = MAX_TOKENS) -> Dict[str, List[Dict]]:
    """
    Process multiple vendor response documents.
    
    Args:
        vendor_files: List of tuples (file_path, vendor_name)
        output_dir: Directory to save output files
        min_tokens: Minimum tokens per chunk
        max_tokens: Maximum tokens per chunk
        
    Returns:
        Dictionary mapping vendor names to their processed chunks
    """
    print("📦 Starting Vendor Response Parsing...")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    vendor_results = {}
    
    for file_path, vendor_name in vendor_files:
        output_json = output_path / f"{vendor_name}_chunks.json"
        try:
            chunks = process_vendor_response(
                file_path, 
                vendor_name, 
                str(output_json),
                min_tokens,
                max_tokens
            )
            vendor_results[vendor_name] = chunks
        except Exception as e:
            print(f"⚠️ Skipping {vendor_name} due to error: {e}")
            continue
    
    print(f"\n🎯 Processed {len(vendor_results)} vendor responses successfully!")
    return vendor_results


def process_vendor_folder(vendor_folder: str, output_dir: str,
                         min_tokens: int = MIN_TOKENS, max_tokens: int = MAX_TOKENS) -> Dict[str, List[Dict]]:
    """
    Process all vendor files in a folder.
    
    Args:
        vendor_folder: Path to folder containing vendor response files
        output_dir: Directory to save output files
        min_tokens: Minimum tokens per chunk
        max_tokens: Maximum tokens per chunk
        
    Returns:
        Dictionary mapping vendor names to their processed chunks
    """
    vendor_path = Path(vendor_folder)
    if not vendor_path.exists():
        raise ValueError(f"Vendor folder not found: {vendor_folder}")
    
    supported_formats = ["*.pdf", "*.doc", "*.docx"]
    vendor_files = []
    
    for pattern in supported_formats:
        for file_path in vendor_path.glob(pattern):
            vendor_name = file_path.stem
            vendor_files.append((str(file_path), vendor_name))
    
    if not vendor_files:
        print(f"⚠️ No vendor files found in: {vendor_folder}")
        return {}
    
    return process_multiple_vendors(vendor_files, output_dir, min_tokens, max_tokens)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        vendor_folder = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
        process_vendor_folder(vendor_folder, output_dir)
    else:
        print("Usage: python vendor_parser.py <vendor_folder> [output_directory]")