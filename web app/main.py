"""
RFP Analysis System - Main Orchestrator
Coordinates the entire pipeline: parsing, extraction, embedding, and chatbot preparation.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Dict
import argparse
from dotenv import load_dotenv

# ⭐ DB integration: try to import backend DB (optional, non-breaking)
try:
    BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(BACKEND_DIR))
    from core.database import SessionLocal
    from core.core_models import RFPDocument, VendorDocument, DocumentChunk
    DB_AVAILABLE = True
except Exception as _db_err:
    # If backend is not available, we just run without DB integration
    SessionLocal = None
    RFPDocument = VendorDocument = DocumentChunk = None
    DB_AVAILABLE = False


from parser import process_document
from vendor_parser import process_vendor_response, process_multiple_vendors
from extractor import analyze_document_chunks, analyze_rfp_and_vendors
from embeder import create_embeddings_from_rfp_and_vendors
from chatbot import create_chatbot
import compliance_checker


class RFPAnalysisSystem:
    """Main system orchestrator for RFP analysis pipeline."""
    
    def __init__(self, 
                 output_dir: str = "output",
                 openai_api_key: Optional[str] = None,
                 min_tokens: int = 512,
                 max_tokens: int = 1024,
                 project_id: Optional[str] = None,
                 rfp_id: Optional[str] = None,
                 vendor_doc_ids: Optional[Dict[str, str]] = None):
        """
        Initialize the RFP Analysis System.
        
        Args:
            output_dir: Base directory for all outputs
            openai_api_key: OpenAI API key (loads from .env if None)
            min_tokens: Minimum tokens per chunk
            max_tokens: Maximum tokens per chunk
            project_id: Optional project UUID (for DB integration)
            rfp_id: Optional RFPDocument UUID (for DB integration)
            vendor_doc_ids: Optional mapping {vendor_name: vendor_doc_id} (for DB integration)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load API key
        if openai_api_key is None:
            load_dotenv()
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY not found in environment or parameters")
        
        self.api_key = openai_api_key
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens

        # ⭐ DB-related IDs (optional)
        self.project_id = project_id
        self.rfp_id = rfp_id
        
        self.vendor_doc_ids = vendor_doc_ids or {}
        
        # Output paths
        self.chunks_dir = self.output_dir / "chunks"
        self.analysis_dir = self.output_dir / "analysis"
        self.embeddings_dir = self.output_dir / "embeddings"
        
        # Create subdirectories
        self.chunks_dir.mkdir(exist_ok=True)
        self.analysis_dir.mkdir(exist_ok=True)
        self.embeddings_dir.mkdir(exist_ok=True)
        
        print("=" * 60)
        print("🚀 RFP Analysis System Initialized")
        print("=" * 60)
        print(f"📁 Output directory: {self.output_dir}")
        print(f"📊 Token range: {self.min_tokens} - {self.max_tokens}")
        print()
    
    def process_rfp(self, rfp_file: str) -> Dict[str, str]:
        """
        Process RFP document through parsing pipeline.
        
        Args:
            rfp_file: Path to RFP document
            
        Returns:
            Dictionary with output file paths
        """
        print("=" * 60)
        print("📋 STEP 1: Processing RFP Document")
        print("=" * 60)
        
        rfp_name = Path(rfp_file).stem
        
        # Output paths
        txt_output = self.chunks_dir / f"{rfp_name}_chunks.txt"
        json_output = self.chunks_dir / f"{rfp_name}_chunks.json"
        
        # Process document
        chunks = process_document(
            rfp_file,
            str(txt_output),
            str(json_output),
            self.min_tokens,
            self.max_tokens
        )
        
        print(f"\n✅ RFP processing complete: {len(chunks)} chunks created")

        # ⭐ DB integration: Save RFP chunks if DB and RFPDocument exist
        if DB_AVAILABLE and DocumentChunk is not None:
            try:
                db = SessionLocal()
                rfp_doc_id = self.rfp_id

                # If rfp_id not passed, try to look it up by filepath
                if rfp_doc_id is None and RFPDocument is not None:
                    rfp_record = db.query(RFPDocument).filter(
                        RFPDocument.filepath == str(Path(rfp_file))
                    ).first()
                    if rfp_record:
                        rfp_doc_id = rfp_record.rfp_id

                if rfp_doc_id is not None:
                    for idx, chunk in enumerate(chunks):
                        db_chunk = DocumentChunk(
                            document_id=rfp_doc_id,
                            document_type="rfp",
                            chunk_index=idx,
                            original_text=chunk.get("text") or chunk.get("content") or "",
                            contextualized_text=chunk.get("contextualized_text"),
                            token_count=chunk.get("token_count"),
                            page_number=chunk.get("page"),
                            headings=chunk.get("headings"),
                            orig_indices=chunk.get("orig_indices"),
                            meta_info=None
                        )
                        db.add(db_chunk)
                    db.commit()
                    print(f"🗄️  Saved {len(chunks)} RFP chunks to database")
                else:
                    print("⚠️ DB: Could not determine rfp_id, skipping RFP chunks DB save")
                db.close()
            except Exception as e:
                print(f"⚠️ DB: Error saving RFP chunks: {e}")

        return {
            "txt": str(txt_output),
            "json": str(json_output),
            "chunks": chunks
        }
    
    def process_vendors(self, vendor_files: List[tuple]) -> Dict[str, Dict]:
        """
        Process multiple vendor response documents.
        
        Args:
            vendor_files: List of tuples (file_path, vendor_name)
            
        Returns:
            Dictionary mapping vendor names to their output paths
        """
        print("\n" + "=" * 60)
        print("📦 STEP 2: Processing Vendor Responses")
        print("=" * 60)
        
        vendor_results = {}
        
        for vendor_file, vendor_name in vendor_files:
            json_output = self.chunks_dir / f"{vendor_name}_chunks.json"
            
            chunks = process_vendor_response(
                vendor_file,
                vendor_name,
                self.chunks_dir,
                self.min_tokens,
                self.max_tokens
            )
            
            vendor_results[vendor_name] = {
                "json": str(json_output),
                "chunks": chunks
            }

            # ⭐ DB integration: Save vendor chunks if DB and VendorDocument exist
            if DB_AVAILABLE and DocumentChunk is not None:
                try:
                    db = SessionLocal()
                    vendor_doc_id = self.vendor_doc_ids.get(vendor_name)

                    # If not passed, try to look up by filepath
                    if vendor_doc_id is None and VendorDocument is not None:
                        v_record = db.query(VendorDocument).filter(
                            VendorDocument.filepath == str(Path(vendor_file))
                        ).first()
                        if v_record:
                            vendor_doc_id = v_record.vendor_doc_id

                    if vendor_doc_id is not None:
                        for idx, chunk in enumerate(chunks):
                            db_chunk = DocumentChunk(
                                document_id=vendor_doc_id,
                                document_type="vendor",
                                chunk_index=idx,
                                original_text=chunk.get("text") or chunk.get("content") or "",
                                contextualized_text=chunk.get("contextualized_text"),
                                token_count=chunk.get("token_count"),
                                page_number=chunk.get("page"),
                                headings=chunk.get("headings"),
                                orig_indices=chunk.get("orig_indices"),
                                meta_info=None
                            )
                            db.add(db_chunk)
                        db.commit()
                        print(f"🗄️  Saved {len(chunks)} chunks for vendor '{vendor_name}' to database")
                    else:
                        print(f"⚠️ DB: Could not determine vendor_doc_id for '{vendor_name}', skipping DB save")
                    db.close()
                except Exception as e:
                    print(f"⚠️ DB: Error saving vendor chunks for '{vendor_name}': {e}")
        
        print(f"\n✅ Vendor processing complete: {len(vendor_results)} vendors processed")
        
        return vendor_results
    
    def extract_requirements(self, rfp_json: str, vendor_jsons: List[tuple]) -> Dict:
        """
        Extract requirements and analysis from all documents.
        
        Args:
            rfp_json: Path to RFP chunks JSON
            vendor_jsons: List of tuples (json_path, vendor_name)
            
        Returns:
            Dictionary with analysis results
        """
        print("\n" + "=" * 60)
        print("🔍 STEP 3: Extracting Requirements & Analysis")
        print("=" * 60)
        
        results = analyze_rfp_and_vendors(
            rfp_json,
            vendor_jsons,
            str(self.analysis_dir),
            self.api_key
        )
        
        print(f"\n✅ Extraction complete: RFP + {len(results.get('vendors', {}))} vendors analyzed")
        
        
        return results
    
    def create_embeddings(self, rfp_json: str, vendor_jsons: List[str]) -> tuple:
        """
        Create embeddings and FAISS index for all documents.
        
        Args:
            rfp_json: Path to RFP chunks JSON
            vendor_jsons: List of paths to vendor chunks JSON files
            
        Returns:
            Tuple of (faiss_index_path, metadata_path)
        """
        print("\n" + "=" * 60)
        print("✨ STEP 4: Creating Embeddings & FAISS Index")
        print("=" * 60)
        
        vector_db_file = "chunks_faiss.index"
        metadata_file = "chunks_metadata.json"
        
        index, metadata = create_embeddings_from_rfp_and_vendors(
            rfp_json,
            vendor_jsons,
            str(self.embeddings_dir),
            vector_db_file,
            metadata_file,
            self.api_key
        )
        
        faiss_path = self.embeddings_dir / vector_db_file
        metadata_path = self.embeddings_dir / metadata_file
        
        print(f"\n✅ Embeddings created successfully")
        print(f"   📊 FAISS index: {faiss_path}")
        print(f"   📋 Metadata: {metadata_path}")
        
        
        return str(faiss_path), str(metadata_path)
    
    def prepare_chatbot(self, vector_db_path: str, metadata_path: str):
        """
        Prepare and return chatbot instance.
        
        Args:
            vector_db_path: Path to FAISS index
            metadata_path: Path to metadata JSON
            
        Returns:
            RFPChatbot instance
        """
        print("\n" + "=" * 60)
        print("🤖 STEP 5: Preparing Chatbot")
        print("=" * 60)
        
        chatbot = create_chatbot(
            vector_db_path,
            metadata_path,
            self.api_key
        )
        
        print("\n✅ Chatbot ready for queries!")
        
        return chatbot
    
    def run_full_pipeline(self, 
                         rfp_file: str, 
                         vendor_files: List[tuple],
                         skip_extraction: bool = False,
                         run_chatbot: bool = True) -> Dict:
        """
        Run the complete pipeline from start to finish.
        
        Args:
            rfp_file: Path to RFP document
            vendor_files: List of tuples (file_path, vendor_name)
            skip_extraction: Skip requirement extraction step (faster)
            run_chatbot: Launch interactive chatbot after processing
            
        Returns:
            Dictionary with all results and paths
        """
        print("\n" + "=" * 60)
        print("🎯 RFP ANALYSIS PIPELINE - FULL RUN")
        print("=" * 60)
        print(f"📋 RFP File: {rfp_file}")
        print(f"📦 Vendor Files: {len(vendor_files)}")
        print()
        
        results = {}
        
        # Step 1: Process RFP
        rfp_results = self.process_rfp(rfp_file)
        results["rfp"] = rfp_results
        
        # Step 2: Process Vendors
        vendor_results = self.process_vendors(vendor_files)
        results["vendors"] = vendor_results
        
        # Step 3: Extract Requirements (optional)
        if not skip_extraction:
            vendor_jsons = [(v["json"], name) for name, v in vendor_results.items()]
            extraction_results = self.extract_requirements(
                rfp_results["json"],
                vendor_jsons
            )
            results["extraction"] = extraction_results
        else:
            print("\n⏭️  Skipping extraction step")
            
        
        ## ⚖️ STEP 3.5: Evaluating Compliance Before Embeddings
        print("\n⚖️ STEP 3.5: Evaluating Compliance Against Mandatory Requirements")

        # Path to the RFP analysis JSON (created in Step 3)
        rfp_analysis_file = str(self.analysis_dir / "rfp_chunk_analysis.json")

        # Automatically collect vendor analysis files
        vendor_analysis_files = {}
        for file in self.analysis_dir.glob("*_analysis.json"):
            name = file.stem.replace("_analysis", "")
            if name.lower() != "rfp_chunk":
                vendor_analysis_files[name] = str(file)

        # Use the NEW ComplianceChecker (class-based, flexible)
        checker = compliance_checker.ComplianceChecker(
            model_name="all-MiniLM-L6-v2",   # optional (default)
            threshold=0.75                    # optional (default)
        )

        # Evaluate all vendors
        compliance_results = checker.evaluate_all_vendors(
            rfp_analysis_file,
            vendor_analysis_files,
            output_dir=str(self.output_dir / "compliance")
        )

        # 🚫 STEP 4.5: Identify vendors that are NON-compliant
        non_compliant_vendors = [
            name for name, data in compliance_results.items()
            if not data.get("compliant", False)
        ]

        if non_compliant_vendors:
            print(f"⚠️ These vendors are NON-compliant and will be skipped: "
                  f"{', '.join(non_compliant_vendors)}")
        else:
            print("✅ All vendors are fully compliant with mandatory requirements")

        # Filter vendor JSON list to ONLY compliant vendors
        vendor_json_paths = [
            v["json"] for name, v in vendor_results.items()
            if name not in non_compliant_vendors
        ]


        # Step 5: Create Embeddings
        vendor_json_paths = [v["json"] for v in vendor_results.values()]
        faiss_path, metadata_path = self.create_embeddings(
            rfp_results["json"],
            vendor_json_paths
        )
        results["embeddings"] = {
            "faiss": faiss_path,
            "metadata": metadata_path
        }
        
        # Step 6: Prepare Chatbot
        chatbot = self.prepare_chatbot(faiss_path, metadata_path)
        results["chatbot"] = chatbot
        
        # Print summary
        print("\n" + "=" * 60)
        print("🎉 PIPELINE COMPLETE!")
        print("=" * 60)
        print(f"📊 Total chunks: RFP ({len(rfp_results['chunks'])}) + Vendors ({sum(len(v['chunks']) for v in vendor_results.values())})")
        print(f"📁 All outputs saved to: {self.output_dir}")
        print()
        
        # Run interactive chatbot if requested
        if run_chatbot:
            print("🤖 Launching interactive chatbot...")
            print("   Type your questions or 'exit' to quit")
            print()
            chatbot.run_interactive()
        
        return results


