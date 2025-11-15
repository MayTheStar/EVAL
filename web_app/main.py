"""
RFP Analysis System - Main Orchestrator (Production Version)
Uses unified parser.py for both RFP and vendor responses.
Ensures compliant vendors only are embedded and available to chatbot.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Dict
import argparse
from dotenv import load_dotenv

# ============================================================
# OPTIONAL: Database Integration (non-blocking)
# ============================================================
try:
    ROOT_DIR = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT_DIR))
    from backend.core.database import SessionLocal
    from backend.core.core_models import RFPDocument, VendorDocument, DocumentChunk
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False
    SessionLocal = None
    RFPDocument = VendorDocument = DocumentChunk = None


# ============================================================
# IMPORT MODULES (Unified Parser)
# ============================================================
from parser import (
    process_document,
    process_vendor_response,
    process_multiple_vendors
)

from extractor import analyze_rfp_and_vendors
from embeder import create_embeddings_from_rfp_and_vendors
from chatbot import create_chatbot
import compliance_checker

load_dotenv()


# ============================================================
# MAIN CLASS — PRODUCTION VERSION
# ============================================================
class RFPAnalysisSystem:
    """Main system orchestrator for RFP analysis pipeline."""

    def __init__(
        self,
        output_dir: str = "output",
        openai_api_key: Optional[str] = None,
        min_tokens: int = 512,
        max_tokens: int = 1024,
        project_id: Optional[str] = None,
        rfp_id: Optional[str] = None,
        vendor_doc_ids: Optional[Dict[str, str]] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load key
        if openai_api_key is None:
            openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("❌ OPENAI_API_KEY missing")

        self.api_key = openai_api_key
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens

        # Project IDs (optional)
        self.project_id = project_id
        self.rfp_id = rfp_id
        self.vendor_doc_ids = vendor_doc_ids or {}

        # File paths
        self.chunks_dir = self.output_dir / "chunks"
        self.analysis_dir = self.output_dir / "analysis"
        self.embeddings_dir = self.output_dir / "embeddings"

        self.chunks_dir.mkdir(exist_ok=True)
        self.analysis_dir.mkdir(exist_ok=True)
        self.embeddings_dir.mkdir(exist_ok=True)

        print("\n============================================================")
        print("🚀 RFP Analysis System Initialized (Production Mode)")
        print("============================================================")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"📊 Token range: {min_tokens}-{max_tokens}\n")

    # ============================================================
    # 1. PROCESS RFP
    # ============================================================
    def process_rfp(self, rfp_file: str) -> Dict:
        print("\n============================================================")
        print("📋 STEP 1: Processing RFP Document")
        print("============================================================")

        name = Path(rfp_file).stem

        json_output = self.chunks_dir / f"{name}_chunks.json"
        txt_output = self.chunks_dir / f"{name}_chunks.txt"

        # Correct unified parser call
        merged_chunks = process_document(
            input_path=rfp_file,
            output_txt_path=str(txt_output),
            output_json_path=str(json_output)
        )

        return {
            "json": str(json_output),
            "chunks": merged_chunks,
        }


    # ============================================================
    # 2. PROCESS VENDORS
    # ============================================================
    def process_vendors(self, vendor_files: List[tuple]) -> Dict:
        print("\n============================================================")
        print("📦 STEP 2: Processing Vendor Responses")
        print("============================================================")

        vendor_results = {}

        for vendor_file, vendor_name in vendor_files:
            json_output = self.chunks_dir / f"{vendor_name}_chunks.json"

            # Correct unified parser call
            chunks = process_vendor_response(
                vendor_file_path=vendor_file,
                vendor_name=vendor_name,
                output_dir=self.chunks_dir
            )

            vendor_results[vendor_name] = {
                "json": str(json_output),
                "chunks": chunks,
            }

        return vendor_results


    # ============================================================
    # 3. EXTRACT REQUIREMENTS
    # ============================================================
    def extract_requirements(self, rfp_json: str, vendor_jsons: List[tuple]) -> Dict:
        print("\n============================================================")
        print("🔍 STEP 3: Extracting Requirements & Analysis")
        print("============================================================")

        return analyze_rfp_and_vendors(
            rfp_json,
            vendor_jsons,
            str(self.analysis_dir),
            self.api_key,
        )

    # ============================================================
    # 4. COMPLIANCE CHECK
    # ============================================================
    def evaluate_compliance(self) -> Dict:
        print("\n============================================================")
        print("⚖️ STEP 3.5: Evaluating Vendor Compliance")
        print("============================================================")

        rfp_analysis_file = str(self.analysis_dir / "rfp_chunk_analysis.json")

        vendor_analysis_files = {}
        for file in self.analysis_dir.glob("*_analysis.json"):
            name = file.stem.replace("_analysis", "")
            if name.lower() != "rfp_chunk":
                vendor_analysis_files[name] = str(file)

        checker = compliance_checker.ComplianceChecker()

        return checker.evaluate_all_vendors(
            rfp_analysis_file,
            vendor_analysis_files,
            output_dir=str(self.output_dir / "compliance"),
        )

    # ============================================================
    # 5. CREATE EMBEDDINGS
    # ============================================================
    def create_embeddings(self, rfp_json: str, vendor_jsons: List[str]):
        print("\n============================================================")
        print("✨ STEP 4: Creating Embeddings")
        print("============================================================")

        return create_embeddings_from_rfp_and_vendors(
            rfp_json,
            vendor_jsons,
            str(self.embeddings_dir),
            "chunks_faiss.index",
            "chunks_metadata.json",
            api_key=self.api_key,
        )

    # ============================================================
    # 6. PREPARE CHATBOT
    # ============================================================
    def prepare_chatbot(self, vector_db_path: str, metadata_path: str):
        print("\n============================================================")
        print("🤖 STEP 5: Preparing Chatbot")
        print("============================================================")

        return create_chatbot(
            vector_db_file=vector_db_path,
            metadata_file=metadata_path,
            api_key=self.api_key,
        )

    # ============================================================
    # FULL PIPELINE
    # ============================================================
    def run_full_pipeline(
        self,
        rfp_file: str,
        vendor_files: List[tuple],
        skip_extraction: bool = False,
        run_chatbot: bool = False,
    ) -> Dict:

        print("\n\n============================================================")
        print("🎯 RUNNING FULL RFP ANALYSIS PIPELINE")
        print("============================================================\n")

        results = {}

        # 1) RFP
        rfp_results = self.process_rfp(rfp_file)
        results["rfp"] = rfp_results

        # 2) Vendors
        vendor_results = self.process_vendors(vendor_files)
        results["vendors"] = vendor_results

        # 3) Extraction
        if not skip_extraction:
            extraction_results = self.extract_requirements(
                rfp_results["json"],
                [(v["json"], name) for name, v in vendor_results.items()],
            )
            results["extraction"] = extraction_results

        # 4) Compliance
        compliance_results = self.evaluate_compliance()
        results["compliance"] = compliance_results

        non_compliant = [
            name for name, data in compliance_results.items()
            if not data.get("compliant", False)
        ]

        # Filter out disqualified vendors
        vendor_json_paths = [
            v["json"] for name, v in vendor_results.items()
        ]


        # 5) Embeddings
        faiss_path, metadata_path = self.create_embeddings(
            rfp_results["json"], vendor_json_paths
        )

        results["embeddings"] = {
            "faiss": faiss_path,
            "metadata": metadata_path,
        }

        # 6) Chatbot
        chatbot = self.prepare_chatbot(faiss_path, metadata_path)
        results["chatbot"] = chatbot

        print("\n============================================================")
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print("============================================================\n")

        return results


# ============================================================
# CLI ENTRY POINT
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="RFP Analysis System")
    parser.add_argument("--rfp", required=True)
    parser.add_argument("--vendors", nargs="+")
    parser.add_argument("--output", default="output")
    parser.add_argument("--skip-extraction", action="store_true")
    args = parser.parse_args()

    vendor_files = []
    if args.vendors:
        for vendor_spec in args.vendors:
            if ":" in vendor_spec:
                path, name = vendor_spec.split(":")
            else:
                path = vendor_spec
                name = Path(vendor_spec).stem
            vendor_files.append((path, name))

    system = RFPAnalysisSystem(output_dir=args.output)
    system.run_full_pipeline(args.rfp, vendor_files)


if __name__ == "__main__":
    main()
