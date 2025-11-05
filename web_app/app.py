from flask import Flask, render_template, request, jsonify, session
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

# Import your existing modules
import sys
PROJECT_DIR = Path("/Users/rayana/EVAL/ai_engine")  # CHANGE THIS TO YOUR PATH
sys.path.insert(0, str(PROJECT_DIR))

from parser2 import process_pdf
from embeder2 import embed_chunks

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
DB_FILE = 'rfp_database.db'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load OpenAI API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY in .env file")

client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize Database
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_and_embed(pdf_path: str):
    """Parse a PDF into chunks and embed them in FAISS - calls YOUR functions"""
    pdf_file = Path(pdf_path)
    print(f"\n📄 Processing PDF: {pdf_file.name}")
    
    # ✅ ACTUALLY CALL YOUR FUNCTIONS
    chunks_txt, chunks_json = process_pdf(str(pdf_file))
    embed_chunks(chunks_json)
    
    print(f"✅ Parsed and embedded: {pdf_file.name}")
    
    return {
        "chunks_txt": chunks_txt,
        "chunks_json": chunks_json,
        "faiss_index": f"{pdf_file.stem.replace(' ', '')}_faiss.index",
        "metadata_json": f"{pdf_file.stem.replace(' ', '')}_metadata.json"
    }

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
    
    rfps = []
    for row in rows:
        rfps.append({
            'id': row[0],
            'filename': row[1],
            'original_filename': row[2],
            'upload_date': row[3],
            'chunks_count': row[4],
            'processing_time': row[5],
            'faiss_index': row[6],
            'metadata_json': row[7],
            'status': row[8]
        })
    return rfps

def get_rfp_by_id(rfp_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM uploaded_rfps WHERE id = ?', (rfp_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'filename': row[1],
            'original_filename': row[2],
            'upload_date': row[3],
            'chunks_count': row[4],
            'processing_time': row[5],
            'faiss_index': row[6],
            'metadata_json': row[7],
            'status': row[8]
        }
    return None

def load_vector_db(index_path, metadata_path):
    """Load FAISS index and metadata."""
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"Vector DB file not found: {index_path}")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    index = faiss.read_index(index_path)
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return index, metadata

def retrieve_chunks(query, index, metadata, top_k=5):
    """Retrieve relevant chunks for a query."""
    emb = client.embeddings.create(
        model="text-embedding-3-large",
        input=query
    ).data[0].embedding

    query_vec = np.array([emb], dtype="float32")
    distances, indices = index.search(query_vec, top_k)

    return [
        {"chunk": metadata[i]["text"], "distance": float(distances[0][j]), "index": i}
        for j, i in enumerate(indices[0])
    ]

def generate_answer(query, chunks):
    """Generate answer using GPT."""
    context = "\n\n".join(f"(Chunk {c['index']})\n{c['chunk']}" for c in chunks)

    messages = [
        {"role": "system", "content":
            "You are an RFP expert. Only answer using the provided context. "
            "Every claim MUST cite the chunk number like [C3]. "
            "If no context supports the answer → respond: Not in the RFP."
        },
        {"role": "user", "content":
            f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=1500,
        temperature=0.1
    )

    return response.choices[0].message.content

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Only PDF files are allowed'}), 400
        
        # Save file
        original_filename = file.filename
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        print(f"\n🔄 Starting processing for: {filename}")
        
        # ✅ ACTUALLY PROCESS THE PDF WITH YOUR FUNCTIONS
        start_time = time.time()
        rfp_files = parse_and_embed(filepath)
        processing_time = time.time() - start_time
        
        # Save to database
        rfp_id = save_rfp_to_db(
            filename=filename,
            original_filename=original_filename,
            chunks_count=len(rfp_files['chunks_json']),
            processing_time=processing_time,
            faiss_index=rfp_files['faiss_index'],
            metadata_json=rfp_files['metadata_json']
        )
        
        print(f"✅ Saved to database with ID: {rfp_id}")
        
        return jsonify({
            'success': True,
            'rfp_id': rfp_id,
            'filename': original_filename,
            'processing_time': round(processing_time, 2),
            'chunks_count': len(rfp_files['chunks_json']),
            'faiss_index': rfp_files['faiss_index'],
            'metadata_json': rfp_files['metadata_json']
        })
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/rfps', methods=['GET'])
def list_rfps():
    """Get all uploaded RFPs"""
    try:
        rfps = get_all_rfps()
        return jsonify({'success': True, 'rfps': rfps})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        query = data.get('message', '').strip()
        rfp_id = data.get('rfp_id')
        
        if not query:
            return jsonify({'success': False, 'error': 'No message provided'}), 400
        
        if not rfp_id:
            return jsonify({'success': False, 'error': 'No RFP selected. Please upload an RFP first.'}), 400
        
        # Get RFP from database
        rfp = get_rfp_by_id(rfp_id)
        if not rfp:
            return jsonify({'success': False, 'error': 'RFP not found in database'}), 404
        
        print(f"\n💬 Chat query: {query}")
        print(f"📂 Using FAISS: {rfp['faiss_index']}")
        print(f"📂 Using metadata: {rfp['metadata_json']}")
        
        # Load vector DB with the embedded data
        index, metadata = load_vector_db(
            rfp['faiss_index'],
            rfp['metadata_json']
        )
        
        # Retrieve and generate answer
        chunks = retrieve_chunks(query, index, metadata)
        answer = generate_answer(query, chunks)
        
        print(f"✅ Generated answer with {len(chunks)} chunks")
        
        return jsonify({
            'success': True,
            'answer': answer,
            'chunks_used': len(chunks)
        })
    
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 EVAL Backend Starting...")
    print(f"📁 Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"💾 Database: {os.path.abspath(DB_FILE)}")
    print(f"🔧 Project dir: {PROJECT_DIR}")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)