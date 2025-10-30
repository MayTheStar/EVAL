from transformers import pipeline
import json
import re
import textwrap

# Initialize stronger Hugging Face model
llm_pipeline = pipeline("text2text-generation", model="google/flan-t5-small")

SECTION_LABELS = [
    "Introduction", "Scope", "Deliverables", "Requirements",
    "Pricing/Budget", "Terms & Conditions", "Other"
]

# Safe chunk size for flan-t5-large (~2200 characters ≈ 450 tokens)
MAX_CHARS_PER_CHUNK = 2200

def split_paragraph_by_lines(text: str):
    """Split a paragraph into lines and remove empty lines."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return lines if lines else [text]

def chunk_text(text: str, max_chars: int = MAX_CHARS_PER_CHUNK):
    """Split text into chunks not exceeding max_chars, preserving line boundaries."""
    lines = split_paragraph_by_lines(text)
    chunks = []
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 1 <= max_chars:
            current_chunk += (" " if current_chunk else "") + line
        else:
            chunks.append(current_chunk)
            current_chunk = line
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def build_prompt(text_chunk: str) -> str:
    """Build LLM prompt with explicit instructions."""
    return f"""Classify the following text into one of these sections: {', '.join(SECTION_LABELS)}.

Text:
{text_chunk}

Respond ONLY in JSON format EXACTLY like this:
{{"section": "<section_name>", "summary": "<1-2 sentence summary>"}}
IMPORTANT: Always provide a 1-2 sentence summary, even if the text is short or just a heading. Do NOT leave summary empty.
"""

def detect_sections_with_llm(pages: list) -> dict:
    sections = {label: [] for label in SECTION_LABELS}

    for page in pages:
        text = page.get("cleaned_text", "")
        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        for para in paragraphs:
            try:
                # Pre-classification heuristic: check for explicit section names
                lower_para = para.lower()
                assigned_section = None
                for label in SECTION_LABELS[:-1]:  # skip "Other"
                    if label.lower() in lower_para:
                        assigned_section = label
                        break

                # Split into chunks for LLM
                prompt_chunks = chunk_text(para)
                summaries = []
                final_section = assigned_section or "Other"

                for chunk in prompt_chunks:
                    prompt = build_prompt(chunk)
                    output = llm_pipeline(prompt, max_new_tokens=200)[0]['generated_text']
                    try:
                        result = json.loads(output)
                        # Override final_section if LLM decides differently
                        if not assigned_section:
                            final_section = result.get("section", "Other")
                        summary = result.get("summary", "").strip()
                        # Fallback to first sentence if summary empty
                        if not summary:
                            summary = chunk.split(".")[0].strip()
                        summaries.append(summary)
                    except json.JSONDecodeError:
                        # Fallback: use first sentence
                        summaries.append(chunk.split(".")[0].strip())

                combined_summary = " ".join([s for s in summaries if s]).strip()

                sections[final_section].append({
                    "page_number": page.get("page_number", None),
                    "text": para,
                    "summary": combined_summary
                })

            except Exception:
                # fallback for any unexpected errors
                sections["Other"].append({
                    "page_number": page.get("page_number", None),
                    "text": para,
                    "summary": para.split(".")[0].strip()
                })

    # Save results
    with open("rfp_sections.json", "w", encoding="utf-8") as f:
        json.dump(sections, f, indent=4, ensure_ascii=False)

    print("LLM-based section detection saved to: rfp_sections.json")
    return sections
