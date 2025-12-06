"""
MemoryBridge - Backend (Flask + SQLAlchemy) - Initial Project Scaffold

What this file contains (ready-to-run scaffold):
- MySQL SQL schema (CREATE TABLE statements)
- Flask app with SQLAlchemy models that match the schema
- Endpoints:
  - /register_user   [POST] -> create a user
  - /upload_audio    [POST] -> upload audio file + metadata (saves file, creates Memory)
  - /add_memory_text [POST] -> add memory by text (for quick testing)
  - /get_memories    [GET]  -> list / search memories (simple keyword search)
  - /play_audio/<id> [GET]  -> serve saved audio file
- Simple AI hooks (stubs) for:
  - speech_to_text(audio_path)  -> implement with Whisper or Google Speech API
  - summarize_text(text)        -> implement with transformers summarization
  - auto_tag(text)              -> lightweight keyword-based tagging + AI hook

How to use (quick):
1) Install requirements (example):
   pip install flask sqlalchemy pymysql python-dotenv werkzeug
   # Optional (AI): pip install openai whisper transformers torchaudio

2) Create a MySQL database and update DATABASE_URL in .env file.
   Example .env:
     DATABASE_URL=mysql+pymysql://username:password@localhost:3306/memorybridge
     UPLOAD_FOLDER=./uploads

3) Run the app:
   python MemoryBridge_backend.py

Notes:
- AI functions are stubs; replace them with calls to Whisper, Google Speech-to-Text, or HuggingFace models.
- This scaffold focuses on correctness of SQL schema, robust endpoints, and an easy-to-follow structure for capstone demo.

"""

from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import re
from werkzeug.utils import secure_filename
from sqlalchemy import func

# -------------------- Configuration --------------------
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', './uploads')
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'ogg'}

DATABASE_URL = os.environ.get('DATABASE_URL', 'mysql+pymysql://user:password@localhost:3306/memorybridge')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(_name_)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# -------------------- SQLAlchemy Models (MySQL-compatible) --------------------
class User(db.Model):
    _tablename_ = 'users'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer)
    generation = db.Column(db.String(50))  # grandparent/parent/young/kid
    relationship = db.Column(db.String(100))

    memories = db.relationship('Memory', backref='author', lazy=True)

class Memory(db.Model):
    _tablename_ = 'memories'
    memory_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    title = db.Column(db.String(250))
    text_content = db.Column(db.Text)
    audio_path = db.Column(db.String(500))
    memory_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tags = db.relationship('Tag', backref='memory', lazy=True)
    attachments = db.relationship('Attachment', backref='memory', lazy=True)

class Tag(db.Model):
    _tablename_ = 'tags'
    tag_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    memory_id = db.Column(db.Integer, db.ForeignKey('memories.memory_id'), nullable=False)
    tag_type = db.Column(db.String(100))  # emotional/topic/generation
    tag_value = db.Column(db.String(150))

class Attachment(db.Model):
    _tablename_ = 'attachments'
    attachment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    memory_id = db.Column(db.Integer, db.ForeignKey('memories.memory_id'), nullable=False)
    file_path = db.Column(db.String(500))
    file_type = db.Column(db.String(50))

# -------------------- Utility functions --------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Simple keyword-based tagger — replace/upgrade with AI later
KEYWORD_TAG_MAP = {
    'recipe': ('topic','food'),
    'cook': ('topic','food'),
    'childhood': ('topic','childhood'),
    'school': ('topic','education'),
    'marriage': ('topic','relationship'),
    'love': ('emotion','love'),
    'happy': ('emotion','happy'),
    'sad': ('emotion','sad'),
}


def auto_tag(text):
    text_low = text.lower()
    tags = []
    for kw, (t_type, t_val) in KEYWORD_TAG_MAP.items():
        if kw in text_low:
            tags.append({'tag_type': t_type, 'tag_value': t_val})
    # Simple heuristic: length -> long story -> 'detailed'
    if len(text.split()) > 120:
        tags.append({'tag_type':'meta','tag_value':'detailed'})
    return tags

