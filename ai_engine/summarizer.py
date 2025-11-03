import json
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# ----------------------------
# Configuration
# ----------------------------
CHUNK_FILE = Path("/Users/rayana/EVAL/ai_engine/output_chunks.txt")
OUTPUT_FILE = Path("/Users/rayana/EVAL/ai_engine/rfp_chunk_analysis_local.json")
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
TEMPERATURE = 0.0

# Use Apple GPU if available
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Using device: {DEVICE}")

# ----------------------------
# Load model & tokenizer locally
# ----------------------------
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="auto",
    torch_dtype=torch.float16,
)

generator = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=1024,
    do_sample=False,
    temperature=TEMPERATURE,
)

# ----------------------------
# Helper functions
# ----------------------------
def read_chunks(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
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

def analyze_chunk(chunk_text):
    prompt = f"""
You are an expert in analyzing government and corporate RFPs. Extract all explicit and implied requirements. 

Instructions:
1. Extract all requirements mentioned (explicit and implied) as a list.
2. Summarize the text in 2–3 sentences.
3. Identify evaluation labels or keywords (e.g., "Technical", "Financial", "Timeline", "Compliance").

Output strictly in JSON format:

{{
    "requirements": [],
    "summary": "",
    "evaluation_labels": []
}}

Text:
{chunk_text}
"""
    try:
        result = generator(prompt, max_new_tokens=1024, temperature=TEMPERATURE)[0]["generated_text"]
        # Parse JSON from output
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        chunk_output = json.loads(result[json_start:json_end])
    except Exception as e:
        print(f"⚠️ Error analyzing chunk: {e}")
        chunk_output = {
            "requirements": [],
            "summary": "",
            "evaluation_labels": [],
            "raw_model_output": result if 'result' in locals() else ""
        }
    else:
        chunk_output["raw_model_output"] = result
    return chunk_output

# ----------------------------
# Main function
# ----------------------------
def main():
    chunks = read_chunks(CHUNK_FILE)
    print(f"Total chunks available: {len(chunks)}")

    all_chunks_data = []
    START_CHUNK = 29  # Start from chunk 30 (0-based index)

    for i, chunk_text in enumerate(chunks[START_CHUNK:], start=START_CHUNK):
 
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

    # Save results
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks_data, f, indent=4, ensure_ascii=False)

    print(f"\n✓ Local analysis complete. Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
