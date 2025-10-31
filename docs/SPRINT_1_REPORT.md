# SPRINT 1 — Technical Report

## 🧭 Overview
This document provides a summary of the technical progress achieved during *Sprint 1* for the *EVAL Project*.  
The main focus of this sprint was to set up the core infrastructure, build the text extraction pipeline, and ensure frontend-backend integration.

---

## 👥 Team Members & Roles
- *Ryana Aljuaid* — Parsing libraries selection and technical research  
- *May Alotaibi* — Frontend upload interface & repository setup  
- *Teif Alshareef* — Text cleaning module & workflow documentation  
- *Ghadi Aljohani* — Backend API development and integration  
- *Mawaddah Alsufyani* — Sprint documentation (system diagrams, workflows, README update)

---

## 🎯 Sprint Goals
1. Set up project repository structure (backend, frontend, models, docs).  
2. Test and select the best PDF parsing libraries for extraction and OCR.  
3. Implement the backend text extraction and cleaning pipeline.  
4. Build a basic frontend upload screen and connect it to the backend.  
5. Document all workflows and system architecture updates.

---

## 🧩 System Architecture
The system follows a modular architecture divided into three main layers:

- *Frontend (React-based)* — Handles user interactions and file uploads.  
- *Backend (FastAPI or Flask)* — Processes files, performs extraction, and returns structured text.  
- *AI Engine (Python)* — Contains modules for PDF parsing, summarization, and document comparison.

### Simplified Diagram


[ User Interface ]
↓
[ Upload API ]
↓
[ Text Extraction → Cleaning → Storage ]
↓
[ Summarized and Comparable Results ]

---

## 🔄 Workflow Summary
1. User uploads RFP or Vendor PDF through the web interface.  
2. The file is sent to the backend /upload_file endpoint.  
3. The backend triggers the extraction pipeline (pdfplumber, PyPDF2, pytesseract).  
4. Extracted text is cleaned — removing headers, footers, and extra spaces.  
5. Clean text is displayed on the frontend in a scrollable container.  

---

## ⚙ Tools & Technologies
| Category | Tools Used |
|-----------|-------------|
| Backend   | Python, FastAPI/Flask |
| Frontend  | React.js |
| AI Engine | PyPDF2, pdfplumber, pytesseract |
| Version Control | Git, GitHub |
| Documentation | Markdown, Notion |

---

## 🚧 Challenges
- Handling table extraction from scanned PDF files required OCR testing.  
- Maintaining text formatting after cleaning needed custom regex rules.  
- Ensuring smooth connection between frontend and backend required debugging CORS issues.

---

## ✅ Sprint 1 Deliverables
- ✅ GitHub repository setup  
- ✅ PDF extraction and cleaning modules implemented  
- ✅ Frontend upload and preview page created  
- ✅ API connection between frontend and backend completed  
- 🕒 Sprint documentation (README + workflows + system diagrams) — in progress  

---

## 💡 Next Steps (Sprint 2 Preview)
- Enhance text comparison between RFP and Vendor documents  
- Implement AI-based summarization and Q&A chatbot  
- Develop structured database models for extracted data storage  

---

## 🏁 Conclusion
Sprint 1 successfully established the foundation of the EVAL system.  
The backend, frontend, and AI modules were integrated and functional.  
Documentation updates and refined architecture diagrams will support scalability for the next sprint.