# Stub: speech to text (use Whisper or Google STT in production)
def speech_to_text(audio_path):
    # Example: integrate OpenAI Whisper or Google Cloud Speech-to-Text here.
    # For now return a placeholder string so you can demo the pipeline.
    print(f"[speech_to_text] called for: {audio_path}")
    return "(transcribed text placeholder) This is where the transcript will appear once you integrate Whisper or Google STT."

# Stub: summarization (use transformers pipeline 'summarization')
def summarize_text(text, max_length=60):
    # Replace with model-based summarizer for better results.
    sentences = re.split(r'(?<=[.!?]) +', text)
    if len(sentences) <= 2:
        return text
    return ' '.join(sentences[:2])

# -------------------- API Endpoints --------------------
@app.route('/init_db', methods=['POST'])
def init_db():
    """Initialize DB tables. Run once during setup."""
    db.create_all()
    return jsonify({'status':'ok','message':'Database initialized (tables created)'}), 201

@app.route('/register_user', methods=['POST'])
def register_user():
    data = request.json or {}
    name = data.get('name')
    age = data.get('age')
    generation = data.get('generation')
    relationship = data.get('relationship')
    if not name:
        return jsonify({'error':'name required'}), 400
    user = User(name=name, age=age, generation=generation, relationship=relationship)
    db.session.add(user)
    db.session.commit()
    return jsonify({'status':'ok','user_id':user.user_id}), 201

@app.route('/add_memory_text', methods=['POST'])
def add_memory_text():
    """Add memory directly by text for quick testing/demo."""
    data = request.json or {}
    user_id = data.get('user_id')
    title = data.get('title')
    text = data.get('text')
    memory_date_str = data.get('memory_date')  # optional YYYY-MM-DD

    if not all([user_id, text]):
        return jsonify({'error':'user_id and text required'}), 400

    memory_date = None
    if memory_date_str:
        try:
            memory_date = datetime.strptime(memory_date_str, '%Y-%m-%d').date()
        except Exception:
            return jsonify({'error':'memory_date must be YYYY-MM-DD'}), 400

    mem = Memory(user_id=user_id, title=title, text_content=text, memory_date=memory_date)
    db.session.add(mem)
    db.session.commit()

    # auto-tag
    tags = auto_tag(text)
    for t in tags:
        tag = Tag(memory_id=mem.memory_id, tag_type=t['tag_type'], tag_value=t['tag_value'])
        db.session.add(tag)
    db.session.commit()

    return jsonify({'status':'ok','memory_id':mem.memory_id}), 201

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    """Upload an audio file and create a memory. The endpoint will call speech_to_text()
       and populate text_content, tags, and store audio file path.
       Form-data fields:
         - user_id (int)
         - title (optional)
         - memory_date (YYYY-MM-DD optional)
         - audio_file (file)
    """
    if 'audio_file' not in request.files:
        return jsonify({'error':'no audio file uploaded'}), 400
    audio_file = request.files['audio_file']
    user_id = request.form.get('user_id')
    title = request.form.get('title')
    memory_date_str = request.form.get('memory_date')

    if not user_id:
        return jsonify({'error':'user_id required'}), 400
    try:
        user_id = int(user_id)
    except Exception:
        return jsonify({'error':'user_id must be integer'}), 400

    if audio_file.filename == '' or not allowed_file(audio_file.filename):
        return jsonify({'error':'invalid file'}), 400

    filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_" + audio_file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    audio_file.save(save_path)

    memory_date = None
    if memory_date_str:
        try:
            memory_date = datetime.strptime(memory_date_str, '%Y-%m-%d').date()
        except Exception:
            return jsonify({'error':'memory_date must be YYYY-MM-DD'}), 400

    # 1) create memory record with audio_path (text will be filled after transcription)
    mem = Memory(user_id=user_id, title=title, audio_path=save_path, memory_date=memory_date)
    db.session.add(mem)
    db.session.commit()

    # 2) Transcribe (stub)
    transcript = speech_to_text(save_path)
    mem.text_content = transcript

    # 3) Summarize
    summary = summarize_text(transcript)

    # 4) Auto-tag
    tags = auto_tag(transcript + ' ' + (title or ''))
    for t in tags:
        tag = Tag(memory_id=mem.memory_id, tag_type=t['tag_type'], tag_value=t['tag_value'])
        db.session.add(tag)

    db.session.commit()

    return jsonify({'status':'ok','memory_id':mem.memory_id,'summary':summary}), 201

