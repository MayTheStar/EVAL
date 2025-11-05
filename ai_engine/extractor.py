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

# Create client
client = OpenAI(api_key=OPENAI_API_KEY)

# ----------------------------
# Configuration
# ----------------------------
CHUNK_FILE = Path("/Users/maybader/EVAL/ai_engine/output_chunks.txt")   # RFP chunks (text)
OUTPUT_FILE = Path("/Users/maybader/EVAL/ai_engine/rfp_chunk_analysis.json")
MODEL = "gpt-4o-mini"
TEMPERATURE = 0


# ----------------------------
# Helper function for RFP chunks
# ----------------------------
def read_chunks(file_path):
    """Read chunks separated by ===CHUNK=== markers in a text file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    chunks = content.split("=" * 60)
    processed_chunks = []

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.splitlines()
        if lines and lines[0].startswith("CHUNK"):
            text = "\n".join(lines[1:]).strip()
        else:
            text = chunk
        processed_chunks.append(text)
    return processed_chunks


# ----------------------------
# Analyze a chunk using OpenAI
# ----------------------------
def analyze_chunk(chunk_text, prompt_type="RFP"):
    if prompt_type == "RFP":
        role_description = (
            "You are an expert in analyzing government and corporate RFPs. "
            "Your task is to extract all explicit and implied requirements."
        )
    else:
        role_description = (
            "You are an expert analyzing vendor proposals in response to RFPs. "
            "Extract all capabilities, commitments, or deliverables mentioned by the vendor."
        )

    prompt = f"""
{role_description}

Instructions:
1. Extract key actionable points or requirements.
2. Summarize the text in 2–3 sentences under "summary".
3. Identify key focus areas under "evaluation_labels" (e.g., Technical, Financial, Compliance).

Return valid JSON:
{{
    "requirements": [],
    "summary": "",
    "evaluation_labels": []
}}

Now analyze:
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
            "requirements": [],
            "summary": "",
            "evaluation_labels": [],
            "raw_model_output": content if 'content' in locals() else ""
        }
    else:
        chunk_output["raw_model_output"] = content

    return chunk_output


# ----------------------------
# Main processing
# ----------------------------
def main():
    # --- RFP ---
    chunks = read_chunks(CHUNK_FILE)
    print(f"📄 Total RFP chunks: {len(chunks)}")

    rfp_results = []
    for i, chunk_text in enumerate(chunks):
        print(f"\nAnalyzing RFP chunk {i+1}/{len(chunks)}...")
        result = analyze_chunk(chunk_text, prompt_type="RFP")
        rfp_results.append(result)

    rfp_output_file = OUTPUT_FILE.parent / "rfp_chunk_analysis_all.json"
    with open(rfp_output_file, "w", encoding="utf-8") as f:
        json.dump(rfp_results, f, indent=4, ensure_ascii=False)
    print(f"✅ RFP analysis saved to {rfp_output_file}")

    # --- Vendors ---
    vendor_json_files = glob.glob("/Users/maybader/EVAL/ai_engine/*_chunks.json")
    for vendor_file in vendor_json_files:
        if "output_chunks.json" in vendor_file:  # Skip RFP chunks JSON
            continue
        vendor_name = Path(vendor_file).stem.replace("_chunks", "")
        print(f"\n🔹 Analyzing vendor: {vendor_name}")

        with open(vendor_file, "r", encoding="utf-8") as vf:
            vendor_chunks = json.load(vf)

        vendor_results = []
        for i, chunk in enumerate(vendor_chunks):
            text = chunk.get("contextualized_text") or chunk.get("text", "")
            print(f"   ↳ Chunk {i+1}/{len(vendor_chunks)}")
            result = analyze_chunk(text, prompt_type="Vendor")
            vendor_results.append(result)

        vendor_output_file = Path(vendor_file).parent / f"{vendor_name}_analysis.json"
        with open(vendor_output_file, "w", encoding="utf-8") as f:
            json.dump(vendor_results, f, indent=4, ensure_ascii=False)
        print(f"✅ Vendor analysis saved to {vendor_output_file}")


# ----------------------------
# Run
# ----------------------------
if __name__ == "__main__":
    main()
