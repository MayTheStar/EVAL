"""
EVAL - RFP Analysis Web Application
Flask-based web interface with user authentication
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import os
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
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
    from Scorer import VendorScorer
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all backend files are in the same directory as app.py")
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

# In-memory storage (replace with database in production)
users_db = {}  # {username: {password_hash, email, created_at}}
user_data = {}  # {user_id: {rfp_file, vendor_files, etc.}}


# ==================== HELPER FUNCTIONS ====================

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_current_user():
    """Get current logged-in user ID."""
    return session.get('user_id')


def login_required(f):
    """Decorator to require login for routes."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


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


def initialize_user_data(user_id):
    """Initialize user data structure."""
    if user_id not in user_data:
        user_data[user_id] = {
            'rfp_file': None,
            'vendor_files': [],
            'processed': False,
            'chatbot_ready': False,
            'files': [],
            'scoring': {}
        }


# ==================== PUBLIC ROUTES ====================

@app.route('/')
def landing():
    """Landing page - public."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Check credentials
        if username in users_db:
            user = users_db[username]
            if check_password_hash(user['password_hash'], password):
                # Login successful
                session['user_id'] = user['user_id']
                session['username'] = username
                
                # Initialize user data
                initialize_user_data(user['user_id'])
                
                if request.is_json:
                    return jsonify({'success': True, 'redirect': url_for('dashboard')})
                return redirect(url_for('dashboard'))
        
        # Login failed
        if request.is_json:
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
        flash('Invalid username or password', 'error')
        return render_template('login.html')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page."""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Validate
        if not username or not email or not password:
            if request.is_json:
                return jsonify({'success': False, 'message': 'All fields are required'}), 400
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        if username in users_db:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Username already exists'}), 400
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        # Create user
        user_id = str(uuid.uuid4())
        users_db[username] = {
            'user_id': user_id,
            'password_hash': generate_password_hash(password),
            'email': email,
            'created_at': datetime.now().isoformat()
        }
        
        # Auto-login after registration
        session['user_id'] = user_id
        session['username'] = username
        
        # Initialize user data
        initialize_user_data(user_id)
        
        if request.is_json:
            return jsonify({'success': True, 'redirect': url_for('dashboard')})
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')


@app.route('/logout')
def logout():
    """Logout user."""
    session.clear()
    return redirect(url_for('landing'))


