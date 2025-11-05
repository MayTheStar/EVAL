#!/usr/bin/env python3
"""
clean_and_enhance_requirements.py

Post-processing + enhancement pipeline for RFP requirement extraction outputs.

Features:
- Loads rfp_chunk_analysis_all.json (must be produced by your original script)
- Extracts all requirements and labels
- Cleans text (normalization)
- Semantic deduplication using OpenAI embeddings (configurable)
- Greedy clustering using vector centroids (no sklearn required)
- Label normalization (mapping) then hybrid assignment (map -> infer via embeddings)
- Generates requirement IDs (REQ-001 ...)
- Produces JSON, CSV and a detailed report of merges and categories

Usage example:
    export OPENAI_API_KEY="sk-..."
    python clean_and_enhance_requirements.py \
        --data-file /Users/rayana/EVAL/ai_engine/rfp_chunk_analysis_all.json \
        --out-dir /Users/rayana/EVAL/ai_engine/ \
        --use-embeddings \
        --embed-model text-embedding-3-small \
        --sim-thresh 0.78

Dependencies:
    pip install openai numpy tqdm

Notes:
- This script uses the new OpenAI Python client style:
    from openai import OpenAI
  (same style you used in your analyzer)
"""

import json
import os
import argparse
import re
from pathlib import Path
from collections import defaultdict, Counter
from math import ceil
import csv
import numpy as np
from tqdm import tqdm

# OpenAI client (same style as your analyzer)
from openai import OpenAI
from dotenv import load_dotenv
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

def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = s.strip()
    s = re.sub(r"\s+", " ", s)  # collapse whitespace
    return s

