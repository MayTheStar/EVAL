"""
EVAL - RFP Analysis Web Application
Flask-based web interface for the RFP Analysis System (compliance-aware)
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import sys
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from werkzeug.utils import secure_filename

# ============================================================
# ⭐ FIX PYTHON PATH — MAKE BACKEND IMPORTABLE
# ============================================================
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# ============================================================
# ⭐ IMPORT AI MODULES (from web app)
# ============================================================
try:
    from main import RFPAnalysisSystem
    from chatbot import create_chatbot, load_compliance_results
except ImportError as e:
    print(f"Error importing AI modules: {e}")
    sys.exit(1)

# ============================================================
# ⭐ IMPORT BACKEND DATABASE MODULES
# ============================================================
try:
    from backend.core.database import SessionLocal, Base, engine  # engine kept if you need it
    from backend.core.core_models import User, Project, RFPDocument, VendorDocument
except Exception as e:
    print(f"❌ ERROR importing backend DB modules: {e}")
    sys.exit(1)

# NOTE: In production we DO NOT call Base.metadata.create_all() here.
# Schema is managed via Supabase migrations / SQL, not at runtime.

# ============================================================
# ⭐ CREATE FLASK APP
# ============================================================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "eval-secret-key-change-in-production")

# ============================================================
# CONFIGURATION
# ============================================================
UPLOAD_FOLDER = Path("uploads")
OUTPUT_FOLDER = Path("outputs")
COMPLIANCE_DIR = OUTPUT_FOLDER / "compliance"

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE  # basic upload protection

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)
COMPLIANCE_DIR.mkdir(exist_ok=True)

# In-memory cache (non-critical) – DB is the source of truth
user_data = {}

# ============================================================
# ⭐ USER / PROJECT HELPERS
# ============================================================

def get_or_create_user_in_db(user_id: str) -> User:
    db = SessionLocal()
    try:
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
        else:
            user.last_active = datetime.utcnow()
            db.commit()
        return user
    finally:
        db.close()


def get_user_id() -> str:
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    get_or_create_user_in_db(session["user_id"])
    return session["user_id"]


def allowed_file(filename: str) -> bool:
    """Basic extension check. (MIME validation can be added later.)"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_or_create_project(user_id: str):
    """Return the active project for the user (auto-created if missing)."""
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.user_id == user_id).first()
        if project is None:
            project = Project(
                user_id=user_id,
                project_name=f"Project_{user_id[:6]}",
                description="Auto-created default project",
            )
            db.add(project)
            db.commit()
            db.refresh(project)
        return project.project_id
    finally:
        db.close()