@app.route('/get_memories', methods=['GET'])
def get_memories():
    """Search and list memories. Query params:
         - q : keyword search
         - user_id : filter by user
         - tag : filter by tag value
    """
    q = request.args.get('q')
    user_id = request.args.get('user_id')
    tag = request.args.get('tag')

    query = db.session.query(Memory)
    if user_id:
        try:
            query = query.filter(Memory.user_id == int(user_id))
        except Exception:
            return jsonify({'error':'invalid user_id'}), 400

    if q:
        # simple keyword search across title and text_content
        like_q = f"%{q}%"
        query = query.filter(db.or_(Memory.title.ilike(like_q), Memory.text_content.ilike(like_q)))

    if tag:
        query = query.join(Tag).filter(Tag.tag_value == tag)

    results = []
    for mem in query.order_by(Memory.created_at.desc()).limit(200).all():
        results.append({
            'memory_id': mem.memory_id,
            'user_id': mem.user_id,
            'title': mem.title,
            'text_preview': (mem.text_content[:300] + '...') if mem.text_content and len(mem.text_content) > 300 else mem.text_content,
            'audio_available': bool(mem.audio_path),
            'memory_date': mem.memory_date.isoformat() if mem.memory_date else None,
            'created_at': mem.created_at.isoformat()
        })

    return jsonify({'status':'ok','count':len(results),'memories':results}), 200

@app.route('/play_audio/<int:memory_id>', methods=['GET'])
def play_audio(memory_id):
    mem = Memory.query.get(memory_id)
    if not mem or not mem.audio_path:
        return jsonify({'error':'audio not found'}), 404
    directory = os.path.dirname(mem.audio_path)
    filename = os.path.basename(mem.audio_path)
    return send_from_directory(directory, filename)

# -------------------- MySQL Schema SQL (for direct use) --------------------
MYSQL_SCHEMA_SQL = '''
-- MySQL schema for MemoryBridge (run on your MySQL server)
CREATE DATABASE IF NOT EXISTS memorybridge CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE memorybridge;

CREATE TABLE IF NOT EXISTS users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  age INT,
  generation VARCHAR(50),
  relationship VARCHAR(100)
) ENG huINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS memories (
  memory_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  title VARCHAR(250),
  text_content TEXT,
  audio_path VARCHAR(500),
  memory_date DATE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS tags (
  tag_id INT AUTO_INCREMENT PRIMARY KEY,
  memory_id INT NOT NULL,
  tag_type VARCHAR(100),
  tag_value VARCHAR(150),
  FOREIGN KEY (memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS attachments (
  attachment_id INT AUTO_INCREMENT PRIMARY KEY,
  memory_id INT NOT NULL,
  file_path VARCHAR(500),
  file_type VARCHAR(50),
  FOREIGN KEY (memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
'''

# -------------------- Run server --------------------
if _name_ == '_main_':
    print('--- MemoryBridge backend scaffold ---')
    print('MySQL schema SQL is available in MYSQL_SCHEMA_SQL variable')
    print('Ensure DATABASE_URL env var is configured. Example:')
    print("mysql+pymysql://user:password@localhost:3306/memorybridge")
    app.run(host='0.0.0.0', port=5000, debug=True)