# ==================== PROTECTED ROUTES ====================

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard."""
    user_id = get_current_user()
    initialize_user_data(user_id)
    
    return render_template('dashboard.html', 
                         user_id=user_id, 
                         username=session.get('username'))


@app.route('/upload-rfp')
@login_required
def upload_rfp_page():
    """RFP upload page."""
    user_id = get_current_user()
    return render_template('upload_rfp.html', 
                         user_id=user_id,
                         username=session.get('username'))


@app.route('/api/upload-rfp', methods=['POST'])
@login_required
def upload_rfp():
    """Handle RFP file upload."""
    user_id = get_current_user()
    
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
        initialize_user_data(user_id)
        
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
@login_required
def upload_vendor_page():
    """Vendor upload page."""
    user_id = get_current_user()
    return render_template('upload_vendor.html', 
                         user_id=user_id,
                         username=session.get('username'))


@app.route('/api/upload-vendor', methods=['POST'])
@login_required
def upload_vendor():
    """Handle vendor file upload."""
    user_id = get_current_user()
    
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
        initialize_user_data(user_id)
        
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
@login_required
def process_documents():
    """Process uploaded RFP and vendor files."""
    user_id = get_current_user()
    
    initialize_user_data(user_id)
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
        
        # Run pipeline
        results = system.run_full_pipeline( 
            rfp_file=rfp_file,
            vendor_files=vendor_files,
            skip_extraction=False,
            run_chatbot=False
        )
        
        # Store embeddings paths for chatbot
        if results.get('embeddings'):
            user_info['embeddings'] = {
                'faiss': results['embeddings']['faiss'],
                'metadata': results['embeddings']['metadata']
            }
            user_info['processed'] = True
            user_info['chatbot_ready'] = True
        
        # Store scoring results
        if results.get('scoring'):
            scoring_dict = {}
            for vendor_name, vendor_score in results['scoring'].items():
                scoring_dict[vendor_name] = vendor_score.to_dict()
            user_info['scoring'] = scoring_dict
        else:
            user_info.setdefault('scoring', {})
        
        return jsonify({
            'success': True,
            'message': 'Documents processed successfully! Chatbot is ready.',
            'chunks_count': {
                'rfp': len(results['rfp']['chunks']) if results.get('rfp') else 0,
                'vendors': sum(len(v['chunks']) for v in results['vendors'].values()) if results.get('vendors') else 0
            },
            'vendors_scored': len(user_info['scoring'])
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error processing documents: {str(e)}'}), 500


@app.route('/api/get-scores')
@login_required
def get_scores():
    """Return stored scoring results for current user session."""
    user_id = get_current_user()
    initialize_user_data(user_id)
    
    scoring = user_data[user_id].get('scoring', {})
    return jsonify({
        'success': True,
        'scores': {
            'vendors': scoring
        }
    })


@app.route('/chatbot')
@login_required
def chatbot_page():
    """Chatbot page."""
    user_id = get_current_user()
    initialize_user_data(user_id)
    
    if not user_data[user_id].get('chatbot_ready'):
        return redirect(url_for('dashboard'))
    
    return render_template('chatbot.html', 
                         user_id=user_id,
                         username=session.get('username'))


@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Handle chat queries."""
    user_id = get_current_user()
    initialize_user_data(user_id)
    
    if not user_data[user_id].get('chatbot_ready'):
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
                'label': chunk.get('label'),
                'distance': chunk.get('distance'),
                'page': chunk.get('page_number'),
                'preview': chunk.get('chunk', '')[:200] + '...' if len(chunk.get('chunk', '')) > 200 else chunk.get('chunk', '')
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
@login_required
def files_page():
    """Files management page."""
    user_id = get_current_user()
    initialize_user_data(user_id)
    
    files_list = user_data[user_id].get('files', [])
    
    return render_template('files.html', 
                         user_id=user_id,
                         username=session.get('username'),
                         files=files_list)


@app.route('/api/get-status')
@login_required
def get_status():
    """Get current processing status."""
    user_id = get_current_user()
    initialize_user_data(user_id)
    
    user_info = user_data[user_id]
    
    return jsonify({
        'rfp_uploaded': user_info.get('rfp_file') is not None,
        'vendors_count': len(user_info.get('vendor_files', [])),
        'processed': user_info.get('processed', False),
        'chatbot_ready': user_info.get('chatbot_ready', False),
        'files_count': len(user_info.get('files', []))
    })


@app.route('/api/delete-file', methods=['POST'])
@login_required
def delete_file():
    """Delete a file."""
    user_id = get_current_user()
    initialize_user_data(user_id)
    
    data = request.get_json()
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'success': False, 'message': 'No filename provided'}), 400
    
    try:
        # Find and remove file from user data
        user_info = user_data[user_id]
        
        # Remove from files list
        original_count = len(user_info['files'])
        user_info['files'] = [
            f for f in user_info['files'] 
            if f['filename'] != filename
        ]
        
        # Check if RFP file
        if user_info.get('rfp_file') and user_info['rfp_file']['filename'] == filename:
            # Delete physical file
            try:
                os.remove(user_info['rfp_file']['filepath'])
            except:
                pass
            user_info['rfp_file'] = None
            user_info['processed'] = False
            user_info['chatbot_ready'] = False
        
        # Check if vendor file
        vendor_to_remove = None
        for vendor in user_info.get('vendor_files', []):
            if vendor['filename'] == filename:
                vendor_to_remove = vendor
                break
        
        if vendor_to_remove:
            # Delete physical file
            try:
                os.remove(vendor_to_remove['filepath'])
            except:
                pass
            user_info['vendor_files'].remove(vendor_to_remove)
            user_info['processed'] = False
            user_info['chatbot_ready'] = False
        
        if len(user_info['files']) == original_count:
            return jsonify({'success': False, 'message': 'File not found'}), 404
        
        return jsonify({'success': True, 'message': 'File deleted successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting file: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)