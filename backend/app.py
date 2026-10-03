import os
import re
import sqlite3
import uuid
import secrets
import string
from datetime import datetime, timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, or_
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_ROOT = os.path.join(BASE_DIR, "uploads")
REGISTRY_DB = os.path.join(DATA_DIR, "family_registry.db")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_ROOT, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "memory-bridge-dev-secret-change-me")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "memory-bridge-jwt-secret-change-me")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=8)
app.config["JWT_TOKEN_LOCATION"] = ["headers", "query_string"]
app.config["JWT_QUERY_STRING_NAME"] = "token"
app.config["JWT_QUERY_STRING_VALUE_PREFIX"] = ""
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
CORS(app)

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

RegistryBase = declarative_base()
FamilyBase = declarative_base()


class FamilyRegistry(RegistryBase):
    __tablename__ = "families"
    id = Column(Integer, primary_key=True)
    family_code = Column(String(32), unique=True, nullable=False, index=True)
    family_name = Column(String(120), nullable=False)
    database_filename = Column(String(120), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class FamilyUser(FamilyBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(160), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="member")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    memories_created = relationship("Memory", back_populates="creator", foreign_keys="Memory.created_by")


class Memory(FamilyBase):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True)
    title = Column(String(180), nullable=False)
    memory_text = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    audio_filename = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    tags = Column(String(500), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    shared_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    creator = relationship("FamilyUser", foreign_keys=[created_by], back_populates="memories_created")
    shared_by = relationship("FamilyUser", foreign_keys=[shared_by_user_id])


registry_engine = create_engine(f"sqlite:///{REGISTRY_DB}", future=True)
RegistryBase.metadata.create_all(registry_engine)
RegistrySession = sessionmaker(bind=registry_engine, expire_on_commit=False)

def clean_text(value, max_length=10000):
    return str(value or "").strip()[:max_length]

def registry_session():
    return RegistrySession()

def family_record(code):
    code = clean_text(code, 32).upper()
    session = registry_session()
    try:
        return session.query(FamilyRegistry).filter_by(family_code=code).first()
    finally:
        session.close()

def family_engine(family):
    path = os.path.join(DATA_DIR, family.database_filename)
    return create_engine(f"sqlite:///{path}", future=True)

def family_session(family):
    engine = family_engine(family)
    FamilyBase.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)(), engine

def safe_family_code():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "MB-" + "".join(secrets.choice(alphabet) for _ in range(7))
        if not family_record(code):
            return code

def create_family_database(family_name, creator_name, email, password):
    code = safe_family_code()
    filename = f"family_{uuid.uuid4().hex}.db"
    registry = registry_session()
    family = FamilyRegistry(family_code=code, family_name=family_name, database_filename=filename)
    registry.add(family)
    registry.commit()
    registry.refresh(family)
    registry.close()

    session, _ = family_session(family)
    user = FamilyUser(
        name=creator_name,
        email=email.lower(),
        password_hash=generate_password_hash(password),
        role="admin",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.close()
    return family, user

def jwt_identity():
    identity = get_jwt_identity()
    if not isinstance(identity, dict):
        return None
    return identity

def authenticated_context():
    identity = jwt_identity()
    if not identity or not identity.get("family_code") or not identity.get("user_id"):
        return None, None, None
    family = family_record(identity["family_code"])
    if not family:
        return identity, None, None
    session, engine = family_session(family)
    user = session.get(FamilyUser, int(identity["user_id"]))
    return identity, family, (session, engine, user)

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
    return " ".join(words[:45]) + ("..." if len(words) > 45 else "")

def make_tags(text):
    lower = clean_text(text).lower()
    found = [tag for tag, keywords in TAG_KEYWORDS.items() if any(k in lower for k in keywords)]
    return found[:6]

def user_dict(user):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}

