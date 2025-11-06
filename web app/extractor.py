"""
RFP and Vendor Response Analysis Extractor
Analyzes chunks using OpenAI to extract requirements, capabilities, and evaluation labels.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Literal
from openai import OpenAI
from dotenv import load_dotenv


# ----------------------------
# Configuration
# ----------------------------
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0


class ChunkAnalyzer:
    """Analyzes document chunks using OpenAI API."""
    
    def __init__(self, api_key: str = None, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE):
        """
        Initialize the analyzer.
        
        Args:
            api_key: OpenAI API key (if None, loads from environment)
            model: OpenAI model to use
            temperature: Model temperature setting
        """
        if api_key is None:
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY in environment or pass as parameter.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
    
    def analyze_chunk(self, chunk_text: str, prompt_type: Literal["RFP", "Vendor"] = "RFP") -> Dict:
        """
        Analyze a single chunk of text.
        
        Args:
            chunk_text: Text content to analyze
            prompt_type: Type of analysis ("RFP" or "Vendor")
            
        Returns:
            Dictionary containing analysis results
        """
        if prompt_type == "RFP":
            role_description = (
                "You are an expert in analyzing government and corporate RFPs. "
                "Your task is to extract all explicit and implied requirements."
            )
        else:
            role_description = (
                "You are an expert analyzing vendor proposals in response to RFPs. "
                "Extract all capabilities, commitments, or deliverables mentioned by the vendor."
            )
        
        prompt = f"""
{role_description}

Instructions:
1. Extract key actionable points or requirements.
2. Summarize the text in 2–3 sentences under "summary".
3. Identify key focus areas under "evaluation_labels" (e.g., Technical, Financial, Compliance).

Return valid JSON:
{{
    "requirements": [],
    "summary": "",
    "evaluation_labels": []
}}

Now analyze:
{chunk_text}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature
            )
            content = response.choices[0].message.content
            chunk_output = json.loads(content)
        except Exception as e:
            print(f"⚠️ Error analyzing chunk: {e}")
            chunk_output = {
                "requirements": [],
                "summary": "",
                "evaluation_labels": [],
                "raw_model_output": content if 'content' in locals() else ""
            }
        else:
            chunk_output["raw_model_output"] = content
        
        return chunk_output


def read_chunks_from_txt(file_path: str) -> List[str]:
    """
    Read chunks separated by === markers from a text file.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        List of chunk texts
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    chunks = content.split("=" * 60)
    processed_chunks = []
    
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.splitlines()
        if lines and lines[0].startswith("CHUNK"):
            text = "\n".join(lines[1:]).strip()
        else:
            text = chunk
        processed_chunks.append(text)
    
    return processed_chunks


def read_chunks_from_json(file_path: str) -> List[Dict]:
    """
    Read chunks from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of chunk dictionaries
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_document_chunks(chunks_file: str, output_file: str, 
                           prompt_type: Literal["RFP", "Vendor"] = "RFP",
                           api_key: str = None, model: str = DEFAULT_MODEL) -> List[Dict]:
    """
    Analyze all chunks in a document.
    
    Args:
        chunks_file: Path to chunks file (TXT or JSON)
        output_file: Path to save analysis results
        prompt_type: Type of analysis ("RFP" or "Vendor")
        api_key: OpenAI API key
        model: OpenAI model to use
        
    Returns:
        List of analysis results
    """
    analyzer = ChunkAnalyzer(api_key=api_key, model=model)
    
    # Determine file type and read chunks
    file_path = Path(chunks_file)
    if file_path.suffix == '.txt':
        chunks = read_chunks_from_txt(chunks_file)
        chunk_texts = chunks
    elif file_path.suffix == '.json':
        chunks = read_chunks_from_json(chunks_file)
        chunk_texts = [c.get("contextualized_text") or c.get("text", "") for c in chunks]
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    print(f"📄 Total chunks to analyze: {len(chunk_texts)}")
    
    results = []
    for i, chunk_text in enumerate(chunk_texts):
        print(f"Analyzing chunk {i+1}/{len(chunk_texts)}...")
        result = analyzer.analyze_chunk(chunk_text, prompt_type)
        results.append(result)
    
    # Save results
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Analysis saved to {output_file}")
    return results


def analyze_rfp_and_vendors(rfp_chunks_file: str, vendor_chunks_files: List[tuple],
                            output_dir: str, api_key: str = None, model: str = DEFAULT_MODEL) -> Dict:
    """
    Analyze RFP and multiple vendor response files.
    
    Args:
        rfp_chunks_file: Path to RFP chunks file
        vendor_chunks_files: List of tuples (file_path, vendor_name)
        output_dir: Directory to save analysis results
        api_key: OpenAI API key
        model: OpenAI model to use
        
    Returns:
        Dictionary with RFP and vendor analysis results
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # Analyze RFP
    print("\n📋 Analyzing RFP document...")
    rfp_output = output_path / "rfp_chunk_analysis.json"
    rfp_results = analyze_document_chunks(
        rfp_chunks_file,
        str(rfp_output),
        prompt_type="RFP",
        api_key=api_key,
        model=model
    )
    results["rfp"] = rfp_results
    
    # Analyze each vendor
    results["vendors"] = {}
    for vendor_file, vendor_name in vendor_chunks_files:
        print(f"\n🔹 Analyzing vendor: {vendor_name}")
        vendor_output = output_path / f"{vendor_name}_analysis.json"
        vendor_results = analyze_document_chunks(
            vendor_file,
            str(vendor_output),
            prompt_type="Vendor",
            api_key=api_key,
            model=model
        )
        results["vendors"][vendor_name] = vendor_results
    
    print("\n🎯 All analyses complete!")
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        chunks_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "analysis.json"
        prompt_type = sys.argv[3] if len(sys.argv) > 3 else "RFP"
        
        analyze_document_chunks(chunks_file, output_file, prompt_type)
    else:
        print("Usage: python extractor.py <chunks_file> [output_file] [RFP|Vendor]")