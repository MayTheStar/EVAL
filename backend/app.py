from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
from werkzeug.utils import secure_filename
import os
import json
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv
import time
import sqlite3
from datetime import datetime
import sys
import shutil
import traceback

# ---------------------------
# Paths (project-local)
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent  # project root
AI_ENGINE_DIR = PROJECT_ROOT / "ai_engine"
sys.path.insert(0, str(AI_ENGINE_DIR))

# Import your modules
from parser2 import process_pdf
from embeder2 import embed_chunks

# App init
app = Flask(__name__, template_folder=str(BASE_DIR / 'templates'), static_folder=str(BASE_DIR / 'static'))
CORS(app)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-change-in-prod')

# Storage folders
UPLOAD_FOLDER = BASE_DIR / 'uploads'
DATA_FOLDER = BASE_DIR / 'data'
DB_FILE = BASE_DIR / 'rfp_database.db'
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {'pdf'}

for p in (UPLOAD_FOLDER, DATA_FOLDER):
    p.mkdir(parents=True, exist_ok=True)

# Load OpenAI key
load_dotenv(str(PROJECT_ROOT / '.env'))
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError('Missing OPENAI_API_KEY in .env file')
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------
# Database
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS uploaded_rfps
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filename TEXT NOT NULL,
                  original_filename TEXT NOT NULL,
                  upload_date TEXT NOT NULL,
                  chunks_count INTEGER,
                  processing_time REAL,
                  faiss_index TEXT,
                  metadata_json TEXT,
                  status TEXT)''')
    conn.commit()
    conn.close()

init_db()

def save_rfp_to_db(filename, original_filename, chunks_count, processing_time, faiss_index, metadata_json):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''INSERT INTO uploaded_rfps
                 (filename, original_filename, upload_date, chunks_count, processing_time,
                  faiss_index, metadata_json, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (filename, original_filename, datetime.now().isoformat(),
               chunks_count, processing_time, faiss_index, metadata_json, 'completed'))
    rfp_id = c.lastrowid
    conn.commit()
    conn.close()
    return rfp_id

def get_all_rfps():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM uploaded_rfps ORDER BY upload_date DESC')
    rows = c.fetchall()
    conn.close()
    
    return [{
        'id': row[0],
        'filename': row[1],
        'original_filename': row[2],
        'upload_date': row[3],
        'chunks_count': row[4],
        'processing_time': row[5],
        'faiss_index': row[6],
        'metadata_json': row[7],
        'status': row[8]
    } for row in rows]

def get_rfp_by_id(rfp_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM uploaded_rfps WHERE id = ?', (rfp_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0], 'filename': row[1], 'original_filename': row[2],
            'upload_date': row[3], 'chunks_count': row[4], 'processing_time': row[5],
            'faiss_index': row[6], 'metadata_json': row[7], 'status': row[8]
        }
    return None

# ---------------------------
# File helpers
# ---------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _find_generated_files(pdf_stem: str):
    """Search for generated index/json files."""
    index_candidates = []
    metadata_candidates = []
    
    for base in (AI_ENGINE_DIR, PROJECT_ROOT, BASE_DIR):
        for p in base.glob(f"{pdf_stem}*"):
            name = p.name.lower()
            if name.endswith('.index') or 'faiss' in name:
                index_candidates.append(p)
            if name.endswith('.json') and 'metadata' in name:
                metadata_candidates.append(p)
    
    if not index_candidates:
        for base in (AI_ENGINE_DIR, PROJECT_ROOT, BASE_DIR):
            index_candidates.extend(base.glob('*.index'))
    if not metadata_candidates:
        for base in (AI_ENGINE_DIR, PROJECT_ROOT, BASE_DIR):
            metadata_candidates.extend(base.glob('*metadata*.json'))
    
    index_candidates = sorted(index_candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    metadata_candidates = sorted(metadata_candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    
    return (index_candidates[0] if index_candidates else None,
            metadata_candidates[0] if metadata_candidates else None)

def _ensure_files_in_data(index_path, metadata_path, pdf_stem):
    """Move files to DATA_FOLDER."""
    stored_index_name = None
    stored_metadata_name = None
    
    if index_path:
        dest_index_name = f"{pdf_stem}_faiss.index"
        dest_index_path = DATA_FOLDER / dest_index_name
        if dest_index_path.exists():
            dest_index_path = DATA_FOLDER / f"{pdf_stem}_faiss_{int(time.time())}.index"
        if index_path.resolve() != dest_index_path.resolve():
            shutil.copy2(str(index_path), str(dest_index_path))
        stored_index_name = dest_index_path.name
    
    if metadata_path:
        dest_meta_name = f"{pdf_stem}_metadata.json"
        dest_meta_path = DATA_FOLDER / dest_meta_name
        if dest_meta_path.exists():
            dest_meta_path = DATA_FOLDER / f"{pdf_stem}_metadata_{int(time.time())}.json"
        if metadata_path.resolve() != dest_meta_path.resolve():
            shutil.copy2(str(metadata_path), str(dest_meta_path))
        stored_metadata_name = dest_meta_path.name
    
    return stored_index_name, stored_metadata_name

# ---------------------------
# Core pipeline
# ---------------------------
def parse_and_embed(pdf_path: str):
    pdf_file = Path(pdf_path)
    pdf_stem = pdf_file.stem.replace(' ', '')
    
    print(f"\n📄 Processing: {pdf_file.name}")
    
    # Call your parser
    parse_result = process_pdf(str(pdf_file))
    if isinstance(parse_result, tuple) and len(parse_result) >= 2:
        chunks_txt, chunks_json = parse_result[0], parse_result[1]
    else:
        chunks_json = parse_result
        chunks_txt = [c.get('text', '') if isinstance(c, dict) else str(c) for c in chunks_json] if isinstance(chunks_json, list) else []
    
    print(f"✅ Parsed {len(chunks_json) if isinstance(chunks_json, list) else 0} chunks")
    
    # Call your embedder
    embed_return = None
    try:
        embed_return = embed_chunks(chunks_json)
    except Exception as e:
        print(f"⚠️ embed_chunks(chunks_json) failed: {e}")
        try:
            embed_return = embed_chunks(str(pdf_file))
        except Exception as e2:
            print(f"⚠️ embed_chunks(path) also failed: {e2}")
    
    # Find generated files
    index_path = None
    metadata_path = None
    if embed_return:
        if isinstance(embed_return, (tuple, list)) and len(embed_return) >= 2:
            idx_candidate, meta_candidate = embed_return[0], embed_return[1]
            index_path = Path(idx_candidate) if idx_candidate else None
            metadata_path = Path(meta_candidate) if meta_candidate else None
    
    if not index_path or not metadata_path:
        found_index, found_meta = _find_generated_files(pdf_stem)
        if found_index and not index_path:
            index_path = found_index
        if found_meta and not metadata_path:
            metadata_path = found_meta
    
    if not index_path or not metadata_path:
        raise FileNotFoundError(f'Could not find FAISS index or metadata. Searched for: {pdf_stem}*')
    
    print(f"📁 Found index: {index_path.name}")
    print(f"📁 Found metadata: {metadata_path.name}")
    
    # Move to data folder
    faiss_basename, metadata_basename = _ensure_files_in_data(index_path, metadata_path, pdf_stem)
    
    print(f"✅ Stored as: {faiss_basename}, {metadata_basename}")
    
    return {
        'chunks_txt': chunks_txt,
        'chunks_json': chunks_json,
        'faiss_index': faiss_basename,
        'metadata_json': metadata_basename
    }

# ---------------------------
# Vector DB operations
# ---------------------------
def load_vector_db(index_filename, metadata_filename):
    index_path = DATA_FOLDER / index_filename
    metadata_path = DATA_FOLDER / metadata_filename
    
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")
    
    index = faiss.read_index(str(index_path))
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    return index, metadata

def retrieve_chunks(query, index, metadata, top_k=5):
    emb = client.embeddings.create(
        model='text-embedding-3-large',
        input=query
    ).data[0].embedding
    
    query_vec = np.array([emb], dtype='float32')
    distances, indices = index.search(query_vec, top_k)
    
    result = []
    for j, i in enumerate(indices[0]):
        if i < 0:
            continue
        meta_item = metadata[i] if i < len(metadata) else {}
        txt = meta_item.get('text') if isinstance(meta_item, dict) else str(meta_item)
        result.append({'chunk': txt, 'distance': float(distances[0][j]), 'index': int(i)})
    return result

def generate_answer(query, chunks):
    context = "\n\n".join(f"(Chunk {c['index']})\n{c['chunk']}" for c in chunks)
    messages = [
        {'role': 'system', 'content':
            'You are an RFP expert. Only answer using the provided context. '
            'Every claim MUST cite the chunk number like [C3]. '
            'If no context supports the answer → respond: Not in the RFP.'
        },
        {'role': 'user', 'content': f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"}
    ]
    
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
        max_tokens=1500,
        temperature=0.1
    )
    
    return response.choices[0].message.content

# ---------------------------
# Routes
# ---------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    print("\n" + "="*60)
    print("📤 UPLOAD REQUEST")
    print("="*60)
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Only PDF files allowed'}), 400
        
        original_filename = file.filename
        filename = secure_filename(file.filename)
        save_path = UPLOAD_FOLDER / filename
        file.save(str(save_path))
        
        print(f"✅ Saved: {save_path}")
        
        start = time.time()
        rfp_files = parse_and_embed(str(save_path))
        proc_time = time.time() - start
        
        chunks_count = len(rfp_files['chunks_json']) if isinstance(rfp_files['chunks_json'], list) else 0
        
        rfp_id = save_rfp_to_db(
            filename=filename,
            original_filename=original_filename,
            chunks_count=chunks_count,
            processing_time=proc_time,
            faiss_index=rfp_files['faiss_index'],
            metadata_json=rfp_files['metadata_json']
        )
        
        print(f"✅ Saved to DB with ID: {rfp_id}")
        print("="*60 + "\n")
        
        return jsonify({
            'success': True,
            'rfp_id': rfp_id,
            'filename': original_filename,
            'processing_time': round(proc_time, 2),
            'chunks_count': chunks_count,
            'faiss_index': rfp_files['faiss_index'],
            'metadata_json': rfp_files['metadata_json']
        })
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        traceback.print_exc()
        print("="*60 + "\n")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/rfps', methods=['GET'])
def list_rfps():
    try:
        return jsonify({'success': True, 'rfps': get_all_rfps()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json or {}
        query = data.get('message', '').strip()
        rfp_id = data.get('rfp_id')
        
        if not query:
            return jsonify({'success': False, 'error': 'No message'}), 400
        if not rfp_id:
            return jsonify({'success': False, 'error': 'No RFP selected'}), 400
        
        rfp = get_rfp_by_id(rfp_id)
        if not rfp:
            return jsonify({'success': False, 'error': 'RFP not found'}), 404
        
        print(f"\n💬 Query: {query}")
        print(f"📂 Using: {rfp['faiss_index']}, {rfp['metadata_json']}")
        
        index, metadata = load_vector_db(rfp['faiss_index'], rfp['metadata_json'])
        chunks = retrieve_chunks(query, index, metadata)
        answer = generate_answer(query, chunks)
        
        print(f"✅ Answer generated with {len(chunks)} chunks\n")
        
        return jsonify({'success': True, 'answer': answer, 'chunks_used': len(chunks)})
    
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 EVAL Backend Starting")
    print(f"📁 Upload: {UPLOAD_FOLDER}")
    print(f"📁 Data: {DATA_FOLDER}")
    print(f"💾 Database: {DB_FILE}")
    print(f"🔧 AI Engine: {AI_ENGINE_DIR}")
    print("="*60 + "\n")
    import multiprocessing as mp
    mp.set_start_method('spawn', force=True)
    app.run(debug=True, port=5000, use_reloader=False)