def memory_dict(memory, session):
    creator = session.get(FamilyUser, memory.created_by)
    subject = session.get(FamilyUser, memory.shared_by_user_id) if memory.shared_by_user_id else None
    return {
        "id": memory.id,
        "title": memory.title,
        "memory_text": memory.memory_text or "",
        "transcript": memory.transcript or "",
        "summary": memory.summary or "",
        "tags": [x for x in (memory.tags or "").split(",") if x],
        "audio_url": f"/api/memories/{memory.id}/audio" if memory.audio_filename else None,
        "created_by": user_dict(creator) if creator else None,
        "shared_by": user_dict(subject) if subject else None,
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
    }

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "message": "Memory Bridge backend is running."})

@app.post("/api/families/create")
def create_family():
    data = request.get_json(silent=True) or {}
    family_name = clean_text(data.get("family_name"), 120)
    name = clean_text(data.get("name"), 100)
    email = clean_text(data.get("email"), 160).lower()
    password = str(data.get("password") or "")
    if not family_name or not name or not email or not password:
        return jsonify({"message": "Family name, your name, email and password are required."}), 400
    if "@" not in email:
        return jsonify({"message": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"message": "Password must contain at least 6 characters."}), 400

    family, user = create_family_database(family_name, name, email, password)
    token = create_access_token(identity={"family_code": family.family_code, "user_id": user.id})
    return jsonify({
        "token": token,
        "family": {"code": family.family_code, "name": family.family_name, "role": user.role},
        "user": user_dict(user),
    }), 201

@app.post("/api/families/join")
def join_family():
    data = request.get_json(silent=True) or {}
    code = clean_text(data.get("family_code"), 32).upper()
    name = clean_text(data.get("name"), 100)
    email = clean_text(data.get("email"), 160).lower()
    password = str(data.get("password") or "")
    family = family_record(code)
    if not family:
        return jsonify({"message": "Family code not found. Check the code and try again."}), 404
    if not name or not email or not password:
        return jsonify({"message": "Name, email and password are required."}), 400
    if len(password) < 6:
        return jsonify({"message": "Password must contain at least 6 characters."}), 400

    session, _ = family_session(family)
    try:
        if session.query(FamilyUser).filter_by(email=email).first():
            return jsonify({"message": "That email is already a member of this family."}), 409
        user = FamilyUser(name=name, email=email, password_hash=generate_password_hash(password), role="member")
        session.add(user)
        session.commit()
        session.refresh(user)
        token = create_access_token(identity={"family_code": family.family_code, "user_id": user.id})
        return jsonify({
            "token": token,
            "family": {"code": family.family_code, "name": family.family_name, "role": user.role},
            "user": user_dict(user),
        }), 201
    finally:
        session.close()

@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    code = clean_text(data.get("family_code"), 32).upper()
    email = clean_text(data.get("email"), 160).lower()
    password = str(data.get("password") or "")
    family = family_record(code)
    if not family:
        return jsonify({"message": "Family code not found."}), 404

    session, _ = family_session(family)
    try:
        user = session.query(FamilyUser).filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"message": "Invalid family code, email or password."}), 401
        token = create_access_token(identity={"family_code": family.family_code, "user_id": user.id})
        return jsonify({
            "token": token,
            "family": {"code": family.family_code, "name": family.family_name, "role": user.role},
            "user": user_dict(user),
        })
    finally:
        session.close()

@app.get("/api/auth/me")
@jwt_required()
def current_user():
    identity, family, context = authenticated_context()
    if not family or not context or not context[2]:
        return jsonify({"message": "Family or user session is no longer valid."}), 401
    session, _, user = context
    try:
        return jsonify({
            "family": {"code": family.family_code, "name": family.family_name, "role": user.role},
            "user": user_dict(user),
        })
    finally:
        session.close()

@app.get("/api/family/members")
@jwt_required()
def family_members():
    identity, family, context = authenticated_context()
    if not family or not context or not context[2]:
        return jsonify({"message": "Invalid family session."}), 401
    session, _, _ = context
    try:
        members = session.query(FamilyUser).order_by(FamilyUser.name.asc()).all()
        return jsonify([user_dict(member) for member in members])
    finally:
        session.close()

