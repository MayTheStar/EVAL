import json
import os
import glob
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found in environment. Please set OPENAI_API_KEY in your .env file.")

client = OpenAI(api_key=OPENAI_API_KEY)

# ----------------------------
# Configuration
# ----------------------------
VENDOR_JSON_PATH = "/Users/maybader/EVAL/ai_engine/*_chunks.json"
MODEL = "gpt-4o-mini"
TEMPERATURE = 0


# ----------------------------
# Analyze Vendor Capabilities
# ----------------------------
def analyze_vendor_chunk(chunk_text):
    """Extract vendor capabilities, commitments, and deliverables."""
    prompt = f"""
You are an expert in evaluating vendor proposals in response to RFPs.

Your task is to identify all **capabilities, commitments, deliverables, and claims** that the vendor makes in the following text.

Instructions:
1. Extract detailed **capabilities** — what the vendor can do or provide.
2. Extract **commitments/deliverables** — what the vendor promises to deliver or guarantee.
3. Extract any **unique differentiators or strengths**.
4. Provide a short **summary (2–3 sentences)**.
5. Categorize the content into **evaluation_labels** such as: Technical, Functional, Financial, Compliance, Security, or Other.

Return valid JSON only in this exact structure:

{{
    "capabilities": [],
    "commitments": [],
    "differentiators": [],
    "summary": "",
    "evaluation_labels": []
}}

Now analyze this text:
{chunk_text}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE
        )
        content = response.choices[0].message.content
        chunk_output = json.loads(content)
    except Exception as e:
        print(f"⚠️ Error analyzing chunk: {e}")
        chunk_output = {
            "capabilities": [],
            "commitments": [],
            "differentiators": [],
            "summary": "",
            "evaluation_labels": [],
            "raw_model_output": content if 'content' in locals() else ""
        }
    else:
        chunk_output["raw_model_output"] = content

    return chunk_output


# ----------------------------
# Main Processing
# ----------------------------
def main():
    vendor_json_files = glob.glob(VENDOR_JSON_PATH)
    if not vendor_json_files:
        print("⚠️ No vendor chunk files found.")
        return

    for vendor_file in vendor_json_files:
        if "output_chunks.json" in vendor_file:
            continue  # Skip RFP file
        vendor_name = Path(vendor_file).stem.replace("_chunks", "")
        print(f"\n🔹 Analyzing vendor: {vendor_name}")

        with open(vendor_file, "r", encoding="utf-8") as vf:
            vendor_chunks = json.load(vf)

        vendor_results = []
        for i, chunk in enumerate(vendor_chunks):
            text = chunk.get("contextualized_text") or chunk.get("text", "")
            print(f"   ↳ Chunk {i+1}/{len(vendor_chunks)}")
            result = analyze_vendor_chunk(text)
            vendor_results.append(result)

        # Save results
        output_path = Path(vendor_file).parent / f"{vendor_name}_capability_analysis.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(vendor_results, f, indent=4, ensure_ascii=False)
        print(f"✅ Saved capability analysis → {output_path}")

    print("\n🎯 All vendor capability analyses completed!")


# ----------------------------
# Run
# ----------------------------
if __name__ == "__main__":
    main()
