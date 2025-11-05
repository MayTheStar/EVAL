#!/usr/bin/env python3
"""
ai_vendor_scoring.py

AI-assisted scoring of vendor proposals against RFP requirements.

Dependencies:
- pip install openai numpy tqdm python-dotenv

Usage:
export OPENAI_API_KEY="sk-..."
python ai_vendor_scoring.py \
    --rfp-file cleaned_requirements.json \
    --vendor-file vendor_proposal.pdf \
    --out-dir ./scores \
    --top-chunks 3 \
    --similarity-thresh 0.65
"""

import os
import json
import csv
from pathlib import Path
import numpy as np
from tqdm import tqdm
from openai import OpenAI
from dotenv import load_dotenv

# Load .env
load_dotenv()

# -------------------------
# Utilities
# -------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_csv(rows, path, headers=None):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if headers:
            writer.writerow(headers)
        for r in rows:
            writer.writerow(r)

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))

# -------------------------
# OpenAI clients
# -------------------------
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment.")
    return OpenAI(api_key=api_key)

# -------------------------
# Main scoring
# -------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--rfp-file", required=True, help="Path to cleaned_requirements.json")
    parser.add_argument("--vendor-file", required=True, help="Path to vendor proposal (PDF/text)")
    parser.add_argument("--out-dir", default="./", help="Output directory")
    parser.add_argument("--top-chunks", type=int, default=3, help="Top chunks to send to LLM")
    parser.add_argument("--similarity-thresh", type=float, default=0.65, help="Minimum cosine similarity to consider")
    args = parser.parse_args()

    rfp_file = Path(args.rfp_file)
    vendor_file = Path(args.vendor_file)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load cleaned requirements
    rfp_reqs = load_json(rfp_file)

    # Fetch category weights from RFP (example: proportional to member_count)
    category_counts = {}
    for req in rfp_reqs:
        cat = req.get("category", "uncategorized")
        category_counts[cat] = category_counts.get(cat, 0) + req.get("member_count", 1)
    total = sum(category_counts.values())
    category_weights = {cat: cnt/total for cat, cnt in category_counts.items()}

    # -------------------------
    # Parse vendor proposal into chunks
    # -------------------------
    # This uses your existing parser; replace below with your actual parser
    from parser2 import process_pdf # <-- your parser
    proposal_chunks = process_pdf(str(vendor_file))
    chunk_texts = [c["text"] for c in proposal_chunks]

    # -------------------------
    # Compute embeddings for vendor chunks
    # -------------------------
    from embeder2 import embed_chunks  # <-- your embedder
    #embed_model = "text-embedding-3-large"
    chunk_embeddings = embed_chunks(chunk_texts)

    # -------------------------
    # Prepare LLM client
    # -------------------------
    client = get_openai_client()
    llm_model = "gpt-4o-mini"

    results = []

    for req in tqdm(rfp_reqs, desc="Scoring requirements"):
        req_text = req["text"]
        req_id = req["req_id"]
        category = req.get("category", "uncategorized")

        # -------------------------
        # Find top matching chunks
        # -------------------------
        sims = [cosine_sim(np.array(req.get("embedding", np.zeros(1536))), np.array(e)) for e in chunk_embeddings]
        top_indices = np.argsort(sims)[::-1][:args.top_chunks]
        top_chunks = [chunk_texts[i] for i in top_indices if sims[i] >= args.similarity_thresh]

        # -------------------------
        # Build LLM prompt
        # -------------------------
        prompt = f"""
Requirement: "{req_text}"

Vendor proposal excerpts: {top_chunks}

Question:
1) Does the vendor meet this requirement? 
2) Score 0 (not met) to 3 (exceeds expectations). 
3) Explain briefly why.
Format: JSON with fields 'score' and 'explanation'.
"""
        # Call LLM
        resp = client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        answer_text = resp.choices[0].message.content.strip()
        try:
            answer_json = json.loads(answer_text)
            score = int(answer_json.get("score", 0))
            explanation = answer_json.get("explanation", "")
        except Exception:
            # fallback if parsing fails
            score = 0
            explanation = answer_text

        results.append({
            "req_id": req_id,
            "requirement": req_text,
            "category": category,
            "score": score,
            "explanation": explanation
        })

    # -------------------------
    # Aggregate by category
    # -------------------------
    cat_scores = {}
    for cat, weight in category_weights.items():
        cat_reqs = [r for r in results if r["category"] == cat]
        if cat_reqs:
            avg_score = sum(r["score"] for r in cat_reqs) / len(cat_reqs)
            cat_scores[cat] = avg_score * weight
        else:
            cat_scores[cat] = 0.0

    total_score = sum(cat_scores.values())

    # -------------------------
    # Save outputs
    # -------------------------
    save_json(results, out_dir / "vendor_scores.json")
    save_csv([[r["req_id"], r["requirement"], r["category"], r["score"], r["explanation"]] for r in results],
             out_dir / "vendor_scores.csv",
             headers=["req_id", "requirement", "category", "score", "explanation"])

    print("Vendor scoring complete.")
    print("Category scores:", cat_scores)
    print("Total weighted score:", total_score)

if __name__ == "__main__":
    main()