@app.get("/api/memories")
@jwt_required()
def list_memories():
    identity, family, context = authenticated_context()
    if not family or not context or not context[2]:
        return jsonify({"message": "Invalid family session."}), 401
    session, _, _ = context
    query = clean_text(request.args.get("q"), 120)
    try:
        q = session.query(Memory)
        if query:
            pattern = f"%{query}%"
            q = q.filter(or_(
                Memory.title.ilike(pattern),
                Memory.memory_text.ilike(pattern),
                Memory.transcript.ilike(pattern),
                Memory.tags.ilike(pattern),
            ))
        memories = q.order_by(Memory.created_at.desc()).all()
        return jsonify([memory_dict(m, session) for m in memories])
    finally:
        session.close()

@app.post("/api/memories")
@jwt_required()
def create_memory():
    identity, family, context = authenticated_context()
    if not family or not context or not context[2]:
        return jsonify({"message": "Invalid family session."}), 401
    session, _, current = context

    shared_by_user_id = request.form.get("shared_by_user_id")
    title = clean_text(request.form.get("title"), 180)
    memory_text = clean_text(request.form.get("memory_text"))
    transcript = clean_text(request.form.get("transcript"))
    combined = transcript or memory_text

    if not shared_by_user_id:
        session.close()
        return jsonify({"message": "Please select the family member whose memory is being recorded."}), 400
    subject = session.get(FamilyUser, int(shared_by_user_id))
    if not subject:
        session.close()
        return jsonify({"message": "Selected family member does not belong to this family."}), 400
    if not combined:
        session.close()
        return jsonify({"message": "Please add a text memory or transcript."}), 400

    audio_filename = None
    audio = request.files.get("audio")
    try:
        if audio and audio.filename:
            original = secure_filename(audio.filename)
            if not allowed_audio(original):
                return jsonify({"message": "Unsupported audio format."}), 400
            extension = original.rsplit(".", 1)[1].lower()
            audio_filename = f"{uuid.uuid4().hex}.{extension}"
            family_upload_dir = os.path.join(UPLOAD_ROOT, family.family_code)
            os.makedirs(family_upload_dir, exist_ok=True)
            audio.save(os.path.join(family_upload_dir, audio_filename))

        memory = Memory(
            title=title or make_title(combined),
            memory_text=memory_text,
            transcript=transcript,
            audio_filename=audio_filename,
            summary=make_summary(combined),
            tags=",".join(make_tags(combined)),
            created_by=current.id,
            shared_by_user_id=subject.id,
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)
        return jsonify(memory_dict(memory, session)), 201
    finally:
        session.close()

@app.get("/api/memories/<int:memory_id>/audio")
@jwt_required()
def memory_audio(memory_id):
    identity, family, context = authenticated_context()
    if not family or not context or not context[2]:
        return jsonify({"message": "Invalid family session."}), 401
    session, _, _ = context
    try:
        memory = session.get(Memory, memory_id)
        if not memory or not memory.audio_filename:
            return jsonify({"message": "Audio not found."}), 404
        directory = os.path.join(UPLOAD_ROOT, family.family_code)
        return send_from_directory(directory, memory.audio_filename, as_attachment=False)
    finally:
        session.close()

@app.delete("/api/memories/<int:memory_id>")
@jwt_required()
def delete_memory(memory_id):
    identity, family, context = authenticated_context()
    if not family or not context or not context[2]:
        return jsonify({"message": "Invalid family session."}), 401
    session, _, _ = context
    try:
        memory = session.get(Memory, memory_id)
        if not memory:
            return jsonify({"message": "Memory not found."}), 404
        if memory.audio_filename:
            path = os.path.join(UPLOAD_ROOT, family.family_code, memory.audio_filename)
            if os.path.exists(path):
                os.remove(path)
        session.delete(memory)
        session.commit()
        return jsonify({"message": "Memory deleted."})
    finally:
        session.close()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
