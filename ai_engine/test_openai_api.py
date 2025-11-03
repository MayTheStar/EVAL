# import json
# from openai import OpenAI
# from pathlib import Path
# import os
# from dotenv import load_dotenv

# # ----------------------------
# # Load environment variables
# # ----------------------------
# load_dotenv()  # Load variables from .env file
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# if not OPENAI_API_KEY:
#     raise ValueError("OpenAI API key not found in environment. Please set OPENAI_API_KEY in your .env file.")

# # Create client
# client = OpenAI(api_key=OPENAI_API_KEY)

# # ----------------------------
# # Configuration
# # ----------------------------
# CHUNK_FILE = Path("/Users/rayana/EVAL/ai_engine/output_chunks.txt")
# OUTPUT_FILE = Path("/Users/rayana/EVAL/ai_engine/rfp_chunk_analysis.json")
# MODEL = "gpt-4"
# TEMPERATURE = 0

# # ----------------------------
# # Helper function to read chunks from a file
# # ----------------------------
# def read_chunks(file_path):
#     """Read chunks separated by ===CHUNK=== markers in a text file"""
#     with open(file_path, 'r', encoding='utf-8') as f:
#         content = f.read()

#     chunks = content.split("="*60)
#     processed_chunks = []

#     for chunk in chunks:
#         chunk = chunk.strip()
#         if not chunk:
#             continue
#         lines = chunk.splitlines()
#         if lines and lines[0].startswith("CHUNK"):
#             text = "\n".join(lines[1:]).strip()
#         else:
#             text = chunk
#         processed_chunks.append(text)
#     return processed_chunks

# # ----------------------------
# # Function to analyze a chunk with OpenAI
# # ----------------------------
# def analyze_chunk(chunk_text):
#     prompt = f"""
# You are an expert in analyzing government and corporate RFPs. Your task is to extract all actionable information from a potentially long and complex chunk of text. Focus on capturing **explicit, implicit, and hidden requirements**.

# Follow these steps for this chunk:

# 1. **Scan the text carefully** and extract all **requirements**, organizing them into these five categories:
#    - **Evaluation Criteria**
#    - **Mandatory Eligibility Criteria**
#    - **Qualification Criteria**
#    - **Scope of Services**
#    - **Deliverables**

# 2. Summarize the chunk in **2-3 sentences** under **summary**.
# 3. Identify any **labels or keywords** describing the type of requirement or focus of the chunk under **evaluation_labels**.

# Return **strictly valid JSON** in the format:
# {{
#     "requirements": {{
#         "Evaluation Criteria": [],
#         "Mandatory Eligibility Criteria": [],
#         "Qualification Criteria": [],
#         "Scope of Services": [],
#         "Deliverables": []
#     }},
#     "summary": "",
#     "evaluation_labels": []
# }}

# **Now analyze the following chunk:**  
# {chunk_text}
# """
#     try:
#         response = client.chat.completions.create(
#             model=MODEL,
#             messages=[{"role": "user", "content": prompt}],
#             temperature=TEMPERATURE
#         )
#         content = response.choices[0].message.content
#         chunk_output = json.loads(content)
#     except Exception as e:
#         print(f"⚠️ Error analyzing chunk: {e}")
#         # Always return a valid structure even if the model fails
#         chunk_output = {
#             "requirements": {
#                 "Evaluation Criteria": [],
#                 "Mandatory Eligibility Criteria": [],
#                 "Qualification Criteria": [],
#                 "Scope of Services": [],
#                 "Deliverables": []
#             },
#             "summary": "",
#             "evaluation_labels": [],
#             "raw_model_output": content if 'content' in locals() else ""
#         }
#     else:
#         # Include raw model output for debugging
#         chunk_output["raw_model_output"] = content

#     return chunk_output

# def is_toc_chunk(chunk_text):
#     """
#     Detect if a chunk is a Table of Contents.
#     Heuristic: 
#     - Contains the phrase 'TABLE OF CONTENTS' (case-insensitive)
#     - OR many lines with dots and numbers
#     """
#     if "TABLE OF CONTENTS" in chunk_text.upper():
#         return True

