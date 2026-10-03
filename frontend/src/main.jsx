import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = "http://127.0.0.1:5000/api";

async function api(path, options = {}) {
  const token = localStorage.getItem("memory_bridge_token");
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(API + path, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.message || "Something went wrong.");
  return data;
}

function Auth({ onLogin }) {
  const [registerMode, setRegisterMode] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const path = registerMode ? "/auth/register" : "/auth/login";
      const data = await api(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      localStorage.setItem("memory_bridge_token", data.token);
      localStorage.setItem("memory_bridge_user", JSON.stringify(data.user));
      onLogin(data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="brand-mark">MB</div>
        <p className="eyebrow">PRESERVE • CONNECT • REMEMBER</p>
        <h1>Memory Bridge</h1>
        <p className="muted">A simple digital place for your family's stories, memories and advice.</p>

        <form onSubmit={submit} className="form-stack">
          {registerMode && (
            <label>
              Your name
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Varsha" required />
            </label>
          )}
          <label>
            Email
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" required />
          </label>
          <label>
            Password
            <input type="password" minLength="6" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="At least 6 characters" required />
          </label>
          {error && <div className="error">{error}</div>}
          <button className="primary" disabled={busy}>{busy ? "Please wait..." : registerMode ? "Create family account" : "Log in"}</button>
        </form>

        <button className="link-button" onClick={() => { setRegisterMode(!registerMode); setError(""); }}>
          {registerMode ? "Already have an account? Log in" : "New here? Create an account"}
        </button>
      </section>
    </main>
  );
}

function Recorder({ onRecorded, onTranscript }) {
  const [recording, setRecording] = useState(false);
  const [supported, setSupported] = useState(true);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const recognitionRef = useRef(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSupported(false);
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = "en-IN";
    recognition.onresult = (event) => {
      let text = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        text += event.results[i][0].transcript + " ";
      }
      onTranscript(text);
    };
    recognitionRef.current = recognition;
  }, [onTranscript]);

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        onRecorded(blob);
        stream.getTracks().forEach((track) => track.stop());
      };
      recorder.start();
      recorderRef.current = recorder;
      recognitionRef.current?.start();
      setRecording(true);
    } catch {
      alert("Microphone permission is required to record a memory.");
    }
  };

  const stop = () => {
    recorderRef.current?.stop();
    try { recognitionRef.current?.stop(); } catch {}
    setRecording(false);
  };

  return (
    <div className="recorder">
      <div>
        <strong>{recording ? "Recording memory..." : "Audio memory"}</strong>
        <p className="muted small">
          {supported ? "Speech-to-text will be captured by your browser when supported." : "Speech recognition is not supported in this browser. You can still record audio and type the transcript."}
        </p>
      </div>
      <button type="button" className={recording ? "danger" : "secondary"} onClick={recording ? stop : start}>
        {recording ? "Stop recording" : "Start recording"}
      </button>
    </div>
  );
}

function AddMemory({ onSaved, onCancel }) {
  const [form, setForm] = useState({ family_member: "", relationship: "", title: "", memory_text: "", transcript: "" });
  const [audio, setAudio] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const data = new FormData();
      Object.entries(form).forEach(([key, value]) => data.append(key, value));
      if (audio) data.append("audio", audio, "memory.webm");
      const saved = await api("/memories", { method: "POST", body: data });
      onSaved(saved);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">NEW MEMORY</p>
          <h2>Capture a family story</h2>
        </div>
        <button className="ghost" onClick={onCancel}>Cancel</button>
      </div>

      <form onSubmit={submit} className="form-stack">
        <div className="two-col">
          <label>
            Family member
            <input value={form.family_member} onChange={(e) => update("family_member", e.target.value)} placeholder="Grandmother's name" required />
          </label>
          <label>
            Relationship
            <input value={form.relationship} onChange={(e) => update("relationship", e.target.value)} placeholder="Grandmother" required />
          </label>
        </div>

        <label>
          Memory title <span className="optional">(optional)</span>
          <input value={form.title} onChange={(e) => update("title", e.target.value)} placeholder="A childhood memory..." />
        </label>

        <label>
          Write the memory
          <textarea value={form.memory_text} onChange={(e) => update("memory_text", e.target.value)} placeholder="Type the story here if you already have it in text." rows="6" />
        </label>

        <Recorder
          onRecorded={setAudio}
          onTranscript={(text) => update("transcript", (form.transcript ? form.transcript + " " : "") + text)}
        />

        <label>
          Transcript / spoken story
          <textarea value={form.transcript} onChange={(e) => update("transcript", e.target.value)} placeholder="The speech-to-text transcript appears here. You can edit it before saving." rows="6" />
        </label>

        {audio && <div className="success">Audio recording ready to save.</div>}
        {error && <div className="error">{error}</div>}
        <button className="primary" disabled={busy}>{busy ? "Saving..." : "Save memory"}</button>
      </form>
    </section>
  );
}

