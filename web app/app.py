"""
EVAL - RFP Analysis Web Application
Flask-based web interface for the RFP Analysis System (compliance-aware)
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
import os
from pathlib import Path
from werkzeug.utils import secure_filename
import json
import uuid
from datetime import datetime
import sys
import shutil

# Add current directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules
try:
    from main import RFPAnalysisSystem
    from chatbot import create_chatbot, load_compliance_results
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "eval-secret-key-change-in-production")

# ---------------- Configuration ----------------
UPLOAD_FOLDER = Path("uploads")
OUTPUT_FOLDER = Path("outputs")
COMPLIANCE_DIR = OUTPUT_FOLDER / "compliance"
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)
COMPLIANCE_DIR.mkdir(exist_ok=True)

user_data = {}  # In-memory session store


# ---------------- Utility helpers ----------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_user_id():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    return session["user_id"]


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
    return render_template("landing.html")


@app.route("/dashboard")
def dashboard():
    """Main dashboard with compliance badges."""
    user_id = get_user_id()
    if user_id not in user_data:
        user_data[user_id] = {
            "rfp_file": None,
            "vendor_files": [],
            "processed": False,
            "chatbot_ready": False,
            "files": [],
        }

    # Load latest compliance results if any
    compliance_results = load_compliance_results(str(COMPLIANCE_DIR))

    # Attach compliance status to vendor list
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


@app.route('/api/upload-rfp', methods=['POST'])
def upload_rfp():
    """Handle RFP file upload."""
    user_id = get_user_id()
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file type. Please upload PDF, DOC, or DOCX'}), 400
    
    try:
        # 1️⃣ Define the user upload folder
        user_folder = get_user_folder(user_id)

        # 2️⃣ Clean old uploads (from previous runs)
        if user_folder.exists():
            shutil.rmtree(user_folder)
        user_folder.mkdir(parents=True, exist_ok=True)

        # 3️⃣ Clean old outputs (generated analyses, chunks, embeddings)
        output_folder = Path("outputs") / user_id
        if output_folder.exists():
            shutil.rmtree(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        # 4️⃣ Save new RFP file
        filename = secure_filename(file.filename)
        filepath = user_folder / f"rfp_{filename}"
        file.save(str(filepath))

        # 5️⃣ Initialize session data
        user_data[user_id] = {
            'rfp_file': {
                'filename': filename,
                'filepath': str(filepath),
                'uploaded_at': datetime.now().isoformat()
            },
            'vendor_files': [],
            'processed': False,
            'chatbot_ready': False,
            'files': [
                {'type': 'RFP', 'filename': filename, 'uploaded_at': datetime.now().isoformat()}
            ]
        }

        return jsonify({
            'success': True,
            'message': 'RFP uploaded successfully!',
            'filename': filename
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error uploading file: {str(e)}'}), 500



@app.route('/upload-vendor')
def upload_vendor_page():
    """Vendor upload page."""
    user_id = get_user_id()
    return render_template('upload_vendor.html', user_id=user_id)


@app.route('/api/upload-vendor', methods=['POST'])
def upload_vendor():
    """Handle vendor file upload."""
    user_id = get_user_id()
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
    
    file = request.files['file']
    vendor_name = request.form.get('vendor_name', 'UnknownVendor').strip().replace(" ", "_")
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file type. Please upload PDF, DOC, or DOCX'}), 400
    
    try:
        filename = f"vendor_{vendor_name}.pdf"
        user_folder = get_user_folder(user_id)
        filepath = user_folder / filename
        file.save(str(filepath))
        
        # Initialize user data if not set
        if user_id not in user_data:
            user_data[user_id] = {
                'rfp_file': None,
                'vendor_files': [],
                'processed': False,
                'chatbot_ready': False,
                'files': []
            }
        
        user_data[user_id]['vendor_files'].append({
            'vendor_name': vendor_name,
            'filename': filename,
            'filepath': str(filepath),
            'uploaded_at': datetime.now().isoformat()
        })
        
        user_data[user_id]['files'].append({
            'type': 'Vendor',
            'vendor_name': vendor_name,
            'filename': filename,
            'uploaded_at': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': f'Vendor response from {vendor_name} uploaded successfully!',
            'filename': filename,
            'vendor_name': vendor_name
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error uploading file: {str(e)}'}), 500
    

@app.route("/api/process-documents", methods=["POST"])
def process_documents():
    """Run full analysis pipeline and build compliance files."""
    user_id = get_user_id()
    if user_id not in user_data:
        return jsonify({"success": False, "message": "No files uploaded"}), 400

    user_info = user_data[user_id]
    if not user_info.get("rfp_file"):
        return jsonify({"success": False, "message": "No RFP uploaded"}), 400

    try:
        rfp_file = user_info["rfp_file"]["filepath"]
        vendor_files = [(v["filepath"], v["vendor_name"]) for v in user_info.get("vendor_files", [])]
        output_dir = get_output_folder(user_id)

        # Run the full pipeline
        system = RFPAnalysisSystem(output_dir=str(output_dir))
        results = system.run_full_pipeline(
            rfp_file=rfp_file,
            vendor_files=vendor_files,
            skip_extraction=False,
            run_chatbot=False,
        )

        # Update user info
        user_info["embeddings"] = {
            "faiss": results["embeddings"]["faiss"],
            "metadata": results["embeddings"]["metadata"],
        }
        user_info["processed"] = True
        user_info["chatbot_ready"] = True

        # Load compliance or comparison results
        compliance_results = load_compliance_results(str(COMPLIANCE_DIR))

        # 🔍 NEW: Check mandatory requirement failures
        mandatory_failures = []
        rfp_requirements_path = Path(output_dir) / "rfp_requirements.json"
        vendor_capabilities_path = Path(output_dir) / "vendor_capabilities.json"

        if rfp_requirements_path.exists() and vendor_capabilities_path.exists():
            import json
            rfp_data = json.loads(rfp_requirements_path.read_text())
            vendor_data = json.loads(vendor_capabilities_path.read_text())

            for vendor_name, capabilities in vendor_data.items():
                for req in rfp_data:
                    if req.get("mandatory", False):
                        matched = any(
                            req["text"].lower() in cap["text"].lower()
                            for cap in capabilities
                        )
                        if not matched:
                            mandatory_failures.append({
                                "vendor": vendor_name,
                                "requirement": req["text"]
                            })

        return jsonify({
            "success": True,
            "message": "Documents processed successfully! Chatbot ready.",
            "compliance_summary": compliance_results,
            "mandatory_failures": mandatory_failures,
            "chunks_count": {
                "rfp": len(json.loads((Path(output_dir) / "rfp_requirements.json").read_text()))
                if (Path(output_dir) / "rfp_requirements.json").exists() else 0,
                "vendors": sum(len(v) for v in json.loads((Path(output_dir) / "vendor_capabilities.json").read_text()).values())
                if (Path(output_dir) / "vendor_capabilities.json").exists() else 0
            }
        })


    except Exception as e:
        return jsonify({"success": False, "message": f"Processing error: {e}"}), 500

@app.route("/chatbot")
def chatbot_page():
    user_id = get_user_id()
    if user_id not in user_data or not user_data[user_id].get("chatbot_ready"):
        return redirect(url_for("dashboard"))
    return render_template("chatbot.html", user_id=user_id)


@app.route("/api/chat", methods=["POST"])
def chat():
    """Chat endpoint aware of compliance."""
    user_id = get_user_id()
    if user_id not in user_data or not user_data[user_id].get("chatbot_ready"):
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
            compliance_dir=str(COMPLIANCE_DIR),  # ✅ pass compliance awareness
        )

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


@app.route("/files")
def files_page():
    user_id = get_user_id()
    files_list = user_data.get(user_id, {}).get("files", [])
    return render_template("files.html", user_id=user_id, files=files_list)


@app.route('/api/get-status')
def get_status():
    """Get current processing status."""
    user_id = get_user_id()
    
    if user_id not in user_data:
        return jsonify({
            'rfp_uploaded': False,
            'vendors_count': 0,
            'processed': False,
            'chatbot_ready': False
        })
    
    user_info = user_data[user_id]
    
    return jsonify({
        'rfp_uploaded': user_info.get('rfp_file') is not None,
        'vendors_count': len(user_info.get('vendor_files', [])),
        'processed': user_info.get('processed', False),
        'chatbot_ready': user_info.get('chatbot_ready', False),
        'files_count': len(user_info.get('files', []))
    })


@app.route('/api/delete-file', methods=['POST'])
def delete_file():
    """Delete a file."""
    user_id = get_user_id()
    data = request.get_json()
    filename = data.get('filename')
    
    if user_id not in user_data:
        return jsonify({'success': False, 'message': 'No files found'}), 400
    
    try:
        # Remove from files list
        user_data[user_id]['files'] = [
            f for f in user_data[user_id]['files'] 
            if f['filename'] != filename
        ]
        
        return jsonify({'success': True, 'message': 'File deleted successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting file: {str(e)}'}), 500


if __name__ == '__main__':
    
    app.run(debug=True, host='0.0.0.0', port=8000)