#     lines = chunk_text.splitlines()
#     toc_lines = 0
#     for line in lines:
#         if '.' in line and any(char.isdigit() for char in line):
#             toc_lines += 1
#     if len(lines) > 0 and toc_lines / len(lines) > 0.5:
#         return True

#     return False


# # # ----------------------------
# # # Main processing
# # # ----------------------------
# # def main():
# #     chunks = read_chunks(CHUNK_FILE)
# #     print(f"Total chunks to analyze: {len(chunks)}")

# #     all_chunks_data = []

# #     for i, chunk_text in enumerate(chunks):
# #         if is_toc_chunk(chunk_text):
# #             print(f"Skipping chunk {i+1} (Table of Contents)")
# #             # Still save an empty record
# #             chunk_data = {
# #                 "chunk_index": i,
# #                 "text": chunk_text,
# #                 "requirements": {
# #                     "Evaluation Criteria": [],
# #                     "Mandatory Eligibility Criteria": [],
# #                     "Qualification Criteria": [],
# #                     "Scope of Services": [],
# #                     "Deliverables": []
# #                 },
# #                 "summary": "",
# #                 "evaluation_labels": [],
# #                 "raw_model_output": "Skipped (Table of Contents)"
# #             }
# #             all_chunks_data.append(chunk_data)
# #             continue

# #         print(f"\nAnalyzing chunk {i+1}/{len(chunks)}...")
# #         chunk_result = analyze_chunk(chunk_text)
# #         chunk_data = {
# #             "chunk_index": i,
# #             "text": chunk_text,
# #             "requirements": chunk_result.get("requirements", {
# #                 "Evaluation Criteria": [],
# #                 "Mandatory Eligibility Criteria": [],
# #                 "Qualification Criteria": [],
# #                 "Scope of Services": [],
# #                 "Deliverables": []
# #             }),
# #             "summary": chunk_result.get("summary", ""),
# #             "evaluation_labels": chunk_result.get("evaluation_labels", []),
# #             "raw_model_output": chunk_result.get("raw_model_output", "")
# #         }
# #         all_chunks_data.append(chunk_data)

# #     # Save all results
# #     with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
# #         json.dump(all_chunks_data, f, indent=4, ensure_ascii=False)

# #     print(f"\n✓ Chunk analysis complete. Results saved to {OUTPUT_FILE}")


# import random  # Add this at the top with your imports

# def main():
#     chunks = read_chunks(CHUNK_FILE)
#     print(f"Total chunks available: {len(chunks)}")

#     # Pick 10 random chunks for testing
#     if len(chunks) > 10:
#         test_chunks = random.sample(chunks, 10)
#     else:
#         test_chunks = chunks

#     all_chunks_data = []

#     for i, chunk_text in enumerate(test_chunks):
#         if is_toc_chunk(chunk_text):
#             print(f"Skipping chunk {i+1} (Table of Contents)")
#             # Still save an empty record
#             chunk_data = {
#                 "chunk_index": i,
#                 "text": chunk_text,
#                 "requirements": {
#                     "Evaluation Criteria": [],
#                     "Mandatory Eligibility Criteria": [],
#                     "Qualification Criteria": [],
#                     "Scope of Services": [],
#                     "Deliverables": []
#                 },
#                 "summary": "",
#                 "evaluation_labels": [],
#                 "raw_model_output": "Skipped (Table of Contents)"
#             }
#             all_chunks_data.append(chunk_data)
#             continue

#         print(f"\nAnalyzing chunk {i+1}/{len(test_chunks)}...")
#         chunk_result = analyze_chunk(chunk_text)
#         chunk_data = {
#             "chunk_index": i,
#             "text": chunk_text,
#             "requirements": chunk_result.get("requirements", {
#                 "Evaluation Criteria": [],
#                 "Mandatory Eligibility Criteria": [],
#                 "Qualification Criteria": [],
#                 "Scope of Services": [],
#                 "Deliverables": []
#             }),
#             "summary": chunk_result.get("summary", ""),
#             "evaluation_labels": chunk_result.get("evaluation_labels", []),
#             "raw_model_output": chunk_result.get("raw_model_output", "")
#         }
#         all_chunks_data.append(chunk_data)

