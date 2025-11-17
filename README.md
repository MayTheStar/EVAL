# 🎯 RFP Evaluation System

An intelligent AI-powered system for automated Request for Proposal (RFP) evaluation and vendor matching. This system streamlines the procurement process by automatically analyzing RFPs, extracting requirements, evaluating vendor capabilities, and generating comprehensive compliance reports.

## 📋 Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Technology Stack](#technology-stack)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

### Core Capabilities

- **📄 Intelligent Document Processing**
  - Automatic extraction of requirements from RFP documents
  - Support for multiple document formats (PDF, DOCX, TXT)
  - Advanced natural language processing for requirement identification

- **🔍 Vendor Capability Analysis**
  - Automated extraction of vendor capabilities from proposals
  - Semantic matching between RFP requirements and vendor offerings
  - Comprehensive vendor profile management

- **📊 Automated Compliance Checking**
  - Line-by-line requirement matching
  - Compliance scoring with detailed justifications
  - Gap analysis and missing requirement identification

- **💬 Interactive AI Chatbot**
  - Natural language queries about RFPs and vendors
  - Context-aware responses based on uploaded documents
  - Real-time assistance during evaluation process

- **📈 Comprehensive Reporting**
  - Detailed evaluation reports with scores and recommendations
  - Visual dashboards for vendor comparison
  - Export capabilities for stakeholder presentations

## 🏗️ System Architecture

```
┌─────────────────┐
│   Web Interface │
│   (Flask App)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   AI Engine     │
│  - Parser       │
│  - Extractor    │
│  - Embedder     │
│  - Scorer       │
│  - Chatbot      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Backend Core  │
│  - Database     │
│  - Models       │
│  - Config       │
└─────────────────┘
```

## 📁 Project Structure

```
evaluation/
├── ai_engine/              # AI processing modules
│   ├── main.py            # Main AI orchestration
│   ├── parser.py          # Document parsing
│   ├── extractor.py       # Requirement extraction
│   ├── embeder.py         # Vector embeddings
│   ├── Scorer.py          # Compliance scoring
│   ├── chatbot.py         # AI chatbot interface
│   ├── compliance_checker.py
│   ├── vendor_parser.py
│   ├── vendor_capability_extractor.py
│   └── util.py            # Utility functions
│
├── backend/               # Backend services
│   ├── core_main.py      # Main backend entry point
│   └── core/             # Core backend modules
│       ├── core_config.py
│       ├── core_models.py
│       └── database.py
│
├── web_app/              # Web application
│   ├── app.py           # Flask application
│   ├── templates/       # HTML templates
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   ├── upload_rfp.html
│   │   ├── upload_vendor.html
│   │   ├── files_uploaded.html
│   │   ├── chatbot.html
│   │   └── profile.html
│   └── static/          # CSS, JS, images
│       ├── style.css
│       └── main.js
│
├── uploads/             # Uploaded documents storage
├── outputs/             # Generated reports and results
├── docker/              # Docker configuration
├── .gitignore
└── README.md
```

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)
- API keys for AI services (OpenAI/Anthropic)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/rfp-evaluation-system.git
cd rfp-evaluation-system
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the root directory:

```env
# API Keys
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Database Configuration
DATABASE_URL=sqlite:///evaluation.db

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key_here
FLASK_ENV=development

# Upload Configuration
MAX_UPLOAD_SIZE=16777216  # 16MB
ALLOWED_EXTENSIONS=pdf,docx,txt
```

### Step 5: Initialize Database

```bash
python backend/core_main.py
```

## 💻 Usage

### Starting the Application

#### Using Python

```bash
# Start the web application
cd web_app
python app.py
```

The application will be available at `http://localhost:5000`

#### Using Docker

```bash
# Build the Docker image
docker build -t rfp-evaluation .

# Run the container
docker run -p 5000:5000 rfp-evaluation
```

### Workflow

1. **Register/Login**: Create an account or log in to the system
2. **Upload RFP**: Navigate to the RFP upload page and submit your RFP document
3. **Upload Vendor Proposals**: Upload vendor response documents for evaluation
4. **View Results**: Check the dashboard for automated evaluation results
5. **Use Chatbot**: Ask questions about requirements and vendor capabilities
6. **Download Reports**: Export detailed evaluation reports

## 🛠️ Technology Stack

### Backend
- **Python 3.8+**: Core programming language
- **Flask**: Web framework
- **SQLAlchemy**: Database ORM
- **SQLite**: Database (development)

### AI/ML
- **OpenAI GPT**: Natural language processing
- **LangChain**: LLM application framework
- **ChromaDB**: Vector database for embeddings
- **Sentence Transformers**: Semantic similarity

### Frontend
- **HTML5/CSS3**: Structure and styling
- **JavaScript**: Interactive functionality
- **Bootstrap**: Responsive design

### Document Processing
- **PyPDF2**: PDF parsing
- **python-docx**: Word document processing
- **BeautifulSoup4**: HTML parsing

## ⚙️ Configuration

### AI Engine Configuration

Edit `ai_engine/config.py` to customize:

- Model selection (GPT-4, Claude, etc.)
- Embedding dimensions
- Scoring thresholds
- Processing parameters

### Backend Configuration

Edit `backend/core/core_config.py` for:

- Database settings
- File upload limits
- Session management
- Security parameters

## 📊 Features in Detail

### RFP Parsing
The system automatically extracts:
- Technical requirements
- Functional specifications
- Compliance criteria
- Evaluation criteria
- Timeline and milestones

### Vendor Evaluation
Automated assessment includes:
- Requirement coverage analysis
- Capability matching scores
- Compliance percentage
- Gap identification
- Risk assessment

### AI Chatbot
Interactive features:
- Query RFP requirements
- Ask about vendor capabilities
- Request clarifications
- Generate custom reports
- Compare vendors

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide for Python code
- Write unit tests for new features
- Update documentation for API changes
- Ensure all tests pass before submitting PR

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- Your Name - Initial work

## 🙏 Acknowledgments

- OpenAI for GPT models
- Anthropic for Claude AI
- LangChain community
- All contributors to this project

## 📞 Support

For support, please:
- Open an issue on GitHub
- Contact: your.email@example.com
- Documentation: [Wiki](https://github.com/yourusername/rfp-evaluation-system/wiki)

## 🗺️ Roadmap

- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] Integration with procurement systems
- [ ] Mobile application
- [ ] Real-time collaboration features
- [ ] Custom scoring models
- [ ] Export to multiple formats (Excel, PowerPoint)

---

**Note**: This system is designed to assist in the RFP evaluation process. Final decisions should always be made by qualified procurement professionals.

Made with ❤️ for better procurement processes