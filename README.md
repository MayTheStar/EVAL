# 🧠 EVAL – Intelligent RFP & Vendor Response Analysis Platform

**EVAL** is an AI-powered platform that automates the evaluation of *Request for Proposals (RFPs)* and *Vendor Responses*.  
It intelligently extracts requirements, compares vendor capabilities, and provides real-time compliance insights through an interactive web interface and integrated chatbot.

---

## 🚀 Key Features

- **Automated RFP Requirement Extraction**  
  Uses advanced NLP models to identify and structure RFP requirements.

- **Vendor Response Analysis**  
  Extracts capabilities, commitments, and differentiators from vendor documents.

- **Compliance Evaluation**  
  Automatically checks each vendor against mandatory and desirable requirements.

- **Interactive Dashboards**  
  Displays evaluation results and insights visually for faster decision-making.

- **AI Chatbot Assistant**  
  Allows users to query results naturally and explore comparisons instantly.

- **Modular & Scalable Architecture**  
  Designed for easy integration, extensibility, and production deployment.

  ---- 
## 📁 Project Structure

```bash
.
├── README.md
├── ai_engine
│   └── __pycache__
│       ├── LLMSecDetector.cpython-313.pyc
│       ├── __init__.cpython-313.pyc
│       ├── parser.cpython-313.pyc
│       └── pdf_processing.cpython-313.pyc
├── backend
│   ├── __pycache__
│   │   └── backend.cpython-313.pyc
│   └── core
│       ├── __pycache__
│       │   ├── config.cpython-313.pyc
│       │   └── database.cpython-313.pyc
│       ├── core_config.py
│       ├── core_main.py
│       ├── core_models.py
│       ├── database.py
│       ├── models
│       │   └── __pycache__
│       │       ├── document.cpython-313.pyc
│       │       ├── requirement.cpython-313.pyc
│       │       └── vendor_claim.cpython-313.pyc
│       └── services
│           └── __pycache__
│               └── init_db.cpython-313.pyc
├── chunks_metadata.json
├── data
│   └── results
├── docker-compose.yml
├── docs
│   └── SPRINT_1_REPORT.md
├── frontend
│   └── package.json
├── outputs
│   └── c394b603-d86f-40c0-90c7-86468650c4dd
│       ├── chunks
│       │   └── rfp_rfp_USask_RFP_chunks.txt
│       └── embeddings
│           └── chunks_faiss.index
├── requirements-old.txt
├── requirements.txt
├── sample_rfp.pdf
├── tests
│   ├── test_ai.py
│   ├── test_api.py
│   └── test_integration.py
├── vendor_responses
│   └── BeamData-2.docx
└── web app
    ├── __pycache__
    │   ├── chatbot.cpython-313.pyc
    │   ├── compliance_checker.cpython-313.pyc
    │   ├── embeder.cpython-313.pyc
    │   ├── extractor.cpython-313.pyc
    │   ├── main.cpython-313.pyc
    │   ├── parser.cpython-313.pyc
    │   ├── vendor_capability_extractor.cpython-313.pyc
    │   └── vendor_parser.cpython-313.pyc
    ├── app.py
    ├── chatbot.py
    ├── compliance_checker.py
    ├── config.py
    ├── embeder.py
    ├── extractor.py
    ├── main.py
    ├── outputs
    │   ├── 75cd39dc-7782-4322-a95a-098b479093f9
    │   │   ├── chunks
    │   │   │   └── rfp_USask_RFP_chunks.txt
    │   │   └── embeddings
    │   │       └── chunks_faiss.index
    │   ├── c31c106e-d35f-492e-a19d-d68b86788a56
    │   │   ├── analysis
    │   │   │   ├── Leafbridge_analysis.json
    │   │   │   └── rfp_chunk_analysis.json
    │   │   ├── chunks
    │   │   │   ├── Leafbridge_capability_analysis.json
    │   │   │   ├── Leafbridge_chunks.json
    │   │   │   ├── rfp_RFP_CP-730126_Generative_AI_RFP_chunks.json
    │   │   │   └── rfp_RFP_CP-730126_Generative_AI_RFP_chunks.txt
    │   │   └── embeddings
    │   │       ├── chunks_faiss.index
    │   │       └── chunks_metadata.json
    │   └── compliance
    │       ├── BeamData_compliance.json
    │       ├── Cognivize_Technologies_FZ_compliance.json
    │       └── Leafbridge_compliance.json
    ├── parser.py
    ├── requirements.txt
    ├── static
    │   ├── css
    │   │   └── style.css
    │   └── js
    │       ├── chatbot.js
    │       ├── dashboard.js
    │       ├── files.js
    │       ├── upload_rfp.js
    │       └── upload_vendor.js
    ├── templates
    │   ├── chatbot.html
    │   ├── dashboard.html
    │   ├── files.html
    │   ├── landing.html
    │   ├── upload_rfp.html
    │   └── upload_vendor.html
    ├── uploads
    │   └── c31c106e-d35f-492e-a19d-d68b86788a56
    │       ├── rfp_RFP_CP-730126_Generative_AI_RFP.pdf
    │       └── vendor_Leafbridge.pdf
    ├── util.py
    ├── vendor_capability_extractor.py
    └── vendor_parser.py

---

## ⚙️ Tech Stack

| Layer | Technology | Purpose |
|-------|-------------|----------|
| **Frontend** | HTML, CSS, JavaScript | Interactive UI |
| **Backend** | Flask / FastAPI | API and workflow orchestration |
| **AI/NLP Engine** | OpenAI GPT-4o-mini, SentenceTransformers | Requirement & capability extraction |
| **Database** | PostgreSQL | Store extracted data and metadata |
| **Infrastructure** | Docker, DVC, MLflow | Containerization and model tracking |

---

## 🧩 Core Modules Overview

| Module | Description |
|--------|--------------|
| `parser.py` | Splits and preprocesses RFP and vendor documents into chunks |
| `extractor.py` | Extracts requirements and capabilities using OpenAI |
| `compliance_checker.py` | Compares extracted data to determine compliance |
| `chatbot.py` | Interactive Q&A system for users to explore insights |
| `vendor_capability_extractor.py` | Extracts and analyzes vendor claims |
| `main.py` | Orchestrates the full end-to-end pipeline |

---

## 🧰 Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/MayTheStar/EVAL.git
cd EVAL
