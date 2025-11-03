
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

# ✅ File where your chunk-level model outputs were saved
INPUT_FILE = "/Users/rayana/EVAL/ai_engine/rfp_chunk_analysis_all.json"
OUTPUT_FILE = "final_consolidated_requirements.json"

# ✅ Load extracted chunk results
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    extracted_data = json.load(f)

# ✅ Flatten requirements and summaries from all chunks
all_chunks_text = json.dumps(extracted_data, ensure_ascii=False)

# ✅ Consolidation prompt (global post-processing)
prompt = f"""
You are an expert in RFP analysis and requirement harmonization.

You are given extracted requirements and summaries from multiple RFP document chunks.
Your task is to consolidate and refine the full dataset.

Instructions:

1. Combine ALL requirements from every chunk into a single list.
2. Remove duplicates, redundancies, and conflicting versions of the same requirement.
3. Rewrite each requirement clearly and concisely in a **consistent vendor-focused format** starting with a mandate verb:
   - Must provide…
   - Must comply…
   - Must ensure…
   - Must include…
4. Do NOT change the meaning or intention of any requirement.
5. Group requirements by category:
   - Technical
   - Functional
   - Compliance / Legal
   - Financial / Pricing
   - Experience / Qualifications
   - Service & Support
   - Schedule / Delivery
   - Security & Data Protection
   - Other (if needed)
6. Provide a **global summary** of the RFP in 4–6 sentences, combining all chunk summaries.

**Output Format (strict JSON):**
{{
  "requirements_by_category": {{
    "Technical": [],
    "Functional": [],
    "Compliance": [],
    "Financial": [],
    "Experience": [],
    "Service_and_Support": [],
    "Schedule": [],
    "Security": [],
    "Other": []
  }},
  "combined_summary": ""
}}

Now process the following extracted chunk outputs:
{all_chunks_text}
"""

# ✅ Send to LLM for consolidation
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a world-class RFP expert."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=4000,
    temperature=0
)

# ✅ Extract result
final_output = response.choices[0].message.content

# ✅ Convert to JSON + save
try:
    final_json = json.loads(final_output)
except json.JSONDecodeError:
    raise ValueError("Model output was not valid JSON. Enable JSON schema enforcement or manual cleaning.")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(final_json, f, indent=4, ensure_ascii=False)

print(f"✅ Consolidation complete! Results saved to {OUTPUT_FILE}")
