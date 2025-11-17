"""
compliance_checker.py
Flexible semantic compliance checker for RFP mandatory requirements.
"""

import json
from pathlib import Path
from typing import Dict, List
from sentence_transformers import SentenceTransformer, util


class ComplianceChecker:
    """
    Semantic compliance checker.
    - Detects missing mandatory requirements.
    - Supports any model, threshold, and vendor list.
    - No hardcoded paths or vendor names.
    """

    def __init__(self, 
                 model_name: str = "all-MiniLM-L6-v2",
                 threshold: float = 0.75):
        """
        Args:
            model_name: SentenceTransformer model name.
            threshold: semantic similarity threshold for compliance.
        """
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold

    # ----------------------------------------------------
    # Helper: Load JSON
    # ----------------------------------------------------
    def load_json(self, file_path: str) -> List[Dict]:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ----------------------------------------------------
    # Check compliance for a single vendor
    # ----------------------------------------------------
    def check_vendor(self, rfp_file: str, vendor_file: str) -> Dict:
        """
        Compare vendor capability statements to RFP mandatory requirements.
        Returns compliance dict.
        """
        rfp_data = self.load_json(rfp_file)
        vendor_data = self.load_json(vendor_file)

        # Extract MANDATORY requirements
        mandatory_reqs = [
            req["text"]
            for chunk in rfp_data
            for req in chunk.get("requirements", [])
            if req.get("type") == "mandatory"
        ]

        # Extract ALL vendor statements
        vendor_caps = [
            req["text"]
            for chunk in vendor_data
            for req in chunk.get("requirements", [])
        ]

        matched = []
        missing = []

        for req in mandatory_reqs:
            req_emb = self.model.encode(req, convert_to_tensor=True)
            sims = []

            for cap in vendor_caps:
                cap_emb = self.model.encode(cap, convert_to_tensor=True)
                sims.append(util.cos_sim(req_emb, cap_emb).item())

            # Determine if requirement matched
            if sims and max(sims) >= self.threshold:
                matched.append(req)
            else:
                missing.append(req)

        return {
            "total_mandatory": len(mandatory_reqs),
            "matched": len(matched),
            "missing": len(missing),
            "missing_requirements": missing,
            "compliant": len(missing) == 0
        }

    # ----------------------------------------------------
    # Evaluate all vendors and save JSON outputs
    # ----------------------------------------------------
    def evaluate_all_vendors(self, 
                             rfp_file: str,
                             vendor_files: Dict[str, str],
                             output_dir: str) -> Dict[str, Dict]:
        """
        Process all vendors and save results.
        Args:
            rfp_file: path to RFP mandatory requirement analysis.
            vendor_files: {vendor_name: vendor_analysis_file}
            output_dir: folder to save JSON results.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        summary = {}

        for vendor_name, vendor_file in vendor_files.items():
            print(f"🔍 Checking compliance for {vendor_name}...")

            result = self.check_vendor(rfp_file, vendor_file)
            summary[vendor_name] = result

            # Save vendor compliance JSON
            vendor_out = output_path / f"{vendor_name}_compliance.json"
            with open(vendor_out, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4, ensure_ascii=False)

        print("\n✅ Compliance evaluation complete!")
        return summary


# ----------------------------------------------------
# Optional: CLI-style execution (safe & dynamic)
# ----------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run compliance checker")
    parser.add_argument("--rfp", required=True, help="Path to RFP analysis JSON")
    parser.add_argument("--vendor", nargs="+", required=True,
                        help="Vendor name and path pairs: VendorA=pathA VendorB=pathB")
    parser.add_argument("--out", required=True, help="Output directory")

    args = parser.parse_args()

    vendor_map = {}
    for pair in args.vendor:
        name, path = pair.split("=")
        vendor_map[name] = path

    checker = ComplianceChecker()
    checker.evaluate_all_vendors(args.rfp, vendor_map, args.out)