def main():
    """Command-line interface for the RFP Analysis System."""
    parser = argparse.ArgumentParser(
        description="RFP Analysis System - Process RFPs and vendor responses for AI-powered analysis"
    )
    
    parser.add_argument(
        "--rfp",
        required=True,
        help="Path to RFP document (PDF, DOC, DOCX)"
    )
    
    parser.add_argument(
        "--vendors",
        nargs="+",
        help="Paths to vendor response documents. Format: path:name path:name ..."
    )
    
    parser.add_argument(
        "--output",
        default="output",
        help="Output directory (default: output)"
    )
    
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=512,
        help="Minimum tokens per chunk (default: 512)"
    )
    
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1024,
        help="Maximum tokens per chunk (default: 1024)"
    )
    
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Skip requirement extraction step (faster processing)"
    )
    
    parser.add_argument(
        "--no-chatbot",
        action="store_true",
        help="Don't launch interactive chatbot after processing"
    )
    
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (or set OPENAI_API_KEY environment variable)"
    )
    
    args = parser.parse_args()
    
    # Parse vendor files
    vendor_files = []
    if args.vendors:
        for vendor_spec in args.vendors:
            if ":" in vendor_spec:
                path, name = vendor_spec.rsplit(":", 1)
            else:
                path = vendor_spec
                name = Path(vendor_spec).stem
            vendor_files.append((path, name))
    
    # Initialize system
    system = RFPAnalysisSystem(
        output_dir=args.output,
        openai_api_key=args.api_key,
        min_tokens=args.min_tokens,
        max_tokens=args.max_tokens
        # project_id, rfp_id, vendor_doc_ids can be passed here later if needed
    )
    
    # Run pipeline
    results = system.run_full_pipeline(
        rfp_file=args.rfp,
        vendor_files=vendor_files,
        skip_extraction=args.skip_extraction,
        run_chatbot=not args.no_chatbot
    )
    
    return results


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
