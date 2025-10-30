import re
import json
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class Section:
    title: str
    start_page: int
    end_page: int
    content: str
    level: int  # heading level (1 for main, 2 for sub, etc.)

class RFPSectionDetector:
    def __init__(self):
        # Regex patterns for detecting headings and sections
        self.heading_patterns = [
            # Main headings
            (r'^([A-Z][A-Z\s&,]+)$', 1),  # All uppercase
            (r'^(EXHIBIT [A-Z][\.\-:].*?)$', 1),  # Exhibits
            (r'^(APPENDIX [A-Z][\.\-:].*?)$', 1),  # Appendices
            
            # Subheadings with numbers
            (r'^(\d+\.\s+[A-Z][A-Za-z\s]+)$', 2),  # 1. Title
            (r'^([A-Z]\.\s+[A-Z][A-Za-z\s]+)$', 2),  # A. Title
            (r'^(Task\s+\d+[A-Z]?:.*?)$', 2),  # Task 1A:
            (r'^(Project\s+\d+:.*?)$', 2),  # Project 1:
            
            # Secondary subheadings
            (r'^(\d+\.\d+\.\s+.*?)$', 3),  # 1.1. Title
            (r'^([A-Z]\d+\.\s+.*?)$', 3),  # G1. Title
        ]
        
        # Keywords that indicate the start of new sections
        self.section_keywords = [
            'Introduction', 'Scope of Work', 'Schedule', 'Proposal Submittal',
            'Evaluation', 'Terms & Conditions', 'Instructions', 'Deliverables',
            'Deadline', 'Budget', 'Requirements', 'Certifications'
        ]

    def detect_heading(self, text: str) -> Tuple[str, int]:
        """Detect heading and its level"""
        text = text.strip()
        
        # Try all patterns
        for pattern, level in self.heading_patterns:
            match = re.match(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip(), level
        
        # Check for section keywords
        for keyword in self.section_keywords:
            if text.startswith(keyword):
                return text, 2
        
        return None, 0

    def is_section_boundary(self, text: str, prev_text: str = "") -> bool:
        """Determine if the text marks a new section boundary"""
        # Check if heading
        heading, level = self.detect_heading(text)
        if heading and level <= 2:
            return True
        
        # Check for major formatting change
        if len(text) < 100 and text.isupper() and len(text.split()) <= 10:
            return True
        
        return False

    def extract_sections(self, pages: List[Dict]) -> List[Section]:
        """Extract sections from pages"""
        sections = []
        current_section = None
        current_content = []
        
        for page in pages:
            page_num = page['page_number']
            text = page['cleaned_text']
            
            # Split text into lines
            lines = text.split('\n')
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Try to detect heading
                heading, level = self.detect_heading(line)
                
                if heading and level <= 2:
                    # Save previous section
                    if current_section:
                        current_section.content = '\n'.join(current_content)
                        current_section.end_page = page_num - 1 if page_num > current_section.start_page else page_num
                        sections.append(current_section)
                    
                    # Start new section
                    current_section = Section(
                        title=heading,
                        start_page=page_num,
                        end_page=page_num,
                        content="",
                        level=level
                    )
                    current_content = []
                else:
                    # Add content to current section
                    if current_section:
                        current_content.append(line)
        
        # Save last section
        if current_section:
            current_section.content = '\n'.join(current_content)
            current_section.end_page = pages[-1]['page_number']
            sections.append(current_section)
        
        return sections

    def analyze_document(self, json_data: Dict) -> Dict:
        """Comprehensive document analysis"""
        pages = json_data['pages']
        sections = self.extract_sections(pages)
        
        # Gather statistics
        stats = {
            'total_pages': len(pages),
            'total_sections': len(sections),
            'sections_by_level': {},
            'average_section_length': 0,
            'sections_detail': []
        }
        
        total_content_length = 0
        for section in sections:
            # Statistics by level
            level_key = f'level_{section.level}'
            stats['sections_by_level'][level_key] = stats['sections_by_level'].get(level_key, 0) + 1
            
            # Content length
            content_length = len(section.content)
            total_content_length += content_length
            
            # Section details
            stats['sections_detail'].append({
                'title': section.title,
                'level': section.level,
                'start_page': section.start_page,
                'end_page': section.end_page,
                'page_span': section.end_page - section.start_page + 1,
                'content_length': content_length,
                'preview': section.content[:200] + '...' if len(section.content) > 200 else section.content
            })
        
        if sections:
            stats['average_section_length'] = total_content_length / len(sections)
        
        return stats

# Load data
with open('response_1761658228787.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Apply section detection
detector = RFPSectionDetector()
analysis = detector.analyze_document(data)

# Display results
print("=" * 80)
print("Document Section Analysis")
print("=" * 80)
print(f"\nTotal pages: {analysis['total_pages']}")
print(f"Total detected sections: {analysis['total_sections']}")
print(f"Average section length: {analysis['average_section_length']:.0f} characters")

print("\n" + "=" * 80)
print("Sections by Level:")
print("=" * 80)
for level, count in sorted(analysis['sections_by_level'].items()):
    print(f"{level}: {count} sections")

print("\n" + "=" * 80)
print("Main Sections Details:")
print("=" * 80)

# Display first 20 sections
for i, section in enumerate(analysis['sections_detail'][:20], 1):
    print(f"\n{i}. {section['title']}")
    print(f"   Level: {section['level']}")
    print(f"   Pages: {section['start_page']}-{section['end_page']} (Span: {section['page_span']} pages)")
    print(f"   Content length: {section['content_length']} characters")
    print(f"   Preview: {section['preview'][:150]}...")

# Save full results
output_file = 'rfp_sections_analysis.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(analysis, f, ensure_ascii=False, indent=2)

print(f"\n\nFull analysis saved to: {output_file}")
