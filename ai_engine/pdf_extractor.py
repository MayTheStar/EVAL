import PyPDF2
import pdfplumber
import tabula
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List

class PDFTextExtractorT3:
   
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        self.pdf_reader = None
        self.total_pages = 0

    def extract_all(self) -> Dict[str, Any]:
      
        extracted_data = {'file_name': self.pdf_path.name, 'pages': []}

        with open(self.pdf_path, 'rb') as f:
            self.pdf_reader = PyPDF2.PdfReader(f)
            self.total_pages = len(self.pdf_reader.pages)

            for page_num in range(self.total_pages):
                print(f"Extracting page {page_num + 1}/{self.total_pages}...")
                page_data = self._extract_page(page_num + 1)
                extracted_data['pages'].append(page_data)

        return extracted_data

    def _extract_page(self, page_num: int) -> Dict[str, Any]:
        """
        Extract text and tables from a single page.
        """
        page_data = {'page_number': page_num, 'text': '', 'tables': []}

        
        page = self.pdf_reader.pages[page_num - 1]
        page_text = page.extract_text()
        page_data['text'] = page_text.strip() if page_text else ""

        
        pdfplumber_tables = self._extract_tables_pdfplumber(page_num)
        if pdfplumber_tables:
            page_data['tables'] = pdfplumber_tables
        else:
            
            page_data['tables'] = self._extract_tables_tabula(page_num)

        return page_data

    def _extract_tables_pdfplumber(self, page_num: int) -> List[Dict[str, Any]]:
        """
        Try extracting tables using pdfplumber.
        """
        tables = []
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                page = pdf.pages[page_num - 1]
                extracted_tables = page.extract_tables()
                for idx, table in enumerate(extracted_tables):
                    if table:
                        tables.append({
                            'table_index': idx + 1,
                            'rows': len(table),
                            'columns': len(table[0]) if table else 0,
                            'data': table,
                            'method': 'pdfplumber'
                        })
        except Exception as e:
            print(f" pdfplumber failed on page {page_num}: {e}")
        return tables

    def _extract_tables_tabula(self, page_num: int) -> List[Dict[str, Any]]:
        """
        Try extracting tables using tabula-py.
        """
        tables = []
        try:
            dfs = tabula.read_pdf(
                str(self.pdf_path),
                pages=page_num,
                multiple_tables=True,
                lattice=True,
                stream=True
            )
            for idx, df in enumerate(dfs):
                if not df.empty:
                    table_data = [df.columns.tolist()] + df.values.tolist()
                    tables.append({
                        'table_index': idx + 1,
                        'rows': len(table_data),
                        'columns': len(table_data[0]),
                        'data': table_data,
                        'method': 'tabula'
                    })
        except Exception as e:
            print(f" tabula failed on page {page_num}: {e}")
        return tables



if __name__ == "__main__":
    
    
    PDF_FILE_NAME = "RFP_Advancing-Roadway-Tolling_FINAL (1).pdf"
    
    try:
        print(f"Starting extraction from: {PDF_FILE_NAME}\n")
        
        
        extractor = PDFTextExtractorT3(PDF_FILE_NAME)
        data = extractor.extract_all()

        
        print("\n--- Extracted Data Dictionary (JSON Format) ---")
        
        
        json_output = json.dumps(data, ensure_ascii=False, indent=4)
        
       
        print(json_output)
        
        print("\n--- End of Output ---")

    except FileNotFoundError:
        print(f"\n❌ERROR: PDF not found at '{PDF_FILE_NAME}'. Please check the file name and path.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")