import json
from openai import OpenAI
from pathlib import Path
import os
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
MODEL = "gpt-4o-mini"
TEMPERATURE = 0

# ----------------------------
# Helper: Read chunks from file
# ----------------------------
def read_chunks(file_path: str):
    """Read chunks separated by ===CHUNK=== markers in a text file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    chunks = content.split("="*60)
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
# Analyze a single chunk
# ----------------------------
def analyze_chunk(chunk_text: str):
    prompt = f"""
You are an expert in analyzing government and corporate RFPs. Your task is to extract **all explicit and implicit requirements** from the following text.  

Instructions:

1. Extract all **requirements** (explicit + implicit).  
2. Summarize in **2–3 sentences** under "summary".  
3. Identify **evaluation labels/keywords** (e.g., "Technical", "Financial", "Timeline", "Compliance") under "evaluation_labels".  

**Output format:** Return valid JSON:

{{
    "requirements": [],
    "summary": "",
    "evaluation_labels": []
}}

Text to analyze:
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
# Main processing function
# ----------------------------
def process_chunks(chunk_file_path: str):
    """
    Process any chunk file dynamically and return analysis JSON path.
    """
    chunk_file = Path(chunk_file_path)
    if not chunk_file.is_file():
        raise FileNotFoundError(f"Chunk file not found: {chunk_file_path}")

    chunks = read_chunks(chunk_file)
    print(f"Total chunks available: {len(chunks)}")

    all_chunks_data = []

    for i, chunk_text in enumerate(chunks):
        print(f"\nAnalyzing chunk {i+1}/{len(chunks)}...")
        chunk_result = analyze_chunk(chunk_text)
        chunk_data = {
            "chunk_index": i,
            "text": chunk_text,
            "requirements": chunk_result.get("requirements", []),
            "summary": chunk_result.get("summary", ""),
            "evaluation_labels": chunk_result.get("evaluation_labels", []),
            "raw_model_output": chunk_result.get("raw_model_output", "")
        }
        all_chunks_data.append(chunk_data)

    # Auto-generate output file name based on input
    output_file = chunk_file.parent / f"{chunk_file.stem.replace(" ", "")}_analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks_data, f, indent=4, ensure_ascii=False)

    print(f"\n✓ Analysis complete. Results saved to {output_file}")
    return output_file

# # ----------------------------
# # Example usage
# # ----------------------------
# if __name__ == "__main__":
#     test_chunk_file = "/path/to/rfp_chunks.txt"
#     process_chunks(test_chunk_file)
