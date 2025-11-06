"""
vendor_capability_extractor.py
AI-powered extraction of vendor capabilities, commitments, and differentiators.
Integrates seamlessly with EVAL's RFP Analysis System.
"""

import json
import os
from pathlib import Path
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found. Set it in your .env file.")

client = OpenAI(api_key=OPENAI_API_KEY)

# ----------------------------
# Configuration
# ----------------------------
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0


# ----------------------------
# Core Analysis Logic
# ----------------------------
def analyze_vendor_chunk(chunk_text: str, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE) -> Dict:
    """Extract vendor capabilities, commitments, differentiators, and evaluation labels."""
    prompt = f"""
You are an expert in analyzing vendor proposals in response to RFPs.

Your task is to extract all **capabilities**, **commitments/deliverables**, and **unique differentiators** that the vendor claims.
You must categorize findings and summarize the text.

Return valid JSON only in the following structure:
{{
    "capabilities": [],
    "commitments": [],
    "differentiators": [],
    "summary": "",
    "evaluation_labels": []
}}

Analyze this vendor content:
{chunk_text}
"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        content = response.choices[0].message.content
        result = json.loads(content)
    except Exception as e:
        print(f"⚠️ Error analyzing chunk: {e}")
        result = {
            "capabilities": [],
            "commitments": [],
            "differentiators": [],
            "summary": "",
            "evaluation_labels": [],
            "raw_model_output": content if 'content' in locals() else ""
        }
    else:
        result["raw_model_output"] = content
    return result


def analyze_vendor_file(vendor_json_path: str, model: str = DEFAULT_MODEL) -> List[Dict]:
    """Analyze all chunks of a vendor JSON file."""
    vendor_name = Path(vendor_json_path).stem.replace("_chunks", "")
    print(f"\n🔹 Analyzing vendor: {vendor_name}")

    with open(vendor_json_path, "r", encoding="utf-8") as vf:
        vendor_chunks = json.load(vf)

    results = []
    for i, chunk in enumerate(vendor_chunks):
        text = chunk.get("contextualized_text") or chunk.get("text", "")
        print(f"   ↳ Chunk {i+1}/{len(vendor_chunks)}")
        result = analyze_vendor_chunk(text, model=model)
        results.append(result)

    output_path = Path(vendor_json_path).parent / f"{vendor_name}_capability_analysis.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print(f"✅ Saved capability analysis → {output_path}")
    return results


def analyze_all_vendors(vendor_folder: str, model: str = DEFAULT_MODEL):
    """Analyze all vendor JSON chunk files in a folder."""
    vendor_files = list(Path(vendor_folder).glob("*_chunks.json"))
    if not vendor_files:
        print("⚠️ No vendor chunk files found.")
        return

    for vendor_file in vendor_files:
        analyze_vendor_file(str(vendor_file), model=model)

    print("\n🎯 All vendor capability analyses completed!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        vendor_folder = sys.argv[1]
        analyze_all_vendors(vendor_folder)
    else:
        print("Usage: python vendor_capability_extractor.py <vendor_folder>")