def get_user_folder(user_id: str, project_id) -> Path:
    """
    Per-user, per-project upload folder.
    Prevents wiping all uploads when a new RFP is uploaded for a different project.
    """
    folder = UPLOAD_FOLDER / user_id / str(project_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_output_folder(user_id: str, project_id) -> Path:
    """Per-user, per-project output folder."""
    folder = OUTPUT_FOLDER / user_id / str(project_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def hydrate_user_state_from_db(user_id: str):
    """
    For production robustness:
    Rebuild user_data[user_id] from the database (latest RFP + vendors),
    but PRESERVE runtime-only fields like embeddings & chatbot instance.
    """
    project_id = get_or_create_project(user_id)
    db = SessionLocal()
    # 🔐 keep previous runtime state if exists
    prev_state = user_data.get(user_id, {})

    try:
        rfp = (
            db.query(RFPDocument)
              .filter(
                  RFPDocument.user_id == user_id,
                  RFPDocument.project_id == project_id,
              )
              .order_by(RFPDocument.uploaded_at.desc())
              .first()
        )

        vendor_files = []
        files = []

        if rfp:
            vendors = (
                db.query(VendorDocument)
                  .filter(
                      VendorDocument.user_id == user_id,
                      VendorDocument.project_id == project_id,
                      VendorDocument.rfp_id == rfp.rfp_id,
                  )
                  .order_by(VendorDocument.uploaded_at.asc())
                  .all()
            )

            rfp_entry = {
                "filename": rfp.filename,
                "filepath": rfp.filepath,
                "uploaded_at": rfp.uploaded_at.isoformat(),
                "rfp_id": str(rfp.rfp_id),
            }
            files.append(
                {
                    "type": "RFP",
                    "filename": rfp.filename,
                    "uploaded_at": rfp.uploaded_at.isoformat(),
                }
            )

            for v in vendors:
                vendor_files.append(
                    {
                        "vendor_name": v.vendor_name,
                        "filename": v.filename,
                        "filepath": v.filepath,
                        "uploaded_at": v.uploaded_at.isoformat(),
                        "vendor_doc_id": str(v.vendor_doc_id),
                    }
                )
                files.append(
                    {
                        "type": "Vendor",
                        "vendor_name": v.vendor_name,
                        "filename": v.filename,
                        "uploaded_at": v.uploaded_at.isoformat(),
                    }
                )
        else:
            rfp_entry = None

        # 🧠 Build new state but keep runtime flags + objects if present
        new_state = {
            "project_id": project_id,
            "rfp_file": rfp_entry,
            "vendor_files": vendor_files,
            "files": files,
            # Preserve flags if they were already set
            "processed": prev_state.get("processed", False),
            "chatbot_ready": prev_state.get("chatbot_ready", False),
        }

        # Preserve embeddings & chatbot instance if they exist
        if "embeddings" in prev_state:
            new_state["embeddings"] = prev_state["embeddings"]
        if "chatbot_instance" in prev_state:
            new_state["chatbot_instance"] = prev_state["chatbot_instance"]

        user_data[user_id] = new_state

    finally:
        db.close()


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/dashboard")
def dashboard():
    user_id = get_user_id()
    hydrate_user_state_from_db(user_id)

    # Load compliance results
    compliance_results = load_compliance_results(str(COMPLIANCE_DIR))

    # Attach compliance flags to vendor files
    for v in user_data[user_id].get("vendor_files", []):
        name = v["vendor_name"]
        if name in compliance_results:
            v["compliance"] = (
                "✅ Compliant" if compliance_results[name]["compliant"] else "❌ Disqualified"
            )
        else:
            v["compliance"] = "⚙️ Pending"

    return render_template(
        "dashboard.html",
        user_id=user_id,
        vendors=user_data[user_id].get("vendor_files", []),
        compliance=compliance_results,
    )


@app.route("/upload-rfp")
def upload_rfp_page():
    return render_template("upload_rfp.html", user_id=get_user_id())


@app.route("/api/upload-rfp", methods=["POST"])
def upload_rfp():
    """Upload RFP file."""
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
        # Per-project folders – old runs for *this* project only
        user_folder = get_user_folder(user_id, project_id)
        if user_folder.exists():
            shutil.rmtree(user_folder)
        user_folder.mkdir(parents=True, exist_ok=True)

        output_folder = get_output_folder(user_id, project_id)
        if output_folder.exists():
            shutil.rmtree(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        filename = secure_filename(file.filename)
        filepath = user_folder / f"rfp_{filename}"
        file.save(str(filepath))

        # Save in DB
        db = SessionLocal()
        try:
            new_rfp = RFPDocument(
                user_id=user_id,
                project_id=project_id,
                filename=filename,
                filepath=str(filepath),
                file_size=os.path.getsize(filepath),
                uploaded_at=datetime.utcnow(),
            )
            db.add(new_rfp)
            db.commit()
            db.refresh(new_rfp)
            rfp_id = str(new_rfp.rfp_id)
        finally:
            db.close()

        # Update cache (optional, DB is main source)
        user_data[user_id] = {
            "project_id": project_id,
            "rfp_file": {
                "filename": filename,
                "filepath": str(filepath),
                "uploaded_at": datetime.utcnow().isoformat(),
                "rfp_id": rfp_id,
            },
            "vendor_files": [],
            "processed": False,
            "chatbot_ready": False,
            "files": [
                {
                    "type": "RFP",
                    "filename": filename,
                    "uploaded_at": datetime.utcnow().isoformat(),
                }
            ],
        }

        return jsonify(
            {"success": True, "message": "RFP uploaded successfully!", "filename": filename}
        )

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"}), 500


@app.route("/upload-vendor")
def upload_vendor_page():
    return render_template("upload_vendor.html", user_id=get_user_id())


@app.route("/api/upload-vendor", methods=["POST"])
def upload_vendor():
    """Upload vendor response."""
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
        user_folder = get_user_folder(user_id, project_id)
        filename = f"vendor_{vendor_name}.pdf"
        filepath = user_folder / filename
        file.save(str(filepath))

        db = SessionLocal()
        try:
            # Ensure there is an RFP for this user/project (even if session cache was lost)
            db_rfp = (
                db.query(RFPDocument)
                    .filter(
                        RFPDocument.user_id == user_id,
                        RFPDocument.project_id == project_id,
                    )
                    .order_by(RFPDocument.uploaded_at.desc())
                    .first()
            )
            if not db_rfp:
                return jsonify(
                    {
                        "success": False,
                        "message": "You must upload an RFP before uploading vendors.",
                    }
                ), 400

            rfp_id = str(db_rfp.rfp_id)

            new_vendor = VendorDocument(
                user_id=user_id,
                project_id=project_id,
                vendor_name=vendor_name,
                rfp_id=rfp_id,
                filename=filename,
                filepath=str(filepath),
                file_size=os.path.getsize(filepath),
                uploaded_at=datetime.utcnow(),
            )
            db.add(new_vendor)
            db.commit()
            db.refresh(new_vendor)
            vendor_doc_id = str(new_vendor.vendor_doc_id)
        finally:
            db.close()

        # Update cache
        if user_id not in user_data:
            hydrate_user_state_from_db(user_id)

        user_data[user_id]["vendor_files"].append(
            {
                "vendor_name": vendor_name,
                "filename": filename,
                "filepath": str(filepath),
                "uploaded_at": datetime.utcnow().isoformat(),
                "vendor_doc_id": vendor_doc_id,
            }
        )
        user_data[user_id]["files"].append(
            {
                "type": "Vendor",
                "vendor_name": vendor_name,
                "filename": filename,
                "uploaded_at": datetime.utcnow().isoformat(),
            }
        )

        return jsonify(
            {
                "success": True,
                "message": f"Vendor response from {vendor_name} uploaded!",
                "filename": filename,
                "vendor_name": vendor_name,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"}), 500


# ============================================================
# PROCESS DOCUMENTS PIPELINE
# ============================================================

@app.route("/api/process-documents", methods=["POST"])
def process_documents():
    user_id = get_user_id()
    project_id = get_or_create_project(user_id)

    db = SessionLocal()
    try:
        rfp = (
            db.query(RFPDocument)
                .filter(
                    RFPDocument.user_id == user_id,
                    RFPDocument.project_id == project_id,
                )
                .order_by(RFPDocument.uploaded_at.desc())
                .first()
        )
        if not rfp:
            return jsonify({"success": False, "message": "No RFP uploaded"}), 400

        vendor_docs = (
            db.query(VendorDocument)
                .filter(
                    VendorDocument.user_id == user_id,
                    VendorDocument.project_id == project_id,
                    VendorDocument.rfp_id == rfp.rfp_id,
                )
                .order_by(VendorDocument.uploaded_at.asc())
                .all()
        )
    finally:
        db.close()

    try:
        rfp_file = rfp.filepath
        vendor_files = [(v.filepath, v.vendor_name) for v in vendor_docs]
        output_dir = get_output_folder(user_id, project_id)

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
        for file_path in (output_dir / "analysis").glob("*_analysis.json"):
            name = file_path.stem.replace("_analysis", "")
            if name.lower() != "rfp_chunk":
                vendor_analysis_files[name] = str(file_path)

        compliance_results = checker.evaluate_all_vendors(
            rfp_analysis_file,
            vendor_analysis_files,
            output_dir=str(output_dir / "compliance"),
        )

        non_compliant = [
            name for name, data in compliance_results.items() if not data.get("compliant", False)
        ]

        # Update cache flags from DB again
        # hydrate_user_state_from_db(user_id)
        for v in user_data[user_id]["vendor_files"]:
            if v["vendor_name"] in non_compliant:
                v["compliance"] = "❌ Disqualified"
            else:
                v["compliance"] = "✅ Compliant"

        # Prepare embeddings – support both old/new keys
        emb = results.get("embeddings", {})
        faiss_index = emb.get("faiss") or emb.get("faiss_index_path")
        metadata = emb.get("metadata") or emb.get("metadata_path")

        user_data[user_id]["embeddings"] = {
            "faiss": faiss_index,
            "metadata": metadata,
        }
        user_data[user_id]["processed"] = True
        user_data[user_id]["chatbot_ready"] = True

        return jsonify(
            {
                "success": True,
                "message": "Documents processed successfully!",
                "non_compliant_vendors": non_compliant,
                "compliance_summary": compliance_results,
                "chatbot_ready": True,
                "faiss_path": faiss_index,
                "metadata_path": metadata,
            }
        )


    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print("\n🔥 FULL PIPELINE ERROR 🔥")
        print(error_details)
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Processing error: {e}",
                    "details": error_details,
                }
            ),
            500,
        )


# ============================================================
# CHATBOT
# ============================================================

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
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"success": False, "message": "No query provided"}), 400

    try:
        # 👇 Make sure we still have embeddings (they might be missing if state was reset)
        embeddings = user_data[user_id].get("embeddings")
        if not embeddings:
            return jsonify({
                "success": False,
                "message": "Embeddings not found in session. Please re-process the documents from the dashboard."
            }), 400

        # 👇 (Re)create chatbot if missing OR None
        if not user_data[user_id].get("chatbot_instance"):
            user_data[user_id]["chatbot_instance"] = create_chatbot(
                embeddings["faiss"],
                embeddings["metadata"],
                compliance_dir=str(COMPLIANCE_DIR),
            )

        chatbot = user_data[user_id]["chatbot_instance"]
        answer, chunks = chatbot.query(query, stream=False, top_k=5)

        sources = [
            {
                "label": c["label"],
                "distance": c["distance"],
                "preview": c["chunk"][:200] + "..." if len(c["chunk"]) > 200 else c["chunk"],
            }
            for c in chunks
        ]

        return jsonify({"success": True, "answer": answer, "sources": sources})

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"}), 500

