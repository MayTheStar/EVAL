"""
compliance_checker.py
Compares RFP mandatory requirements with vendor capabilities to determine compliance.
"""

import json
from pathlib import Path
from typing import Dict, List
from sentence_transformers import SentenceTransformer, util


def load_json(file_path: str) -> List[Dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize(text: str) -> str:
    """Simple normalization for comparison."""
    return text.lower().strip()


model = SentenceTransformer("all-MiniLM-L6-v2")

def check_compliance_semantic(rfp_analysis_file: str, vendor_analysis_file: str, threshold=0.75) -> Dict:
    rfp_data = load_json(rfp_analysis_file)
    vendor_data = load_json(vendor_analysis_file)

    mandatory_requirements = [
        req["text"] for chunk in rfp_data
        for req in chunk.get("requirements", [])
        if req.get("type") == "mandatory"
    ]
    vendor_capabilities = [
        cap for chunk in vendor_data
        for cap in chunk.get("capabilities", [])
    ]

    missing, matched = [], []
    for req in mandatory_requirements:
        req_emb = model.encode(req, convert_to_tensor=True)
        sims = [util.cos_sim(req_emb, model.encode(cap, convert_to_tensor=True)).item()
                for cap in vendor_capabilities]
        if sims and max(sims) >= threshold:
            matched.append(req)
        else:
            missing.append(req)

    return {
        "total_mandatory": len(mandatory_requirements),
        "matched": len(matched),
        "missing": len(missing),
        "compliant": len(missing) == 0,
        "missing_requirements": missing
    }



def evaluate_all_vendors(rfp_analysis_file: str, vendor_analysis_files: Dict[str, str], output_dir: str):
    """Evaluate compliance for all vendors."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    summary = {}
    
    for vendor_name, file_path in vendor_analysis_files.items():
        print(f"🔍 Checking compliance for {vendor_name}...")
        result = check_compliance_semantic(rfp_analysis_file, file_path)
        summary[vendor_name] = result
        
        output_file = Path(output_dir) / f"{vendor_name}_compliance.json"
        with open(Path(output_dir) / f"{vendor_name}_compliance.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
    
    print("\n✅ Compliance evaluation complete!")
    return summary


if __name__ == "__main__":
    rfp = "outputs/rfp_chunk_analysis.json"
    vendors = {
        "VendorA": "outputs/VendorA_analysis.json",
        "VendorB": "outputs/VendorB_analysis.json"
    }
    evaluate_all_vendors(rfp, vendors, "outputs/compliance")