def canonicalize_for_compare(s: str) -> str:
    """Lowercase, remove punctuation and common filler phrases used in RFP language"""
    s = s.lower()
    s = re.sub(r"[^\w\s]", "", s)  # remove punctuation
    # remove very common leading formal words that don't help dedupe
    s = re.sub(r"\b(system must|vendor shall|the system must|the vendor shall|the vendor must|vendor must|shall|must|should)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))

# -------------------------
# Label mapping + seeds
# -------------------------
LABEL_MAP = {
    "technical requirement": "technical",
    "technical": "technical",
    "technical spec": "technical",
    "functional": "technical",
    "non-functional": "technical",
    "financial": "financial",
    "pricing": "financial",
    "cost": "financial",
    "timeline": "schedule",
    "schedule": "schedule",
    "delivery": "schedule",
    "legal": "compliance",
    "compliance": "compliance",
    "security": "compliance",
    "performance": "technical",
    "operational": "technical",
}

# Seed category keywords (used to infer category by embedding similarity if mapping missing)
CATEGORY_SEEDS = {
    "technical": ["technical", "functional", "performance", "non-functional", "specification"],
    "financial": ["financial", "pricing", "cost", "budget", "price"],
    "schedule": ["timeline", "schedule", "delivery", "milestone", "deadline"],
    "compliance": ["compliance", "legal", "regulatory", "security", "policy"],
}

# -------------------------
# Embeddings helpers
# -------------------------
def get_openai_client_from_env():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment.")
    return OpenAI(api_key=api_key)

def compute_embeddings(client, texts, model="text-embedding-3-large", batch_size=64):
    """
    Compute embeddings via OpenAI. Returns list of numpy arrays in same order as texts.
    Uses batching.
    """
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        # the new client returns data with .embedding elements
        resp = client.embeddings.create(model=model, input=batch)
        batch_emb = [np.array(d.embedding, dtype=np.float32) for d in resp.data]
        embeddings.extend(batch_emb)
    return embeddings

# -------------------------
# Greedy clustering on vectors
# -------------------------
def greedy_cluster_vectors(vectors, items, sim_threshold=0.78):
    """
    Greedy clustering: iterate items, compare vector to existing cluster centroids.
    If similarity to any centroid >= threshold -> add to that cluster and update centroid.
    Else -> create new cluster.
    Returns clusters: list of lists of indices.
    """
    if len(vectors) == 0:
        return []

    vectors = [np.array(v) for v in vectors]
    clusters = []           # list of index lists
    centroids = []          # centroid vectors (numpy arrays)

    for idx, vec in enumerate(vectors):
        assigned = False
        best_sim = -1.0
        best_c = None
        for c_i, centroid in enumerate(centroids):
            sim = cosine_sim(vec, centroid)
            if sim > best_sim:
                best_sim = sim
                best_c = c_i
        if best_sim >= sim_threshold:
            clusters[best_c].append(idx)
            # update centroid: mean of member vectors
            member_vecs = [vectors[i] for i in clusters[best_c]]
            centroids[best_c] = np.mean(member_vecs, axis=0)
        else:
            clusters.append([idx])
            centroids.append(vec.copy())
    return clusters

# -------------------------
# Main pipeline
# -------------------------
def build_args():
    p = argparse.ArgumentParser(description="Clean and enhance RFP requirements using embeddings + clustering")
    p.add_argument("--data-file", type=str, required=True,
                   help="Path to rfp_chunk_analysis_all.json produced by your analyzer")
    p.add_argument("--out-dir", type=str, default=".",
                   help="Directory to write outputs")
    p.add_argument("--use-embeddings", action="store_true", default=False,
                   help="Use OpenAI embeddings for semantic deduplication (recommended)")
    p.add_argument("--embed-model", type=str, default="text-embedding-3-large",
                   help="Embedding model to use")
    p.add_argument("--sim-thresh", type=float, default=0.78,
                   help="Cosine similarity threshold for clustering (0-1). Larger = stricter dedupe")
    p.add_argument("--batch-size", type=int, default=64,
                   help="Batch size for embedding calls")
    p.add_argument("--seed", type=int, default=42, help="Random seed (affects selection of representative items only)")
    return p

def main():
    args = build_args().parse_args()
    data_file = Path(args.data_file)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # load analyzer output
    if not data_file.exists():
        raise FileNotFoundError(f"Data file not found: {data_file}")
    print("Loading analyzer output...")
    raw = load_json(data_file)

    # flatten requirements and collect labels + provenance
    requirements = []     # list of requirement strings (original)
    provenance = []       # which chunk index and raw model output etc
    req_labels = []       # labels associated with each requirement (list)
    for entry in raw:
        chunk_idx = entry.get("chunk_index")
        text = entry.get("text", "")
        labels = entry.get("evaluation_labels", []) or []
        reqs = entry.get("requirements", []) or []
        for r in reqs:
            rnorm = normalize_text(r)
            if not rnorm:
                continue
            requirements.append(rnorm)
            provenance.append({
                "chunk_index": chunk_idx,
                "chunk_text_snippet": text[:240]
            })
            req_labels.append(labels)

    print(f"Extracted {len(requirements)} raw requirements from {len(raw)} chunks")

    # normalize and canonical forms for easy mapping
    canonical_forms = [canonicalize_for_compare(r) for r in requirements]

    # if embeddings enabled: compute embeddings for requirements and for seed category keywords
    client = None
    req_embeddings = None
    seed_category_embeddings = {}
    if args.use_embeddings:
        print("Initializing OpenAI client and computing embeddings (this will use API calls)...")
        client = get_openai_client_from_env()
        # compute requirement embeddings
        req_embeddings = compute_embeddings(client, requirements, model=args.embed_model, batch_size=args.batch_size)
        # compute seed embeddings for categories (flatten seeds)
        seed_texts = []
        seed_to_cat = []
        for cat, keywords in CATEGORY_SEEDS.items():
            for kw in keywords:
                seed_texts.append(kw)
                seed_to_cat.append(cat)
        seed_embs = compute_embeddings(client, seed_texts, model=args.embed_model, batch_size=args.batch_size)
        # aggregate by category: mean vector of its keywords
        for cat in CATEGORY_SEEDS.keys():
            kw_embs = [seed_embs[i] for i, c in enumerate(seed_to_cat) if c == cat]
            if kw_embs:
                seed_category_embeddings[cat] = np.mean(kw_embs, axis=0)

    # Hybrid label mapping: normalize direct labels first (LABEL_MAP)
    flat_labels = []
    for lbls in req_labels:
        for l in lbls:
            if l and isinstance(l, str):
                flat_labels.append(l)
    # canonicalize and map
    mapped_labels = [LABEL_MAP.get(l.strip().lower(), l.strip().lower()) for l in flat_labels]
    unique_mapped_labels = sorted(set(mapped_labels))
    print(f"Found {len(flat_labels)} raw labels; {len(unique_mapped_labels)} unique mapped labels (examples): {unique_mapped_labels[:10]}")

    # If no embeddings: fallback to fuzzy dedupe using canonical forms + sequence matching
    if not args.use_embeddings:
        print("Embeddings disabled — using text canonicalization + greedy string similarity dedupe.")
        # simple dedupe based on canonical forms and string similarity
        from difflib import SequenceMatcher
        kept = []
        groups = []
        for idx, canon in enumerate(canonical_forms):
            found = False
            for gi, g in enumerate(groups):
                # compare to group's canonical rep
                rep_idx = g[0]
                rep_canon = canonical_forms[rep_idx]
                ratio = SequenceMatcher(None, canon, rep_canon).ratio()
                if ratio >= args.sim_thresh:
                    g.append(idx)
                    found = True
                    break
            if not found:
                groups.append([idx])
        clusters = groups

        # produce centroid-less versions for compatibility
        cluster_vectors = None
    else:
        # Use embeddings + greedy clustering
        print("Clustering using embeddings (greedy centroid method)...")
        clusters = greedy_cluster_vectors(req_embeddings, requirements, sim_threshold=args.sim_thresh)
        cluster_vectors = req_embeddings

    # Build cluster metadata, choose representative requirement (longest or highest label count)
    clusters_meta = []
    for c_i, cluster in enumerate(clusters):
        members = cluster
        # choose representative: pick the item with the longest original string (more detail), tie-breaker first
        rep_idx = max(members, key=lambda i: (len(requirements[i]), -i))
        rep_text = requirements[rep_idx]
        # aggregate original variations
        variations = [{"index": i, "text": requirements[i], "canonical": canonical_forms[i], "provenance": provenance[i], "labels": req_labels[i]} for i in members]
        # collect labels for cluster and map using LABEL_MAP where possible
        cluster_label_candidates = []
        for i in members:
            for l in req_labels[i]:
                if l and isinstance(l, str):
                    cluster_label_candidates.append(l.strip().lower())
        mapped = [LABEL_MAP.get(l, l) for l in cluster_label_candidates]
        mapped_counts = Counter(mapped)
        # pick majority mapped label if any
        if mapped_counts:
            top_label, top_count = mapped_counts.most_common(1)[0]
            assigned_category = top_label
        else:
            # try infer by embedding similarity to seed categories
            assigned_category = None
            if args.use_embeddings and len(seed_category_embeddings) > 0:
                # compute centroid of cluster
                vecs = [cluster_vectors[i] for i in members]
                centroid = np.mean(vecs, axis=0)
                best_cat = None
                best_sim = -1.0
                for cat, seed_vec in seed_category_embeddings.items():
                    sim = cosine_sim(centroid, seed_vec)
                    if sim > best_sim:
                        best_sim = sim
                        best_cat = cat
                # accept if similarity reasonably high (>0.55) else unknown
                if best_sim >= 0.55:
                    assigned_category = best_cat
                else:
                    assigned_category = "uncategorized"
            else:
                assigned_category = "uncategorized"

        clusters_meta.append({
            "cluster_index": c_i,
            "member_count": len(members),
            "member_indices": members,
            "representative_index": rep_idx,
            "representative_text": rep_text,
            "variations": variations,
            "assigned_category": assigned_category,
            "label_counts": dict(mapped_counts)
        })

    # Sort clusters by size descending
    clusters_meta.sort(key=lambda x: x["member_count"], reverse=True)

    # Assign REQ IDs and build final cleaned requirements list
    cleaned_requirements = []
    req_id_map = {}  # rep_idx -> REQ-ID
    for i, c in enumerate(clusters_meta, start=1):
        req_id = f"REQ-{i:03d}"
        rep_idx = c["representative_index"]
        rep_text = c["representative_text"]
        cleaned_requirements.append({
            "req_id": req_id,
            "text": rep_text,
            "category": c["assigned_category"],
            "member_count": c["member_count"],
            "merged_variations": [v["text"] for v in c["variations"]],
            "provenance_examples": [v["provenance"] for v in c["variations"]][:3],
            "label_counts": c["label_counts"]
        })
        req_id_map[rep_idx] = req_id
        # map other indices to same id
        for m in c["member_indices"]:
            req_id_map[m] = req_id

    # Build cleaned labels list (global)
    cleaned_label_set = set()
    for lbls in req_labels:
        for l in lbls:
            if l and isinstance(l, str):
                cleaned_label_set.add(LABEL_MAP.get(l.strip().lower(), l.strip().lower()))
    cleaned_labels = sorted(cleaned_label_set)

    # Build requirements_by_category
    by_category = defaultdict(list)
    for item in cleaned_requirements:
        cat = item["category"] or "uncategorized"
        by_category[cat].append({
            "req_id": item["req_id"],
            "text": item["text"],
            "member_count": item["member_count"]
        })

    # Generate CSV rows for human consumption
    csv_rows = []
    csv_headers = ["req_id", "category", "member_count", "text", "merged_variations_count"]
    for item in cleaned_requirements:
        csv_rows.append([item["req_id"], item["category"], item["member_count"], item["text"], len(item["merged_variations"])])

    # Build a detailed report for merges
    merges_report = {
        "summary": {
            "total_raw_requirements": len(requirements),
            "total_clusters": len(clusters_meta),
            "total_cleaned_requirements": len(cleaned_requirements)
        },
        "clusters": clusters_meta
    }

    # Save files
    save_json(cleaned_requirements, out_dir / "cleaned_requirements.json")
    save_json(cleaned_labels, out_dir / "cleaned_labels.json")
    save_json(merges_report, out_dir / "requirements_report.json")
    save_json(by_category, out_dir / "requirements_by_category.json")
    save_csv(csv_rows, out_dir / "cleaned_requirements.csv", headers=csv_headers)

    print("\nOutputs written to:", out_dir)
    print(f"- cleaned_requirements.json ({len(cleaned_requirements)} entries)")
    print(f"- cleaned_requirements.csv")
    print(f"- cleaned_labels.json ({len(cleaned_labels)} labels)")
    print(f"- requirements_report.json (detailed merge report)")
    print(f"- requirements_by_category.json")

if __name__ == "__main__":
    main()