#     # Save test results
#     test_output_file = OUTPUT_FILE.parent / "rfp_chunk_analysis_test.json"
#     with open(test_output_file, "w", encoding="utf-8") as f:
#         json.dump(all_chunks_data, f, indent=4, ensure_ascii=False)

#     print(f"\n✓ Test analysis complete. Results saved to {test_output_file}")


# if __name__ == "__main__":
#     main()






import json
from openai import OpenAI
from pathlib import Path
import os
from dotenv import load_dotenv
import random

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()  # Load variables from .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found in environment. Please set OPENAI_API_KEY in your .env file.")

# Create client
client = OpenAI(api_key=OPENAI_API_KEY)

# ----------------------------
# Configuration
# ----------------------------
CHUNK_FILE = Path("/Users/rayana/EVAL/ai_engine/output_chunks.txt")
OUTPUT_FILE = Path("/Users/rayana/EVAL/ai_engine/rfp_chunk_analysis.json")
MODEL = "gpt-3.5-turbo"
TEMPERATURE = 0

# ----------------------------
# Helper function to read chunks from a file
# ----------------------------
def read_chunks(file_path):
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
# Detect Table of Contents chunks
# ----------------------------
def is_toc_chunk(chunk_text):
    """
    Detect if a chunk is a Table of Contents.
    Heuristic: 
    - Contains 'TABLE OF CONTENTS' (case-insensitive)
    - OR many lines with dots and numbers
    """
    if "TABLE OF CONTENTS" in chunk_text.upper():
        return True

    lines = chunk_text.splitlines()
    toc_lines = 0
    for line in lines:
        if '.' in line and any(char.isdigit() for char in line):
            toc_lines += 1
    if len(lines) > 0 and toc_lines / len(lines) > 0.5:
        return True

    return False

# ----------------------------
# Analyze a chunk using OpenAI (new RFP prompt)
# ----------------------------
def analyze_chunk(chunk_text):
    prompt = f"""
You are an expert in analyzing government and corporate RFPs. Your task is to extract **all explicit and implied requirements** from the following text. Focus on capturing actionable information that a vendor must fulfill or that will be used to evaluate proposals.  

Instructions:

1. Extract all **requirements** mentioned in the text. Include both explicit and implied requirements.  
2. Summarize the text in **2–3 sentences** under "summary". Focus on the key objectives and context of the RFP.  
3. Identify any **evaluation labels or keywords** describing the type of requirement (e.g., "Technical", "Financial", "Timeline", "Compliance") under "evaluation_labels".  

**Output format:** Return a strictly valid JSON object as follows:  

{{
    "requirements": [
        "Requirement 1",
        "Requirement 2",
        "Requirement 3"
    ],
    "summary": "Short 2-3 sentence summary of the text",
    "evaluation_labels": [
        "Label1",
        "Label2"
    ]
}}

**Now analyze the following text:**  
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
def main():
    chunks = read_chunks(CHUNK_FILE)
    print(f"Total chunks available: {len(chunks)}")

    all_chunks_data = []
    START_CHUNK = 29  # Start from chunk 30 (0-based index)

    for i, chunk_text in enumerate(chunks[START_CHUNK:], start=START_CHUNK):
 
        # if is_toc_chunk(chunk_text):
        #     print(f"Skipping chunk {i+1} (Table of Contents)")
        #     chunk_data = {
        #         "chunk_index": i,
        #         "text": chunk_text,
        #         "requirements": [],
        #         "summary": "",
        #         "evaluation_labels": [],
        #         "raw_model_output": "Skipped (Table of Contents)"
        #     }
        #     all_chunks_data.append(chunk_data)
        #     continue

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
    output_file = OUTPUT_FILE.parent / "rfp_chunk_analysis_all.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks_data, f, indent=4, ensure_ascii=False)

    print(f"\n✓ Analysis of all chunks complete. Results saved to {output_file}")

# ----------------------------
# Run main
# ----------------------------
if __name__ == "__main__":
    main()





