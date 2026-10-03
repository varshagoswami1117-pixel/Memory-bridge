import os
import re
import uuid
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "memory-bridge-dev-secret")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "memory-bridge-jwt-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=8)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(BASE_DIR, "memory_bridge.db"),
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

CORS(app)
db = SQLAlchemy(app)
jwt = JWTManager(app)

ALLOWED_AUDIO_EXTENSIONS = {"webm", "wav", "mp3", "m4a", "ogg"}
TAG_KEYWORDS = {
    "childhood": ["childhood", "school", "school days", "child"],
    "family": ["family", "mother", "father", "grandmother", "grandfather", "parents"],
    "village": ["village", "farm", "fields", "gaon"],
    "festival": ["festival", "diwali", "holi", "wedding", "marriage"],
    "work": ["work", "job", "office", "business", "career"],
    "advice": ["advice", "lesson", "learned", "should", "remember"],
    "travel": ["travel", "trip", "journey", "train", "bus"],
    "food": ["food", "recipe", "kitchen", "cooking"],
}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    memories = db.relationship(
        "Memory",
        backref="owner",
        lazy=True,
        cascade="all, delete-orphan",
    )

class Memory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    family_member = db.Column(db.String(100), nullable=False)
    relationship = db.Column(db.String(80), nullable=False)
    memory_text = db.Column(db.Text, nullable=True)
    transcript = db.Column(db.Text, nullable=True)
    audio_filename = db.Column(db.String(255), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

def clean_text(value, max_length=10000):
    if value is None:
        return ""
    return str(value).strip()[:max_length]

def allowed_audio(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

def make_title(text, fallback="Family Memory"):
    words = re.findall(r"\S+", clean_text(text, 240))
    if not words:
        return fallback
    title = " ".join(words[:8]).strip(" .,!?:;")
    return title + ("..." if len(words) > 8 else "")

def make_summary(text):
    text = clean_text(text)
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    useful = " ".join(sentences[:2]).strip()
    words = useful.split()
    if len(words) > 45:
        useful = " ".join(words[:45]) + "..."
    return useful

def make_tags(text):
    lower = clean_text(text).lower()
    found = []
    for tag, keywords in TAG_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            found.append(tag)
    return found[:6]

def memory_to_dict(memory):
    tags = [tag for tag in (memory.tags or "").split(",") if tag]
    audio_url = None
    if memory.audio_filename:
        audio_url = f"/api/memories/{memory.id}/audio"

    return {
        "id": memory.id,
        "title": memory.title,
        "family_member": memory.family_member,
        "relationship": memory.relationship,
        "memory_text": memory.memory_text or "",
        "transcript": memory.transcript or "",
        "summary": memory.summary or "",
        "tags": tags,
        "audio_url": audio_url,
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
    }

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "message": "Memory Bridge backend is running."})

@app.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    name = clean_text(data.get("name"), 100)
    email = clean_text(data.get("email"), 160).lower()
    password = str(data.get("password") or "")

    if not name or not email or not password:
        return jsonify({"message": "Name, email and password are required."}), 400
    if len(password) < 6:
        return jsonify({"message": "Password must contain at least 6 characters."}), 400
    if "@" not in email:
        return jsonify({"message": "Please enter a valid email address."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "An account with this email already exists."}), 409

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({
        "token": token,
        "user": {"id": user.id, "name": user.name, "email": user.email},
    }), 201

@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = clean_text(data.get("email"), 160).lower()
    password = str(data.get("password") or "")

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"message": "Invalid email or password."}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({
        "token": token,
        "user": {"id": user.id, "name": user.name, "email": user.email},
    })

@app.get("/api/auth/me")
@jwt_required()
def current_user():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({"message": "User not found."}), 404
    return jsonify({"id": user.id, "name": user.name, "email": user.email})

@app.get("/api/memories")
@jwt_required()
def list_memories():
    user_id = int(get_jwt_identity())
    query = clean_text(request.args.get("q"), 120)

    memories_query = Memory.query.filter_by(user_id=user_id)
    if query:
        pattern = f"%{query}%"
        memories_query = memories_query.filter(
            db.or_(
                Memory.title.ilike(pattern),
                Memory.family_member.ilike(pattern),
                Memory.relationship.ilike(pattern),
                Memory.memory_text.ilike(pattern),
                Memory.transcript.ilike(pattern),
                Memory.tags.ilike(pattern),
            )
        )

    memories = memories_query.order_by(Memory.created_at.desc()).all()
    return jsonify([memory_to_dict(memory) for memory in memories])

@app.post("/api/memories")
@jwt_required()
def create_memory():
    user_id = int(get_jwt_identity())
    family_member = clean_text(request.form.get("family_member"), 100)
    relationship = clean_text(request.form.get("relationship"), 80)
    memory_text = clean_text(request.form.get("memory_text"))
    transcript = clean_text(request.form.get("transcript"))
    title = clean_text(request.form.get("title"), 180)

    if not family_member or not relationship:
        return jsonify({"message": "Family member name and relationship are required."}), 400

    combined_text = transcript or memory_text
    if not combined_text:
        return jsonify({"message": "Please add a text memory or transcript."}), 400

    audio_filename = None
    audio = request.files.get("audio")
    if audio and audio.filename:
        original = secure_filename(audio.filename)
        if not allowed_audio(original):
            return jsonify({"message": "Unsupported audio format."}), 400
        extension = original.rsplit(".", 1)[1].lower()
        audio_filename = f"{uuid.uuid4().hex}.{extension}"
        audio.save(os.path.join(UPLOAD_DIR, audio_filename))

    memory = Memory(
        title=title or make_title(combined_text),
        family_member=family_member,
        relationship=relationship,
        memory_text=memory_text,
        transcript=transcript,
        audio_filename=audio_filename,
        summary=make_summary(combined_text),
        tags=",".join(make_tags(combined_text)),
        user_id=user_id,
    )
    db.session.add(memory)
    db.session.commit()

    return jsonify(memory_to_dict(memory)), 201

@app.get("/api/memories/<int:memory_id>")
@jwt_required()
def get_memory(memory_id):
    user_id = int(get_jwt_identity())
    memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
    if not memory:
        return jsonify({"message": "Memory not found."}), 404
    return jsonify(memory_to_dict(memory))

@app.get("/api/memories/<int:memory_id>/audio")
@jwt_required()
def memory_audio(memory_id):
    user_id = int(get_jwt_identity())
    memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
    if not memory or not memory.audio_filename:
        return jsonify({"message": "Audio not found."}), 404
    return send_from_directory(UPLOAD_DIR, memory.audio_filename, as_attachment=False)

@app.delete("/api/memories/<int:memory_id>")
@jwt_required()
def delete_memory(memory_id):
    user_id = int(get_jwt_identity())
    memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
    if not memory:
        return jsonify({"message": "Memory not found."}), 404

    if memory.audio_filename:
        path = os.path.join(UPLOAD_DIR, memory.audio_filename)
        if os.path.exists(path):
            os.remove(path)

    db.session.delete(memory)
    db.session.commit()
    return jsonify({"message": "Memory deleted."})

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
