from ai_engine.pdf_processing import parse_document
from ai_engine.LLMSecDetector import detect_sections_with_llm
import json


pdf_path = "sample_rfp.pdf"


print("Extracting text from PDF...")
pages = parse_document(pdf_path)
print(f"✅ Extracted {len(pages)} pages.")


print("Detecting sections using LLM...")
sections = detect_sections_with_llm(pages)


output_file = "rfp_sections.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(sections, f, indent=2, ensure_ascii=False)

print(f"\n Analysis complete! Results saved to {output_file}")