# ============================================================
# FILE PAGES
# ============================================================

@app.route("/files")
def files_page():
    user_id = get_user_id()
    hydrate_user_state_from_db(user_id)
    files_list = user_data.get(user_id, {}).get("files", [])
    return render_template("files.html", user_id=user_id, files=files_list)


@app.route("/api/get-status")
def get_status():
    user_id = get_user_id()
    hydrate_user_state_from_db(user_id)
    data = user_data.get(user_id, {})

    return jsonify(
        {
            "rfp_uploaded": data.get("rfp_file") is not None,
            "vendors_count": len(data.get("vendor_files", [])),
            "processed": data.get("processed", False),
            "chatbot_ready": data.get("chatbot_ready", False),
            "files_count": len(data.get("files", [])),
        }
    )



@app.route("/api/delete-file", methods=["POST"])
def delete_file():
    user_id = get_user_id()
    data = request.get_json()
    filename = data.get("filename")

    if user_id not in user_data:
        return jsonify({"success": False, "message": "No files found"}), 400

    try:
        # Remove from in-memory view
        user_data[user_id]["files"] = [
            f for f in user_data[user_id]["files"] if f["filename"] != filename
        ]
        user_data[user_id]["vendor_files"] = [
            v for v in user_data[user_id]["vendor_files"] if v["filename"] != filename
        ]
        if user_data[user_id].get("rfp_file", {}).get("filename") == filename:
            user_data[user_id]["rfp_file"] = None

        # Remove from database
        db = SessionLocal()
        try:
            rfp = (
                db.query(RFPDocument)
                    .filter(RFPDocument.user_id == user_id, RFPDocument.filename == filename)
                    .first()
            )
            if rfp:
                db.delete(rfp)

            vendor = (
                db.query(VendorDocument)
                    .filter(VendorDocument.user_id == user_id, VendorDocument.filename == filename)
                    .first()
            )
            if vendor:
                db.delete(vendor)

            db.commit()
        finally:
            db.close()

        # Remove from filesystem (both uploads and outputs)
        for root_folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
            for root, _, files in os.walk(root_folder):
                if filename in files:
                    try:
                        os.remove(Path(root) / filename)
                    except FileNotFoundError:
                        pass

        return jsonify({"success": True, "message": "File deleted successfully"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"}), 500


# ============================================================
# RUN APP
# ============================================================

if __name__ == "__main__":
    # In production you’ll normally run via Gunicorn/uvicorn behind a reverse proxy.
    app.run(debug=False, host="0.0.0.0", port=8000)
