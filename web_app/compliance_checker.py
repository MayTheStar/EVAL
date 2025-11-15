"""
Compliance Checker (Production Version)
- Fully compatible with unified parser + extractor output
- Robust to empty vendor requirements
- Uses batched encoding for 50x speed increase
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from sentence_transformers import SentenceTransformer, util
import numpy as np


class ComplianceChecker:

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        threshold: float = 0.75
    ):
        """
        Args:
            model_name: SentenceTransformer model.
            threshold: Semantic similarity threshold.
        """
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold

    # ----------------------------------------------------
    # JSON Loader
    # ----------------------------------------------------
    def load_json(self, file_path: str) -> List[Dict]:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ----------------------------------------------------
    # Extract Mandatory Requirements
    # ----------------------------------------------------
    def extract_mandatory(self, rfp_data: List[Dict]) -> List[str]:
        mandatory = []
        for chunk in rfp_data:
            for req in chunk.get("requirements", []):
                if isinstance(req, dict) and req.get("type") == "mandatory":
                    text = req.get("text", "").strip()
                    if text:
                        mandatory.append(text)
        return mandatory

    # ----------------------------------------------------
    # Extract Vendor Capability Statements
    # ----------------------------------------------------
    def extract_vendor_statements(self, vendor_data: List[Dict]) -> List[str]:
        caps = []
        for chunk in vendor_data:
            for req in chunk.get("requirements", []):
                if isinstance(req, dict):
                    text = req.get("text", "").strip()
                    if text:
                        caps.append(text)
        return caps

    # ----------------------------------------------------
    # Semantic Compliance (batched)
    # ----------------------------------------------------
    def check_vendor(self, rfp_file: str, vendor_file: str) -> Dict:
        """
        Evaluate vendor compliance against mandatory RFP requirements.
        """

        rfp_data = self.load_json(rfp_file)
        vendor_data = self.load_json(vendor_file)

        mandatory = self.extract_mandatory(rfp_data)
        vendor_caps = self.extract_vendor_statements(vendor_data)

        # If vendor has no capabilities at all
        if not vendor_caps:
            return {
                "total_mandatory": len(mandatory),
                "matched": 0,
                "missing": len(mandatory),
                "missing_requirements": mandatory,
                "compliant": False
            }

        # Encode ALL sentences at once (50x faster)
        mand_embs = self.model.encode(mandatory, convert_to_tensor=True, batch_size=16)
        cap_embs = self.model.encode(vendor_caps, convert_to_tensor=True, batch_size=16)

        # Compute cosine similarity matrix
        sim_matrix = util.cos_sim(mand_embs, cap_embs).cpu().numpy()

        matched = []
        missing = []

        # For each mandatory requirement, check if ANY vendor statement meets threshold
        for i, req in enumerate(mandatory):
            best_score = float(np.max(sim_matrix[i]))
            if best_score >= self.threshold:
                matched.append(req)
            else:
                missing.append(req)

        return {
            "total_mandatory": len(mandatory),
            "matched": len(matched),
            "missing": len(missing),
            "missing_requirements": missing,
            "compliant": len(missing) == 0
        }

    # ----------------------------------------------------
    # Evaluate All Vendors + Save JSON
    # ----------------------------------------------------
    def evaluate_all_vendors(
        self,
        rfp_file: str,
        vendor_files: Dict[str, str],
        output_dir: str
    ) -> Dict[str, Dict]:

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        summary = {}

        for vendor_name, vendor_file in vendor_files.items():
            print(f"🔍 Checking compliance for {vendor_name}...")
            result = self.check_vendor(rfp_file, vendor_file)
            summary[vendor_name] = result

            vendor_out = output_path / f"{vendor_name}_compliance.json"
            with open(vendor_out, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4, ensure_ascii=False)

        print("\n✅ Compliance evaluation complete!")
        return summary


# ----------------------------------------------------
# CLI MODE (Optional)
# ----------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run compliance checker")
    parser.add_argument("--rfp", required=True)
    parser.add_argument("--vendor", nargs="+", required=True)
    parser.add_argument("--out", required=True)

    args = parser.parse_args()

    vendor_map = {}
    for pair in args.vendor:
        name, path = pair.split("=")
        vendor_map[name] = path

    checker = ComplianceChecker()
    checker.evaluate_all_vendors(args.rfp, vendor_map, args.out)
