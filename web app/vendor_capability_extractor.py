"""
Vendor Capability Extractor
Flexible AI-powered extraction of vendor capabilities, commitments, and differentiators.
Integrates with the EVAL RFP Analysis System.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv


# ----------------------------
# Configuration Defaults
# ----------------------------
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0


class VendorCapabilityExtractor:
    """Extracts capabilities, commitments, and differentiators from vendor response chunks."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE):
        """
        Initialize the extractor.
        
        Args:
            api_key: OpenAI API key (if None, loads from .env)
            model: Model name to use
            temperature: Model temperature (0 = deterministic)
        """
        load_dotenv()
        api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OpenAI API key not found. Provide it directly or via .env")

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def analyze_chunk(self, chunk_text: str) -> Dict:
        """
        Analyze a single vendor chunk for capabilities, commitments, and differentiators.
        """
        prompt = f"""
You are an expert in analyzing vendor proposals in response to RFPs.

Your task is to extract all **capabilities**, **commitments/deliverables**, and **unique differentiators** that the vendor claims.
You must categorize findings and summarize the text.

Return valid JSON only in the following structure:
{{
    "capabilities": [],
    "commitments": [],
    "differentiators": [],
    "summary": "",
    "evaluation_labels": []
}}

Analyze this vendor content:
{chunk_text}
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
            )
            content = response.choices[0].message.content
            result = json.loads(content)
        except Exception as e:
            print(f"⚠️ Error analyzing chunk: {e}")
            result = {
                "capabilities": [],
                "commitments": [],
                "differentiators": [],
                "summary": "",
                "evaluation_labels": [],
                "raw_model_output": content if 'content' in locals() else ""
            }
        else:
            result["raw_model_output"] = content

        return result

    def analyze_file(self, vendor_json_path: str, output_dir: Optional[str] = None) -> List[Dict]:
        """
        Analyze all chunks in a single vendor JSON file.
        
        Args:
            vendor_json_path: Path to vendor chunks JSON
            output_dir: Directory to save the output file (default = same directory)
        
        Returns:
            List of analysis results
        """
        vendor_name = Path(vendor_json_path).stem.replace("_chunks", "")
        print(f"\n🔹 Analyzing vendor: {vendor_name}")

        with open(vendor_json_path, "r", encoding="utf-8") as vf:
            vendor_chunks = json.load(vf)

        results = []
        for i, chunk in enumerate(vendor_chunks):
            text = chunk.get("contextualized_text") or chunk.get("text", "")
            print(f"   ↳ Chunk {i+1}/{len(vendor_chunks)}")
            result = self.analyze_chunk(text)
            results.append(result)

        output_dir = Path(output_dir) if output_dir else Path(vendor_json_path).parent
        output_path = output_dir / f"{vendor_name}_capability_analysis.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

        print(f"✅ Saved capability analysis → {output_path}")
        return results

    def analyze_folder(self, vendor_folder: str, output_dir: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        Analyze all vendor chunk files in a folder.
        
        Args:
            vendor_folder: Path to folder containing *_chunks.json
            output_dir: Directory to save all results (default = same folder)
        
        Returns:
            Dictionary mapping vendor names to their extracted data
        """
        vendor_path = Path(vendor_folder)
        if not vendor_path.exists():
            raise ValueError(f"Vendor folder not found: {vendor_folder}")

        vendor_files = [
            f for f in vendor_path.glob("*_chunks.json")
            if not f.stem.lower().startswith("rfp_")
        ]

        if not vendor_files:
            print("⚠️ No vendor chunk files found.")
            return {}

        all_results = {}
        for vf in vendor_files:
            vendor_name = Path(vf).stem.replace("_chunks", "")
            all_results[vendor_name] = self.analyze_file(str(vf), output_dir)


        print("\n🎯 All vendor capability analyses completed!")
        return all_results


# ----------------------------
# CLI Entry Point
# ----------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        vendor_folder = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None

        extractor = VendorCapabilityExtractor()
        extractor.analyze_folder(vendor_folder, output_dir)
    else:
        print("Usage: python vendor_capability_extractor.py <vendor_folder> [output_dir]")