function MemoryCard({ memory, onDelete }) {
  const token = localStorage.getItem("memory_bridge_token");
  const audioSrc = memory.audio_url ? `${API}${memory.audio_url}?token=${encodeURIComponent(token || "")}` : null;

  return (
    <article className="memory-card">
      <div className="memory-top">
        <div>
          <p className="eyebrow">{memory.relationship}</p>
          <h3>{memory.title}</h3>
          <p className="muted">Shared by {memory.family_member}</p>
        </div>
        <button className="delete-button" onClick={() => onDelete(memory.id)} aria-label="Delete memory">Delete</button>
      </div>

      {memory.summary && (
        <div className="summary-box">
          <strong>Simple summary</strong>
          <p>{memory.summary}</p>
        </div>
      )}

      {(memory.memory_text || memory.transcript) && (
        <p className="memory-text">{memory.memory_text || memory.transcript}</p>
      )}

      {memory.tags.length > 0 && (
        <div className="tags">{memory.tags.map((tag) => <span key={tag}>#{tag}</span>)}</div>
      )}

      {audioSrc && (
        <audio controls src={audioSrc} className="audio-player">
          Your browser does not support audio playback.
        </audio>
      )}

      <p className="date-text">{memory.created_at ? new Date(memory.created_at).toLocaleString() : ""}</p>
    </article>
  );
}

function Dashboard({ user, onLogout }) {
  const [memories, setMemories] = useState([]);
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async (query = "") => {
    setLoading(true);
    try {
      const data = await api("/memories" + (query ? `?q=${encodeURIComponent(query)}` : ""));
      setMemories(data);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const deleteMemory = async (id) => {
    if (!window.confirm("Delete this memory?")) return;
    try {
      await api(`/memories/${id}`, { method: "DELETE" });
      setMemories((items) => items.filter((item) => item.id !== id));
    } catch (err) {
      setError(err.message);
    }
  };

  const logout = () => {
    localStorage.removeItem("memory_bridge_token");
    localStorage.removeItem("memory_bridge_user");
    onLogout();
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">MEMORY BRIDGE</p>
          <h1>Family memory archive</h1>
        </div>
        <div className="top-actions">
          <span className="welcome">Hi, {user.name}</span>
          <button className="ghost" onClick={logout}>Log out</button>
        </div>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">KEEP THEIR STORIES ALIVE</p>
          <h2>Every memory can become a bridge between generations.</h2>
          <p className="muted">Record a story, save the transcript, and return to it whenever your family wants to listen or read.</p>
        </div>
        <button className="primary hero-button" onClick={() => setShowAdd(true)}>+ Add memory</button>
      </section>

      {showAdd ? (
        <AddMemory
          onCancel={() => setShowAdd(false)}
          onSaved={(memory) => {
            setMemories((items) => [memory, ...items]);
            setShowAdd(false);
          }}
        />
      ) : (
        <section className="panel">
          <div className="search-row">
            <div>
              <p className="eyebrow">YOUR ARCHIVE</p>
              <h2>{memories.length} {memories.length === 1 ? "memory" : "memories"}</h2>
            </div>
            <input className="search-input" value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load(search)} placeholder="Search memories..." />
            <button className="secondary" onClick={() => load(search)}>Search</button>
          </div>

          {error && <div className="error">{error}</div>}
          {loading ? (
            <p className="muted">Loading memories...</p>
          ) : memories.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">♡</div>
              <h3>No memories yet</h3>
              <p className="muted">Add your first family story to start building the archive.</p>
              <button className="primary" onClick={() => setShowAdd(true)}>Add first memory</button>
            </div>
          ) : (
            <div className="memory-grid">
              {memories.map((memory) => <MemoryCard key={memory.id} memory={memory} onDelete={deleteMemory} />)}
            </div>
          )}
        </section>
      )}

      <footer>Memory Bridge • A college project focused on preserving family stories.</footer>
    </main>
  );
}

function App() {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("memory_bridge_user") || "null"); }
    catch { return null; }
  });

  if (!user) return <Auth onLogin={setUser} />;
  return <Dashboard user={user} onLogout={() => setUser(null)} />;
}

createRoot(document.getElementById("root")).render(<App />);
