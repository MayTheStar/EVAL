"""
EVAL - RFP Analysis Web Application
Flask-based web interface for the RFP Analysis System
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
import os
from pathlib import Path
from werkzeug.utils import secure_filename
import json
import uuid
from datetime import datetime
import sys

# Add current directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our refactored modules
try:
    from main import RFPAnalysisSystem
    from chatbot import create_chatbot
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all backend files (main.py, chatbot.py, etc.) are in the same directory as app.py")
    sys.exit(1)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'eval-secret-key-change-in-production')

# Configuration
UPLOAD_FOLDER = Path('uploads')
OUTPUT_FOLDER = Path('outputs')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Create directories
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

# In-memory storage for user sessions (use database in production)
user_data = {}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_user_id():
    """Get or create user ID for session."""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']


def get_user_folder(user_id):
    """Get user-specific folder."""
    user_folder = UPLOAD_FOLDER / user_id
    user_folder.mkdir(exist_ok=True)
    return user_folder


def get_output_folder(user_id):
    """Get user-specific output folder."""
    output_folder = OUTPUT_FOLDER / user_id
    output_folder.mkdir(exist_ok=True)
    return output_folder


@app.route('/')
def landing():
    """Landing page."""
    return render_template('landing.html')


@app.route('/dashboard')
def dashboard():
    """Main dashboard."""
    user_id = get_user_id()
    
    # Initialize user data if not exists
    if user_id not in user_data:
        user_data[user_id] = {
            'rfp_file': None,
            'vendor_files': [],
            'processed': False,
            'chatbot_ready': False,
            'files': []
        }
    
    return render_template('dashboard.html', user_id=user_id)


@app.route('/upload-rfp')
def upload_rfp_page():
    """RFP upload page."""
    user_id = get_user_id()
    return render_template('upload_rfp.html', user_id=user_id)


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
        # Save file
        filename = secure_filename(file.filename)
        user_folder = get_user_folder(user_id)
        filepath = user_folder / f"rfp_{filename}"
        file.save(str(filepath))
        
        # Update user data
        if user_id not in user_data:
            user_data[user_id] = {
                'rfp_file': None,
                'vendor_files': [],
                'processed': False,
                'chatbot_ready': False,
                'files': []
            }
        
        user_data[user_id]['rfp_file'] = {
            'filename': filename,
            'filepath': str(filepath),
            'uploaded_at': datetime.now().isoformat()
        }
        
        # Add to files list
        user_data[user_id]['files'].append({
            'type': 'RFP',
            'filename': filename,
            'uploaded_at': datetime.now().isoformat()
        })
        
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
    vendor_name = request.form.get('vendor_name', 'Unknown Vendor')
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file type. Please upload PDF, DOC, or DOCX'}), 400
    
    try:
        # Save file
        filename = secure_filename(file.filename)
        user_folder = get_user_folder(user_id)
        filepath = user_folder / f"vendor_{vendor_name}_{filename}"
        file.save(str(filepath))
        
        # Update user data
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
        
        # Add to files list
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


@app.route('/api/process-documents', methods=['POST'])
def process_documents():
    """Process uploaded RFP and vendor files."""
    user_id = get_user_id()
    
    if user_id not in user_data:
        return jsonify({'success': False, 'message': 'No files uploaded'}), 400
    
    user_info = user_data[user_id]
    
    if not user_info.get('rfp_file'):
        return jsonify({'success': False, 'message': 'No RFP file uploaded'}), 400
    
    try:
        # Prepare file lists
        rfp_file = user_info['rfp_file']['filepath']
        vendor_files = [
            (v['filepath'], v['vendor_name']) 
            for v in user_info.get('vendor_files', [])
        ]
        
        # Initialize system
        output_dir = get_output_folder(user_id)
        system = RFPAnalysisSystem(output_dir=str(output_dir))
        
        # Run pipeline (skip extraction for faster processing in web UI)
        results = system.run_full_pipeline(
            rfp_file=rfp_file,
            vendor_files=vendor_files,
            skip_extraction=False,  # Skip for faster processing
            run_chatbot=False  # Don't run interactive mode
        )
        
        # Store embeddings paths for chatbot
        user_info['embeddings'] = {
            'faiss': results['embeddings']['faiss'],
            'metadata': results['embeddings']['metadata']
        }
        user_info['processed'] = True
        user_info['chatbot_ready'] = True
        
        return jsonify({
            'success': True,
            'message': 'Documents processed successfully! Chatbot is ready.',
            'chunks_count': {
                'rfp': len(results['rfp']['chunks']),
                'vendors': sum(len(v['chunks']) for v in results['vendors'].values())
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error processing documents: {str(e)}'}), 500


@app.route('/chatbot')
def chatbot_page():
    """Chatbot page."""
    user_id = get_user_id()
    
    if user_id not in user_data or not user_data[user_id].get('chatbot_ready'):
        return redirect(url_for('dashboard'))
    
    return render_template('chatbot.html', user_id=user_id)


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat queries."""
    user_id = get_user_id()
    
    if user_id not in user_data or not user_data[user_id].get('chatbot_ready'):
        return jsonify({'success': False, 'message': 'Chatbot not ready. Please process documents first.'}), 400
    
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'success': False, 'message': 'No query provided'}), 400
    
    try:
        # Get embeddings paths
        embeddings = user_data[user_id]['embeddings']
        
        # Create chatbot instance
        chatbot = create_chatbot(
            embeddings['faiss'],
            embeddings['metadata']
        )
        
        # Get answer
        answer, chunks = chatbot.query(query, stream=False, top_k=5)
        
        # Format sources
        sources = [
            {
                'label': chunk['label'],
                'distance': chunk['distance'],
                'page': chunk.get('page_number'),
                'preview': chunk['chunk'][:200] + '...' if len(chunk['chunk']) > 200 else chunk['chunk']
            }
            for chunk in chunks
        ]
        
        return jsonify({
            'success': True,
            'answer': answer,
            'sources': sources
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error processing query: {str(e)}'}), 500


@app.route('/files')
def files_page():
    """Files management page."""
    user_id = get_user_id()
    
    files_list = []
    if user_id in user_data:
        files_list = user_data[user_id].get('files', [])
    
    return render_template('files.html', user_id=user_id, files=files_list)


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