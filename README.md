# 🧠 EVAL  
> AI-powered system for analyzing, summarizing, and comparing RFP and vendor documents.

---

## 📁 Project Structure

```bash
intelligent-rfp-platform
├── backend/
│   ├── api/
│   │   ├── rfp_upload/           # Endpoints for uploading and processing RFP PDF files
│   │   ├── vendor_upload/        # Endpoints for uploading vendor responses
│   │   ├── document_compare/     # Logic for comparing PDFs based on RFP criteria
│   │   ├── summarization/        # AI models for summarizing documents
│   │   ├── extraction/           # Extracting key data (criteria, pricing, compliance, etc.)
│   │   ├── chatbot/              # AI assistant endpoints (Q&A about documents)
│   │   ├── notifications/        # Logic for flagging sections needing manual review
│   │   └── filters/              # API for applying custom filtering rules
│   ├── core/
│   │   ├── models/               # Database models (RFP, VendorResponse, ComparisonResult, etc.)
│   │   ├── services/             # Core business logic
│   │   ├── utils/                # Helper functions (PDF parser, text extraction, etc.)
│   │   ├── config.py             # Environment and system configuration
│   │   └── database.py           # DB connection and ORM setup
│   ├── main.py                   # Main entry point (FastAPI / Flask)
│   └── requirements.txt          # Backend dependencies
│
├── frontend/
│   ├── components/
│   │   ├── UploadSection/        # File upload interface for RFP and Vendor PDFs
│   │   ├── SummaryView/          # Summarized document display
│   │   ├── ComparisonTable/      # Display of comparison results
│   │   ├── FilterPanel/          # Dynamic filtering UI
│   │   ├── ChatbotWidget/        # Integrated chatbot interface
│   │   └── NotificationPanel/    # Alerts for manual review sections
│   ├── pages/
│   │   ├── Dashboard/            # Main user dashboard
│   │   ├── RFPDetails/           # Detailed document and comparison view
│   │   └── Settings/             # Customization and filtering preferences
│   ├── assets/                   # Images, icons, and styles
│   ├── hooks/                    # Custom React hooks (e.g., for API calls)
│   ├── App.jsx                   # Frontend root component
│   ├── index.jsx                 # App entry point
│   └── package.json              # Frontend dependencies
│
├── ai_engine/
│   ├── pdf_processing.py         # Text extraction, segmentation, and cleaning
│   ├── summarizer.py             # Summarization model logic
│   ├── comparator.py             # Semantic comparison between documents
│   ├── question_answering.py     # Logic for the chatbot (context-based Q&A)
│   └── notifier.py               # Smart detection of sections needing review
│
├── data/
│   ├── sample_rfps/              # Example RFP PDFs
│   ├── sample_vendors/           # Example vendor responses
│   └── results/                  # Generated summaries and comparison outputs
│
├── tests/
│   ├── test_api.py               # API endpoint tests
│   ├── test_ai_engine.py         # Unit tests for AI modules
│   ├── test_frontend/            # Frontend component tests
│   └── test_integration.py       # End-to-end tests
│
├── README.md                     # Project overview and documentation
├── .env.example                  # Example environment variables
├── .gitignore                    # Ignored files and folders
└── docker-compose.yml            # Containerization setup (backend, frontend, database)
