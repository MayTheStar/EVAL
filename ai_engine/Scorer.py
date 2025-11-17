"""
Advanced RFP Vendor Scoring System
Evaluates vendor proposals against RFP requirements using multiple scoring techniques.
Includes mandatory compliance, semantic matching, criteria-based scoring, and confidence metrics.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sentence_transformers import SentenceTransformer, util
from openai import OpenAI
from dotenv import load_dotenv
import os
from collections import defaultdict
from dataclasses import dataclass, asdict


@dataclass
class ScoreBreakdown:
    """Detailed score breakdown for a single criterion."""
    criterion_name: str
    weight: float
    raw_score: float
    weighted_score: float
    confidence: float
    evidence: List[str]
    gaps: List[str]


@dataclass
class VendorScore:
    """Complete vendor scoring result."""
    vendor_name: str
    total_score: float
    confidence_score: float
    is_compliant: bool
    disqualification_reason: Optional[str]
    
    # Detailed scores
    mandatory_compliance_score: float
    technical_score: float
    financial_score: float
    experience_score: float
    methodology_score: float
    innovation_score: float
    
    # Breakdown
    criteria_breakdown: List[ScoreBreakdown]
    
    # Summary
    strengths: List[str]
    weaknesses: List[str]
    missing_requirements: List[str]
    
    # Metadata
    total_requirements: int
    met_requirements: int
    evaluation_model: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result['criteria_breakdown'] = [asdict(cb) for cb in self.criteria_breakdown]
        return result


class VendorScorer:
    """
    Advanced vendor scoring system with multiple evaluation techniques.
    """
    
    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        openai_model: str = "gpt-4o-mini",
        compliance_threshold: float = 0.75,
        api_key: Optional[str] = None
    ):
        """
        Initialize the scoring system.
        
        Args:
            embedding_model: SentenceTransformer model for semantic similarity
            openai_model: OpenAI model for advanced evaluation
            compliance_threshold: Threshold for semantic matching (0-1)
            api_key: OpenAI API key (loads from env if None)
        """
        self.embedding_model = SentenceTransformer(embedding_model)
        self.compliance_threshold = compliance_threshold
        self.openai_model = openai_model
        
        # Load OpenAI client
        if api_key is None:
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY")
        
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
        else:
            self.openai_client = None
            print("⚠️  OpenAI client not initialized - advanced scoring features disabled")
    
    # ============================================================
    # MANDATORY COMPLIANCE CHECK
    # ============================================================
    
    def check_mandatory_compliance(
        self,
        rfp_requirements: List[Dict],
        vendor_capabilities: List[Dict]
    ) -> Tuple[bool, List[str], float]:
        """
        Check if vendor meets all mandatory requirements.
        
        Args:
            rfp_requirements: List of RFP requirement dicts with 'text' and 'type'
            vendor_capabilities: List of vendor capability dicts with 'text'
            
        Returns:
            Tuple of (is_compliant, missing_requirements, compliance_percentage)
        """
        # Extract mandatory requirements
        mandatory_reqs = [
            req["text"] for req in rfp_requirements
            if req.get("type") == "mandatory"
        ]
        
        if not mandatory_reqs:
            return True, [], 100.0
        
        # Extract vendor statements
        vendor_statements = [cap["text"] for cap in vendor_capabilities]
        
        if not vendor_statements:
            return False, mandatory_reqs, 0.0
        
        # Check each mandatory requirement
        missing = []
        matched = 0
        
        for req in mandatory_reqs:
            req_emb = self.embedding_model.encode(req, convert_to_tensor=True)
            
            # Compare with all vendor statements
            max_similarity = 0.0
            for statement in vendor_statements:
                stmt_emb = self.embedding_model.encode(statement, convert_to_tensor=True)
                similarity = util.cos_sim(req_emb, stmt_emb).item()
                max_similarity = max(max_similarity, similarity)
            
            if max_similarity >= self.compliance_threshold:
                matched += 1
            else:
                missing.append(req)
        
        compliance_percentage = (matched / len(mandatory_reqs)) * 100
        is_compliant = len(missing) == 0
        
        return is_compliant, missing, compliance_percentage
    
    # ============================================================
    # SEMANTIC SIMILARITY SCORING
    # ============================================================
    
    def calculate_semantic_scores(
        self,
        rfp_requirements: List[Dict],
        vendor_capabilities: List[Dict]
    ) -> Dict[str, float]:
        """
        Calculate semantic similarity scores for different requirement categories.
        
        Returns:
            Dictionary with category scores (0-100)
        """
        if not vendor_capabilities:
            return {
                "technical": 0.0,
                "financial": 0.0,
                "experience": 0.0,
                "methodology": 0.0,
                "overall": 0.0
            }
        
        # Categorize requirements
        categories = {
            "technical": ["technical", "technology", "system", "software", "hardware", "architecture"],
            "financial": ["cost", "price", "budget", "financial", "payment", "fee"],
            "experience": ["experience", "expertise", "qualification", "past", "history", "portfolio"],
            "methodology": ["methodology", "approach", "process", "procedure", "method", "workflow"]
        }
        
        category_scores = {}
        vendor_statements = [cap["text"] for cap in vendor_capabilities]
        
        for category, keywords in categories.items():
            # Filter requirements by category
            category_reqs = [
                req["text"] for req in rfp_requirements
                if any(kw in req["text"].lower() for kw in keywords)
            ]
            
            if not category_reqs:
                category_scores[category] = 50.0  # Neutral score if no requirements in category
                continue
            
            # Calculate average similarity
            total_similarity = 0.0
            count = 0
            
            for req in category_reqs:
                req_emb = self.embedding_model.encode(req, convert_to_tensor=True)
                
                # Find best match from vendor
                best_match = 0.0
                for statement in vendor_statements:
                    stmt_emb = self.embedding_model.encode(statement, convert_to_tensor=True)
                    similarity = util.cos_sim(req_emb, stmt_emb).item()
                    best_match = max(best_match, similarity)
                
                total_similarity += best_match
                count += 1
            
            # Convert to 0-100 scale
            avg_similarity = total_similarity / count if count > 0 else 0.0
            category_scores[category] = avg_similarity * 100
        
        # Calculate overall score
        category_scores["overall"] = np.mean(list(category_scores.values()))
        
        return category_scores
    
    # ============================================================
    # CRITERIA-BASED EVALUATION (OpenAI)
    # ============================================================
    
    def evaluate_with_criteria(
        self,
        rfp_text: str,
        vendor_text: str,
        evaluation_criteria: List[Dict]
    ) -> Tuple[List[ScoreBreakdown], float]:
        """
        Evaluate vendor response against specific criteria using OpenAI.
        
        Args:
            rfp_text: Full RFP text or summary
            vendor_text: Full vendor response text or summary
            evaluation_criteria: List of criteria dicts with 'name', 'description', 'weight'
            
        Returns:
            Tuple of (criteria_breakdown, confidence_score)
        """
        if not self.openai_client:
            # Fallback to simple scoring if OpenAI not available
            return self._fallback_criteria_evaluation(evaluation_criteria), 0.5
        
        prompt = f"""
