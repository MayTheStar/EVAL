"""
EVAL - RFP Analysis Web Application
Flask-based web interface for the RFP Analysis System (compliance-aware)
Updated to use new UI templates
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
from pathlib import Path
from werkzeug.utils import secure_filename
import json
import uuid
from datetime import datetime
import shutil
import sys

# --------------------------------------------
# Python Path Setup (Fixing Imports)
# --------------------------------------------
import sys
import os
from pathlib import Path

# Get the absolute path to the "web app" directory
CURRENT_DIR = Path(__file__).resolve().parent

# Get the project root (one level above "web app")
ROOT_DIR = CURRENT_DIR.parent

# Path to ai_engine folder
AI_ENGINE_DIR = ROOT_DIR / "ai_engine"

# Path to backend/core
BACKEND_CORE_DIR = ROOT_DIR / "backend" / "core"

# Add paths to Python import path
sys.path.insert(0, str(ROOT_DIR))          # main project
sys.path.insert(0, str(AI_ENGINE_DIR))     # ai_engine
sys.path.insert(0, str(BACKEND_CORE_DIR))  # backend/core

print("---- PYTHON PATH CONFIG ----")
print("ROOT_DIR:", ROOT_DIR)
print("AI_ENGINE_DIR:", AI_ENGINE_DIR)
print("BACKEND_CORE_DIR:", BACKEND_CORE_DIR)
print("--------------------------------")


# ---------------- Import database and models ----------------
from backend.core.database import SessionLocal, Base, engine
from backend.core.core_models import User, Project, RFPDocument, VendorDocument, VendorEvaluation


# ---------------- Import AI modules ----------------
try:
    from ai_engine.main import RFPAnalysisSystem
    from chatbot import create_chatbot, load_compliance_results
except ImportError as e:
    print(f"[IMPORT ERROR] {e}")
    sys.exit(1)

# ---------------- App setup ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "eval-secret-key-change-in-production")

# ---------------- Config ----------------
UPLOAD_FOLDER = Path("uploads")
OUTPUT_FOLDER = Path("outputs")
COMPLIANCE_DIR = OUTPUT_FOLDER / "compliance"
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)
COMPLIANCE_DIR.mkdir(exist_ok=True)

user_data = {}  # In-memory session store

# ---------------- Helper functions ----------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_or_create_user_in_db(user_id):
    db = SessionLocal()
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        user = User(
            user_id=user_id,
            session_id=user_id,
            email=None,
            last_active=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user

def get_user_id():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    get_or_create_user_in_db(session["user_id"])
    return session["user_id"]

def get_or_create_project(user_id):
    db = SessionLocal()
    project = db.query(Project).filter(Project.user_id == user_id).first()
    if project is None:
        project = Project(
            user_id=user_id,
            project_name=f"Project_{user_id[:6]}",
            description="Auto-created default project"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
    db.close()
    return project.project_id

def get_user_folder(user_id):
    folder = UPLOAD_FOLDER / user_id
    folder.mkdir(exist_ok=True)
    return folder

def get_output_folder(user_id):
    folder = OUTPUT_FOLDER / user_id
    folder.mkdir(exist_ok=True)
    return folder

# ---------------- Routes ----------------
@app.route("/")
def landing():
    return render_template("index.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.session_id == username).first()
        if user:
            session["user_id"] = str(user.user_id)
            session["username"] = username
            return jsonify({"success": True, "redirect": url_for("dashboard")})
        return jsonify({"success": False, "message": "Invalid username or password"}), 401
    finally:
        db.close()

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    email = data.get("email", "").strip()
    
    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400
    
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.session_id == username).first()
        if existing:
            return jsonify({"success": False, "message": "Username already exists"}), 400
        
        new_user = User(
            user_id=str(uuid.uuid4()),
            session_id=username,
            email=email if email else None,
            last_active=datetime.utcnow(),
            is_active=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        session["user_id"] = str(new_user.user_id)
        session["username"] = username
        
        return jsonify({"success": True, "redirect": url_for("dashboard")})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Registration failed: {str(e)}"}), 500
    finally:
        db.close()

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))

@app.route("/dashboard")
def dashboard():
    user_id = get_user_id()
    username = session.get("username", "User")
    project_id = get_or_create_project(user_id)

    if user_id not in user_data:
        user_data[user_id] = {
            "project_id": project_id,
            "rfp_file": None,
            "vendor_files": [],
            "processed": False,
            "chatbot_ready": False,
            "files": [],
        }

    compliance_results = load_compliance_results(str(COMPLIANCE_DIR))
    for v in user_data[user_id].get("vendor_files", []):
        name = v["vendor_name"]
        if name in compliance_results:
            v["compliance"] = "âœ” Compliant" if compliance_results[name]["compliant"] else "âŒ Disqualified"
        else:
            v["compliance"] = "â³ Pending"

    return render_template(
        "dashboard.html",
        user_id=user_id,
        username=username,
        vendors=user_data[user_id].get("vendor_files", []),
        compliance=compliance_results,
    )

@app.route("/upload-rfp")
def upload_rfp_page():
    return render_template("upload_rfp.html", user_id=get_user_id())

@app.route("/upload-vendor")
def upload_vendor_page():
    user_id = get_user_id()
    username = session.get("username", "User")
    return render_template("upload_vendor.html", user_id=user_id, username=username)

@app.route("/profile")
def profile_page():
    user_id = get_user_id()
    username = session.get("username", "User")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        return render_template(
            "profile.html",
            user_id=user_id,
            username=username,
            email=user.email if user else None,
            created_at=user.created_at.strftime("%Y-%m-%d") if user and user.created_at else "N/A"
        )
    finally:
        db.close()

# ---------------- Upload RFP ----------------
@app.route("/api/upload-rfp", methods=["POST"])
def upload_rfp():
    user_id = get_user_id()
    project_id = get_or_create_project(user_id)

    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Invalid file type"}), 400

    try:
        user_folder = get_user_folder(user_id)
        if user_folder.exists():
            shutil.rmtree(user_folder)
        user_folder.mkdir(parents=True, exist_ok=True)

        output_folder = get_output_folder(user_id)
        if output_folder.exists():
            shutil.rmtree(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        filename = secure_filename(file.filename)
        filepath = user_folder / f"rfp_{filename}"
        file.save(str(filepath))

        db = SessionLocal()
        new_rfp = RFPDocument(
            user_id=user_id,
            project_id=project_id,
            filename=filename,
            filepath=str(filepath),
            file_size=os.path.getsize(filepath),
            uploaded_at=datetime.utcnow()
        )
        db.add(new_rfp)
        db.commit()
        db.refresh(new_rfp)
        rfp_id = str(new_rfp.rfp_id)
        db.close()

        user_data[user_id] = {
            "project_id": project_id,
            "rfp_file": {
                "filename": filename,
                "filepath": str(filepath),
                "uploaded_at": datetime.now().isoformat(),
                "rfp_id": rfp_id
            },
            "vendor_files": [],
            "processed": False,
            "chatbot_ready": False,
            "files": [{"type": "RFP", "filename": filename, "uploaded_at": datetime.now().isoformat()}],
        }

        return jsonify({"success": True, "message": "RFP uploaded successfully!", "filename": filename})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"}), 500

# ---------------- Upload Vendor ----------------
@app.route("/api/upload-vendor", methods=["POST"])
def upload_vendor():
    user_id = get_user_id()
    project_id = get_or_create_project(user_id)

    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file provided"}), 400

    file = request.files["file"]
    vendor_name = request.form.get("vendor_name", "UnknownVendor").strip().replace(" ", "_")
    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Invalid file type"}), 400

    try:
        user_folder = get_user_folder(user_id)
        filename = f"vendor_{vendor_name}.pdf"
        filepath = user_folder / filename
        file.save(str(filepath))

        db = SessionLocal()
        new_vendor = VendorDocument(
            user_id=user_id,
            project_id=project_id,
            vendor_name=vendor_name,
            rfp_id=user_data.get(user_id, {}).get("rfp_file", {}).get("rfp_id"),
            filename=filename,
            filepath=str(filepath),
            file_size=os.path.getsize(filepath),
            uploaded_at=datetime.utcnow()
        )
        db.add(new_vendor)
        db.commit()
        db.refresh(new_vendor)
        vendor_doc_id = str(new_vendor.vendor_doc_id)
        db.close()

        user_data[user_id]["vendor_files"].append({
            "vendor_name": vendor_name,
            "filename": filename,
            "filepath": str(filepath),
            "uploaded_at": datetime.now().isoformat(),
            "vendor_doc_id": vendor_doc_id
        })
        user_data[user_id]["files"].append({
            "type": "Vendor",
            "vendor_name": vendor_name,
            "filename": filename,
            "uploaded_at": datetime.now().isoformat()
        })

        return jsonify({"success": True, "message": f"Vendor response from {vendor_name} uploaded!", "filename": filename})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"}), 500

# ---------------- Process Documents ----------------
@app.route("/api/process-documents", methods=["POST"])
def process_documents():
    user_id = get_user_id()
    if user_id not in user_data or not user_data[user_id].get("rfp_file"):
        return jsonify({"success": False, "message": "No RFP uploaded"}), 400

    try:
        rfp_file = user_data[user_id]["rfp_file"]["filepath"]
        vendor_files = [(v["filepath"], v["vendor_name"]) for v in user_data[user_id].get("vendor_files", [])]
        output_dir = get_output_folder(user_id)

        system = RFPAnalysisSystem(output_dir=str(output_dir))
        results = system.run_full_pipeline(
            rfp_file=rfp_file,
            vendor_files=vendor_files,
            skip_extraction=False,
            run_chatbot=False,
        )

        from compliance_checker import ComplianceChecker
        checker = ComplianceChecker()
        rfp_analysis_file = str(output_dir / "analysis" / "rfp_chunk_analysis.json")

        vendor_analysis_files = {}
        for file in (output_dir / "analysis").glob("*_analysis.json"):
            name = file.stem.replace("_analysis", "")
            if name.lower() != "rfp_chunk":
                vendor_analysis_files[name] = str(file)

        compliance_results = checker.evaluate_all_vendors(rfp_analysis_file, vendor_analysis_files, output_dir=str(output_dir / "compliance"))

        non_compliant = [name for name, data in compliance_results.items() if not data.get("compliant", False)]
        for v in user_data[user_id]["vendor_files"]:
            if v["vendor_name"] in non_compliant:
                v["compliance"] = "âŒ Disqualified"
            else:
                v["compliance"] = "âœ” Compliant"

        # Store embeddings
        user_data[user_id]["embeddings"] = {
            "faiss": results["embeddings"]["faiss"],
            "metadata": results["embeddings"]["metadata"]
        }
        user_data[user_id]["processed"] = True
        user_data[user_id]["chatbot_ready"] = True

        return jsonify({
            "success": True,
            "message": "Documents processed successfully!",
            "non_compliant_vendors": non_compliant,
            "compliance_summary": compliance_results,
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Processing error: {e}"}), 500

# ---------------- Chatbot ----------------
@app.route("/chatbot")
def chatbot_page():
    user_id = get_user_id()
    if not user_data.get(user_id, {}).get("chatbot_ready"):
        return redirect(url_for("dashboard"))
    return render_template("chatbot.html", user_id=user_id)

@app.route("/api/chat", methods=["POST"])
def chat():
    user_id = get_user_id()
    if not user_data.get(user_id, {}).get("chatbot_ready"):
        return jsonify({"success": False, "message": "Chatbot not ready"}), 400

    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"success": False, "message": "No query provided"}), 400

    try:
        embeddings = user_data[user_id]["embeddings"]
        chatbot = create_chatbot(
            embeddings["faiss"],
            embeddings["metadata"],
            compliance_dir=str(COMPLIANCE_DIR)
        )

        answer, chunks = chatbot.query(query, stream=False, top_k=5)
        sources = [{"label": c["label"], "distance": c["distance"], "preview": c["chunk"][:200]+"..." if len(c["chunk"])>200 else c["chunk"]} for c in chunks]
        return jsonify({"success": True, "answer": answer, "sources": sources})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"}), 500

# ---------------- Files ----------------
@app.route("/files")
def files_page():
    user_id = get_user_id()
    files_list = user_data.get(user_id, {}).get("files", [])
    return render_template("files_uploaded.html", user_id=user_id, files=files_list)

@app.route("/api/get-status")
def get_status():
    user_id = get_user_id()
    data = user_data.get(user_id, {})
    return jsonify({
        "rfp_uploaded": data.get("rfp_file") is not None,
        "vendors_count": len(data.get("vendor_files", [])),
        "processed": data.get("processed", False),
        "chatbot_ready": data.get("chatbot_ready", False),
        "files_count": len(data.get("files", []))
    })


@app.route("/api/delete-file", methods=["POST"])
def delete_file():
    user_id = get_user_id()
    data = request.get_json()
    filename = data.get("filename")

    if user_id not in user_data:
        return jsonify({"success": False, "message": "No files found"}), 400

    try:
        user_data[user_id]["files"] = [f for f in user_data[user_id]["files"] if f["filename"] != filename]
        return jsonify({"success": True, "message": "File deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"}), 500
# ============================================
# UPDATED: /api/get-scores endpoint
# Replace the existing get-scores endpoint in app.py with this
# ============================================

@app.route("/api/get-scores")
def get_scores():
    """Get vendor scoring results from the output folder."""
    user_id = get_user_id()
    output_folder = get_output_folder(user_id)
    
    # Try multiple possible locations for scoring results
    possible_paths = [
        output_folder / "scoring_results" / "scoring_summary.json",
        output_folder / "final_scores.json",
        output_folder / "scoring_summary.json"
    ]
    
    print(f"[DEBUG] Looking for scores in: {output_folder}")
    
    try:
        for scores_file in possible_paths:
            print(f"[DEBUG] Checking: {scores_file}")
            if scores_file.exists():
                print(f"[DEBUG] Found scores at: {scores_file}")
                with open(scores_file, 'r') as f:
                    scores = json.load(f)
                print(f"[DEBUG] Loaded scores with {len(scores.get('vendors', {}))} vendors")
                return jsonify({"success": True, "scores": scores})
        
        # No scores file found - list what files exist
        print(f"[DEBUG] No scores file found. Checking directory structure:")
        if output_folder.exists():
            print(f"[DEBUG] Output folder contents: {list(output_folder.iterdir())}")
            scoring_dir = output_folder / "scoring_results"
            if scoring_dir.exists():
                print(f"[DEBUG] Scoring results folder contents: {list(scoring_dir.iterdir())}")
        
        return jsonify({"success": False, "message": "No scores available yet"})
    except Exception as e:
        print(f"[ERROR] Error loading scores: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Error loading scores: {str(e)}"})


# ============================================
# ALTERNATIVE: Add endpoint to check files
# Add this endpoint to help debug
# ============================================

@app.route("/api/debug-files")
def debug_files():
    """Debug endpoint to check what files exist."""
    user_id = get_user_id()
    output_folder = get_output_folder(user_id)
    
    files_info = {
        "output_folder": str(output_folder),
        "exists": output_folder.exists(),
        "contents": []
    }
    
    if output_folder.exists():
        for item in output_folder.rglob("*"):
            if item.is_file():
                files_info["contents"].append({
                    "path": str(item.relative_to(output_folder)),
                    "size": item.stat().st_size,
                    "name": item.name
                })
    
    return jsonify(files_info)
# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)