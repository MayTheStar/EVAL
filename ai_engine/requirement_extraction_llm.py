# import json
# import re


# REQUIREMENT_KEYWORDS = [
   
#     r"\bmust\b", r"\bshall\b", r"\bshould\b", r"\bwill\b",
#     r"\bare expected to\b", r"\bare obligated to\b",
#     r"\bis required to\b", r"\bis responsible for\b",
#     r"\bshall ensure\b", r"\bshall provide\b", r"\bshall comply\b",
#     r"\bmandated\b", r"\bmandatory\b", r"\bcompulsory\b",

  
#     r"\bindemnify\b", r"\bliable\b", r"\bresponsible\b", r"\baccountable\b",
#     r"\bto deliver\b", r"\bto perform\b", r"\bto provide\b", r"\bto maintain\b",
#     r"\bto comply\b", r"\bto adhere\b",

    
#     r"\bprohibited\b", r"\bnot permitted\b", r"\bshall not\b",
#     r"\bmust not\b", r"\bare not allowed\b",
    
    
#     r"\bensure quality\b", r"\bmeet standards\b", r"\bmaintain confidentiality\b",
#     r"\bprotect\b", r"\bsecure\b"
# ]



# def extract_requirements_from_text(text):
#     """Extract requirement-like sentences from text."""
   
#     sentences = re.split(r'(?<=[.!?])\s+', text)
#     requirements = []
    
#     for s in sentences:
       
#         if any(re.search(keyword, s, re.IGNORECASE) for keyword in REQUIREMENT_KEYWORDS):
           
#             if len(s.strip()) > 30:
#                 requirements.append(s.strip())
#     return requirements


# try:
#     with open("rfp_sections.json", "r", encoding="utf-8") as f:
#         data = json.load(f)
# except FileNotFoundError:
#     raise FileNotFoundError("❌ File 'rfp_sections.json' not found. Run LLMSecDetector first!")


# extracted_requirements = []
# for section, entries in data.items():
#     for entry in entries:
#         text = entry.get("text", "")
#         reqs = extract_requirements_from_text(text)
#         for r in reqs:
#             extracted_requirements.append({
#                 "section": section,
#                 "page": entry.get("page_number"),
#                 "requirement": r
#             })


# output_file = "requirements_extracted.json"
# with open(output_file, "w", encoding="utf-8") as f:
#     json.dump(extracted_requirements, f, indent=2, ensure_ascii=False)


# print("✅ Requirement extraction complete!")
# print(f"Total requirements found: {len(extracted_requirements)}")
# sections_count = {}
# for req in extracted_requirements:
#     sec = req["section"]
#     sections_count[sec] = sections_count.get(sec, 0) + 1

# print("\n Requirements by section:")
# for sec, count in sections_count.items():
#     print(f"  • {sec}: {count} items")

# print(f"\n Results saved to: {output_file}")

import json
import os
from openai import OpenAI

# -----------------------------
# ✅ 1. إعداد المفتاح والموديل
# -----------------------------

from transformers import pipeline

extractor = pipeline("text2text-generation", model="google/flan-t5-base")

def extract_requirements_llm(section, text, page):
    prompt = f"Extract all requirements from this RFP section:\n\n{text}\n\nReturn only a JSON list."
    output = extractor(prompt, max_new_tokens=300)[0]['generated_text']
    return json.loads(output) if output.strip().startswith('[') else []


# -----------------------------
# 🧠 2. دالة استخراج المتطلبات
# -----------------------------
def extract_requirements_llm(section_name, text, page):
    """Use LLM to extract requirement-like statements from a given RFP section"""
    prompt = f"""
    You are an expert in analyzing RFP (Request for Proposal) documents.
    Your task is to extract all sentences that describe explicit or implicit REQUIREMENTS
    from the given section below.

    Return the output as a valid JSON array of strings (requirements only).

    Example output:
    [
      "The vendor shall provide a disaster recovery plan.",
      "The solution must comply with ISO 27001."
    ]

    Section: {section_name}
    Page: {page}
    Text:
    {text}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        raw_output = response.choices[0].message.content.strip()

        # محاولة قراءة JSON ناتج
        try:
            data = json.loads(raw_output)
        except:
            # fallback: استخرج الجمل بين علامات اقتباس
            import re
            data = re.findall(r'"(.*?)"', raw_output)

        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"⚠️ LLM error in section '{section_name}': {e}")
        return []


# -----------------------------
# 📄 3. تحميل النصوص من rfp_sections.json
# -----------------------------
try:
    with open("rfp_sections.json", "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError("❌ File 'rfp_sections.json' not found. Run LLMSecDetector first!")


# -----------------------------
# 🧩 4. تنفيذ الاستخراج من كل قسم
# -----------------------------
results = []
for section, entries in data.items():
    for entry in entries:
        text = entry.get("text", "")
        page = entry.get("page_number", "?")
        reqs = extract_requirements_llm(section, text, page)
        for r in reqs:
            results.append({
                "section": section,
                "page": page,
                "requirement": r
            })


# -----------------------------
# 💾 5. حفظ النتائج
# -----------------------------
output_file = "requirements_extracted_llm.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("✅ LLM-based requirement extraction complete!")
print(f"Total requirements found: {len(results)}")

# إحصائية لكل قسم
sections_count = {}
for req in results:
    sec = req["section"]
    sections_count[sec] = sections_count.get(sec, 0) + 1

print("\n📊 Requirements by section:")
for sec, count in sections_count.items():
    print(f"  • {sec}: {count} items")

print(f"\n🗂️ Results saved to: {output_file}")