You are an expert RFP evaluator. Evaluate how well the vendor response addresses each evaluation criterion from the RFP.

RFP Context (key requirements):
{rfp_text[:3000]}

Vendor Response:
{vendor_text[:3000]}

Evaluation Criteria:
{json.dumps(evaluation_criteria, indent=2)}

For each criterion, provide:
1. A score from 0-100
2. Confidence level (0-1) in your assessment
3. 1-2 specific evidence points from the vendor response
4. 1-2 gaps or weaknesses (if any)

Return ONLY valid JSON in this exact format:
{{
  "criteria_scores": [
    {{
      "criterion_name": "string",
      "score": 0-100,
      "confidence": 0-1,
      "evidence": ["point1", "point2"],
      "gaps": ["gap1", "gap2"]
    }}
  ],
  "overall_confidence": 0-1
}}
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Convert to ScoreBreakdown objects
            breakdowns = []
            for criterion_result in result.get("criteria_scores", []):
                # Find original criterion to get weight
                original_criterion = next(
                    (c for c in evaluation_criteria if c["name"] == criterion_result["criterion_name"]),
                    None
                )
                
                weight = original_criterion.get("weight", 1.0) if original_criterion else 1.0
                raw_score = criterion_result["score"]
                
                breakdown = ScoreBreakdown(
                    criterion_name=criterion_result["criterion_name"],
                    weight=weight,
                    raw_score=raw_score,
                    weighted_score=raw_score * weight,
                    confidence=criterion_result.get("confidence", 0.7),
                    evidence=criterion_result.get("evidence", []),
                    gaps=criterion_result.get("gaps", [])
                )
                breakdowns.append(breakdown)
            
            overall_confidence = result.get("overall_confidence", 0.7)
            
            return breakdowns, overall_confidence
            
        except Exception as e:
            print(f"⚠️  OpenAI evaluation failed: {e}")
            return self._fallback_criteria_evaluation(evaluation_criteria), 0.5
    
    def _fallback_criteria_evaluation(self, criteria: List[Dict]) -> List[ScoreBreakdown]:
        """Fallback scoring when OpenAI is unavailable."""
        breakdowns = []
        for criterion in criteria:
            breakdown = ScoreBreakdown(
                criterion_name=criterion["name"],
                weight=criterion.get("weight", 1.0),
                raw_score=50.0,  # Neutral score
                weighted_score=50.0 * criterion.get("weight", 1.0),
                confidence=0.3,  # Low confidence for fallback
                evidence=["Automated evaluation not available"],
                gaps=["Manual review required"]
            )
            breakdowns.append(breakdown)
        return breakdowns
    
    # ============================================================
    # STRENGTHS & WEAKNESSES ANALYSIS
    # ============================================================
    
    def analyze_strengths_weaknesses(
        self,
        vendor_text: str,
        rfp_text: str,
        semantic_scores: Dict[str, float]
    ) -> Tuple[List[str], List[str]]:
        """
        Identify vendor strengths and weaknesses using OpenAI.
        
        Returns:
            Tuple of (strengths, weaknesses)
        """
        if not self.openai_client:
            return self._fallback_strengths_weaknesses(semantic_scores)
        
        prompt = f"""
Analyze this vendor proposal in response to an RFP.

RFP Summary:
{rfp_text[:2000]}

Vendor Proposal:
{vendor_text[:2000]}

Semantic Scores:
{json.dumps(semantic_scores, indent=2)}

Identify:
1. Top 3-5 strengths (what the vendor does well)
2. Top 3-5 weaknesses or gaps (what could be improved)

Be specific and evidence-based. Return ONLY valid JSON:
{{
  "strengths": ["strength1", "strength2", ...],
  "weaknesses": ["weakness1", "weakness2", ...]
}}
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("strengths", []), result.get("weaknesses", [])
            
        except Exception as e:
            print(f"⚠️  Strengths/weaknesses analysis failed: {e}")
            return self._fallback_strengths_weaknesses(semantic_scores)
    
    def _fallback_strengths_weaknesses(
        self,
        semantic_scores: Dict[str, float]
    ) -> Tuple[List[str], List[str]]:
        """Fallback analysis based on semantic scores."""
        strengths = []
        weaknesses = []
        
        for category, score in semantic_scores.items():
            if category == "overall":
                continue
            
            if score >= 75:
                strengths.append(f"Strong {category} capabilities (score: {score:.1f})")
            elif score < 50:
                weaknesses.append(f"Limited {category} coverage (score: {score:.1f})")
        
        if not strengths:
            strengths = ["Adequate baseline response provided"]
        if not weaknesses:
            weaknesses = ["Minor areas for improvement"]
        
        return strengths, weaknesses
    
    # ============================================================
    # COMPREHENSIVE VENDOR SCORING
    # ============================================================
    
    def score_vendor(
        self,
        vendor_name: str,
        rfp_requirements: List[Dict],
        vendor_capabilities: List[Dict],
        rfp_full_text: str,
        vendor_full_text: str,
        evaluation_criteria: Optional[List[Dict]] = None
    ) -> VendorScore:
        """
        Perform comprehensive vendor scoring.
        
        Args:
            vendor_name: Name of the vendor
            rfp_requirements: Extracted RFP requirements
            vendor_capabilities: Extracted vendor capabilities
            rfp_full_text: Full RFP text for context
            vendor_full_text: Full vendor response text
            evaluation_criteria: Optional custom criteria from RFP
            
        Returns:
            Complete VendorScore object
        """
        print(f"\n📊 Scoring {vendor_name}...")
        
        # 1. Mandatory Compliance Check
        is_compliant, missing_reqs, compliance_pct = self.check_mandatory_compliance(
            rfp_requirements,
            vendor_capabilities
        )
        
        if not is_compliant:
            print(f"   ❌ {vendor_name} is NON-COMPLIANT")
            return VendorScore(
                vendor_name=vendor_name,
                total_score=0.0,
                confidence_score=0.95,  # High confidence in disqualification
                is_compliant=False,
                disqualification_reason=f"Missing {len(missing_reqs)} mandatory requirements",
                mandatory_compliance_score=compliance_pct,
                technical_score=0.0,
                financial_score=0.0,
                experience_score=0.0,
                methodology_score=0.0,
                innovation_score=0.0,
                criteria_breakdown=[],
                strengths=[],
                weaknesses=[f"Failed to meet {len(missing_reqs)} mandatory requirements"],
                missing_requirements=missing_reqs[:10],  # Limit to first 10
                total_requirements=len([r for r in rfp_requirements if r.get("type") == "mandatory"]),
                met_requirements=0,
                evaluation_model=self.openai_model
            )
        
        print(f"   ✅ {vendor_name} is COMPLIANT")
        
        # 2. Semantic Similarity Scoring
        semantic_scores = self.calculate_semantic_scores(
            rfp_requirements,
            vendor_capabilities
        )
        
        # 3. Criteria-Based Evaluation
        if evaluation_criteria is None:
            # Generate default criteria
            evaluation_criteria = self._generate_default_criteria()
        
        criteria_breakdown, criteria_confidence = self.evaluate_with_criteria(
            rfp_full_text,
            vendor_full_text,
            evaluation_criteria
        )
        
        # 4. Strengths & Weaknesses
        strengths, weaknesses = self.analyze_strengths_weaknesses(
            vendor_full_text,
            rfp_full_text,
            semantic_scores
        )
        
        # 5. Calculate Final Scores
        # Technical score from semantic + criteria
        technical_score = (
            semantic_scores["technical"] * 0.4 +
            self._get_criteria_score(criteria_breakdown, "Technical") * 0.6
        )
        
        financial_score = (
            semantic_scores["financial"] * 0.4 +
            self._get_criteria_score(criteria_breakdown, "Financial") * 0.6
        )
        
        experience_score = (
            semantic_scores["experience"] * 0.5 +
            self._get_criteria_score(criteria_breakdown, "Experience") * 0.5
        )
        
        methodology_score = (
            semantic_scores["methodology"] * 0.5 +
            self._get_criteria_score(criteria_breakdown, "Methodology") * 0.5
        )
        
        # Innovation score from criteria only
        innovation_score = self._get_criteria_score(criteria_breakdown, "Innovation")
        
        # Calculate weighted total score
        total_score = (
            technical_score * 0.30 +
            financial_score * 0.20 +
            experience_score * 0.20 +
            methodology_score * 0.20 +
            innovation_score * 0.10
        )
        
        # Calculate overall confidence
        confidence_score = self._calculate_confidence(
            criteria_confidence,
            len(vendor_capabilities),
            len(rfp_requirements)
        )
        
        # Count requirements met
        total_reqs = len(rfp_requirements)
        mandatory_count = len([r for r in rfp_requirements if r.get("type") == "mandatory"])
        met_reqs = mandatory_count + int((len(rfp_requirements) - mandatory_count) * (total_score / 100))
        
        print(f"   ✅ Total Score: {total_score:.2f}/100 (Confidence: {confidence_score:.2f})")
        
        return VendorScore(
            vendor_name=vendor_name,
            total_score=round(total_score, 2),
            confidence_score=round(confidence_score, 2),
            is_compliant=True,
            disqualification_reason=None,
            mandatory_compliance_score=round(compliance_pct, 2),
            technical_score=round(technical_score, 2),
            financial_score=round(financial_score, 2),
            experience_score=round(experience_score, 2),
            methodology_score=round(methodology_score, 2),
            innovation_score=round(innovation_score, 2),
            criteria_breakdown=criteria_breakdown,
            strengths=strengths,
            weaknesses=weaknesses,
            missing_requirements=[],
            total_requirements=total_reqs,
            met_requirements=met_reqs,
            evaluation_model=self.openai_model
        )
    
    def _generate_default_criteria(self) -> List[Dict]:
        """Generate default evaluation criteria."""
        return [
            {
                "name": "Technical Capability",
                "description": "Vendor's technical skills and infrastructure",
                "weight": 0.30
            },
            {
                "name": "Financial Proposal",
                "description": "Cost competitiveness and value for money",
                "weight": 0.20
            },
            {
                "name": "Experience & Qualifications",
                "description": "Past performance and relevant experience",
                "weight": 0.20
            },
            {
                "name": "Methodology & Approach",
                "description": "Proposed implementation approach",
                "weight": 0.20
            },
            {
                "name": "Innovation",
                "description": "Creative solutions and added value",
                "weight": 0.10
            }
        ]
    
    def _get_criteria_score(self, criteria_breakdown: List[ScoreBreakdown], name_contains: str) -> float:
        """Extract score for criteria containing a specific string."""
        matching = [
            cb.raw_score for cb in criteria_breakdown
            if name_contains.lower() in cb.criterion_name.lower()
        ]
        return np.mean(matching) if matching else 50.0
    
    def _calculate_confidence(
        self,
        criteria_confidence: float,
        num_vendor_caps: int,
        num_rfp_reqs: int
    ) -> float:
        """Calculate overall confidence score."""
        # Base confidence from OpenAI evaluation
        confidence = criteria_confidence
        
        # Adjust based on data availability
        if num_vendor_caps < 5:
            confidence *= 0.7  # Low data confidence
        elif num_vendor_caps > 20:
            confidence = min(confidence * 1.1, 1.0)  # High data confidence
        
        if num_rfp_reqs < 3:
            confidence *= 0.8
        
        return min(confidence, 0.95)  # Cap at 0.95
    
    # ============================================================
    # BATCH SCORING
    # ============================================================
    
    def score_all_vendors(
        self,
        rfp_analysis_file: str,
        vendor_analysis_files: Dict[str, str],
        rfp_chunks_file: str,
        vendor_chunks_files: Dict[str, str],
        output_dir: str,
        evaluation_criteria: Optional[List[Dict]] = None
    ) -> Dict[str, VendorScore]:
        """
        Score all vendors and save results.
        
        Args:
            rfp_analysis_file: Path to RFP requirement analysis JSON
            vendor_analysis_files: Dict of {vendor_name: analysis_file_path}
            rfp_chunks_file: Path to RFP chunks JSON
            vendor_chunks_files: Dict of {vendor_name: chunks_file_path}
            output_dir: Directory to save scoring results
            evaluation_criteria: Optional custom criteria
            
        Returns:
            Dictionary of {vendor_name: VendorScore}
        """
        print("\n" + "=" * 60)
        print("🎯 VENDOR SCORING ENGINE")
        print("=" * 60)
        
        # Load RFP data
        rfp_requirements = self._load_requirements_from_analysis(rfp_analysis_file)
        rfp_full_text = self._load_full_text_from_chunks(rfp_chunks_file)
        
        # Score each vendor
        results = {}
        for vendor_name, analysis_file in vendor_analysis_files.items():
            try:
                # Load vendor data
                vendor_capabilities = self._load_requirements_from_analysis(analysis_file)
                vendor_chunks_path = vendor_chunks_files.get(vendor_name)
                vendor_full_text = self._load_full_text_from_chunks(vendor_chunks_path) if vendor_chunks_path else ""
                
                # Score vendor
                score = self.score_vendor(
                    vendor_name=vendor_name,
                    rfp_requirements=rfp_requirements,
                    vendor_capabilities=vendor_capabilities,
                    rfp_full_text=rfp_full_text,
                    vendor_full_text=vendor_full_text,
                    evaluation_criteria=evaluation_criteria
                )
                
                results[vendor_name] = score
                
                # Save individual result
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                
                result_file = output_path / f"{vendor_name}_score.json"
                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump(score.to_dict(), f, indent=2, ensure_ascii=False)
                
                print(f"   💾 Saved score to {result_file}")
                
            except Exception as e:
                print(f"   ❌ Error scoring {vendor_name}: {e}")
                continue
        
        # Save combined summary
        summary_file = Path(output_dir) / "scoring_summary.json"
        summary = {
            "vendors": {name: score.to_dict() for name, score in results.items()},
            "evaluation_metadata": {
                "total_vendors": len(results),
                "compliant_vendors": sum(1 for s in results.values() if s.is_compliant),
                "disqualified_vendors": sum(1 for s in results.values() if not s.is_compliant),
                "evaluation_model": self.openai_model,
                "embedding_model": "all-MiniLM-L6-v2"
            }
        }
        
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved scoring summary to {summary_file}")
        print("\n" + "=" * 60)
        print("✅ VENDOR SCORING COMPLETE!")
        print("=" * 60)
        
        return results
    
    def _load_requirements_from_analysis(self, analysis_file: str) -> List[Dict]:
        """Load requirements/capabilities from analysis JSON."""
        with open(analysis_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        requirements = []
        for chunk in data:
            for req in chunk.get("requirements", []):
                requirements.append(req)
        
        return requirements
    
    def _load_full_text_from_chunks(self, chunks_file: str) -> str:
        """Load and concatenate full text from chunks JSON."""
        if not chunks_file or not Path(chunks_file).exists():
            return ""
        
        with open(chunks_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        
        texts = [
            chunk.get("contextualized_text") or chunk.get("text", "")
            for chunk in chunks
        ]
        
        return "\n\n".join(texts)[:10000]  # Limit to 10k chars


# ============================================================
# CLI & TESTING
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Score vendors against RFP")
    parser.add_argument("--rfp-analysis", required=True, help="Path to RFP analysis JSON")
    parser.add_argument("--rfp-chunks", required=True, help="Path to RFP chunks JSON")
    parser.add_argument("--vendor", nargs="+", required=True,
                        help="Vendor pairs: name=analysis_path=chunks_path")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--criteria", help="Optional JSON file with evaluation criteria")
    
    args = parser.parse_args()
    
    # Parse vendor arguments
    vendor_analysis_files = {}
    vendor_chunks_files = {}
    
    for vendor_spec in args.vendor:
        parts = vendor_spec.split("=")
        if len(parts) == 3:
            name, analysis, chunks = parts
            vendor_analysis_files[name] = analysis
            vendor_chunks_files[name] = chunks
    
    # Load criteria if provided
    criteria = None
    if args.criteria:
        with open(args.criteria, "r") as f:
            criteria = json.load(f)
    
    # Run scorer
    scorer = VendorScorer()
    results = scorer.score_all_vendors(
        rfp_analysis_file=args.rfp_analysis,
        vendor_analysis_files=vendor_analysis_files,
        rfp_chunks_file=args.rfp_chunks,
        vendor_chunks_files=vendor_chunks_files,
        output_dir=args.output,
        evaluation_criteria=criteria
    )
    
    print(f"\n🎯 Scored {len(results)} vendors successfully!")