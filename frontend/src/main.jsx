import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = "http://127.0.0.1:5000/api";
const TOKEN_KEY = "memory_bridge_token";
const USER_KEY = "memory_bridge_user";

async function api(path, options = {}) {
  const token = localStorage.getItem(TOKEN_KEY);
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = "Bearer " + token;
  const response = await fetch(API + path, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.message || "Something went wrong.");
  return data;
}

function Auth({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ family_name: "", name: "", email: "", password: "", relationship: "", join_code: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const path = mode === "create" ? "/families/create" : mode === "join" ? "/families/join" : "/auth/login";
      const payload = mode === "login" ? { email: form.email, password: form.password } : form;
      const data = await api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      localStorage.setItem(TOKEN_KEY, data.token);
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));
      onLogin(data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const title = mode === "create" ? "Create your family space" : mode === "join" ? "Join your family" : "Welcome back";
  const button = mode === "create" ? "Create family" : mode === "join" ? "Join family" : "Log in";

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="brand-mark">MB</div>
        <p className="eyebrow">PRESERVE • CONNECT • REMEMBER</p>
        <h1>Memory Bridge</h1>
        <h2 className="auth-title">{title}</h2>
        <p className="muted">A private family space for stories, memories and advice from every generation.</p>
        <div className="auth-tabs">
          <button type="button" className={mode === "login" ? "tab active" : "tab"} onClick={() => { setMode("login"); setError(""); }}>Log in</button>
          <button type="button" className={mode === "create" ? "tab active" : "tab"} onClick={() => { setMode("create"); setError(""); }}>Create family</button>
          <button type="button" className={mode === "join" ? "tab active" : "tab"} onClick={() => { setMode("join"); setError(""); }}>Join family</button>
        </div>
        <form onSubmit={submit} className="form-stack">
          {mode === "create" && <label>Family name<input value={form.family_name} onChange={(e) => setForm({ ...form, family_name: e.target.value })} placeholder="The Goswami Family" required /></label>}
          {mode !== "login" && <>
            <label>Your name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Varsha" required /></label>
            <label>Relationship<input value={form.relationship} onChange={(e) => setForm({ ...form, relationship: e.target.value })} placeholder="Daughter / Grandmother / Son" required /></label>
          </>}
          {mode === "join" && <label>Family join code<input value={form.join_code} onChange={(e) => setForm({ ...form, join_code: e.target.value.toUpperCase() })} placeholder="8-character code" maxLength="8" required /></label>}
          <label>Email<input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" required /></label>
          <label>Password<input type="password" minLength="6" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="At least 6 characters" required /></label>
          {error && <div className="error">{error}</div>}
          <button className="primary" disabled={busy}>{busy ? "Please wait..." : button}</button>
        </form>
        <div className="auth-help">
          {mode === "create" ? "After creation, share the private join code with relatives." : mode === "join" ? "Ask your family admin for the private join code." : "Log in with your family account."}
        </div>
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
    if (!SpeechRecognition) { setSupported(false); return; }
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = "en-IN";
    recognition.onresult = (event) => {
      let text = "";
      for (let i = event.resultIndex; i < event.results.length; i++) text += event.results[i][0].transcript + " ";
      onTranscript(text);
    };
    recognitionRef.current = recognition;
  }, [onTranscript]);

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => { if (event.data.size) chunksRef.current.push(event.data); };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        onRecorded(blob);
        stream.getTracks().forEach((track) => track.stop());
      };
      recorder.start();
      recorderRef.current = recorder;
      try { recognitionRef.current?.start(); } catch {}
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
      <div><strong>{recording ? "Recording memory..." : "Audio memory"}</strong><p className="muted small">{supported ? "Speech-to-text is captured by the browser when supported. You can edit it." : "Speech recognition is not supported here. You can still record audio and type the transcript."}</p></div>
      <button type="button" className={recording ? "danger" : "secondary"} onClick={recording ? stop : start}>{recording ? "Stop recording" : "Start recording"}</button>
    </div>
  );
}

function AddMemory({ members, onSaved, onCancel }) {
  const [form, setForm] = useState({ member_id: "", title: "", memory_text: "", transcript: "" });
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
    } finally { setBusy(false); }
  };

  return (
    <section className="panel">
      <div className="panel-heading"><div><p className="eyebrow">NEW MEMORY</p><h2>Capture a family story</h2></div><button className="ghost" onClick={onCancel}>Cancel</button></div>
      <form onSubmit={submit} className="form-stack">
        <label>Who is this memory about?
          <select value={form.member_id} onChange={(e) => update("member_id", e.target.value)} required>
            <option value="">Select a family member</option>
            {members.map((member) => <option key={member.id} value={member.id}>{member.name} — {member.relationship}</option>)}
          </select>
        </label>
        <label>Memory title <span className="optional">(optional)</span><input value={form.title} onChange={(e) => update("title", e.target.value)} placeholder="A childhood memory..." /></label>
        <label>Write the memory<textarea value={form.memory_text} onChange={(e) => update("memory_text", e.target.value)} placeholder="Type the story here if you already have it in text." rows="6" /></label>
        <Recorder onRecorded={setAudio} onTranscript={(text) => update("transcript", (form.transcript ? form.transcript + " " : "") + text)} />
        <label>Transcript / spoken story<textarea value={form.transcript} onChange={(e) => update("transcript", e.target.value)} placeholder="Speech-to-text appears here. You can edit it before saving." rows="6" /></label>
        {audio && <div className="success">Audio recording ready to save.</div>}
        {error && <div className="error">{error}</div>}
        <button className="primary" disabled={busy}>{busy ? "Saving..." : "Save memory"}</button>
      </form>
    </section>
  );
}

function MemoryCard({ memory, onDelete }) {
  const token = localStorage.getItem(TOKEN_KEY);
  const audioSrc = memory.audio_url ? API + memory.audio_url + "?token=" + encodeURIComponent(token || "") : null;
  return (
    <article className="memory-card">
      <div className="memory-top"><div><p className="eyebrow">{memory.relationship}</p><h3>{memory.title}</h3><p className="muted">Memory of {memory.family_member}</p></div><button className="delete-button" onClick={() => onDelete(memory.id)}>Delete</button></div>
      {memory.summary && <div className="summary-box"><strong>Simple summary</strong><p>{memory.summary}</p></div>}
      {(memory.memory_text || memory.transcript) && <p className="memory-text">{memory.memory_text || memory.transcript}</p>}
      {memory.tags.length > 0 && <div className="tags">{memory.tags.map((tag) => <span key={tag}>#{tag}</span>)}</div>}
      {audioSrc && <audio controls src={audioSrc} className="audio-player">Your browser does not support audio playback.</audio>}
      <p className="date-text">{memory.created_at ? new Date(memory.created_at).toLocaleString() : ""}</p>
    </article>
  );
}

function Dashboard({ user, onLogout }) {
  const [family, setFamily] = useState(null);
  const [memories, setMemories] = useState([]);
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadFamily = async () => setFamily(await api("/family"));
  const loadMemories = async (query = "") => {
    setLoading(true);
    try { setMemories(await api("/memories" + (query ? "?q=" + encodeURIComponent(query) : ""))); setError(""); }
    catch (err) { setError(err.message); } finally { setLoading(false); }
  };

  useEffect(() => { Promise.all([loadFamily(), loadMemories()]).catch((err) => setError(err.message)); }, []);

  const deleteMemory = async (id) => {
    if (!window.confirm("Delete this family memory?")) return;
    try { await api("/memories/" + id, { method: "DELETE" }); setMemories((items) => items.filter((item) => item.id !== id)); }
    catch (err) { setError(err.message); }
  };

  const logout = () => { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); onLogout(); };

  if (!family) return <main className="app-shell"><p>Loading your family space...</p></main>;

  return (
    <main className="app-shell">
      <header className="topbar">
        <div><p className="eyebrow">PRIVATE FAMILY SPACE</p><h1>{family.name}</h1><p className="muted">Welcome, {user.name} • {user.role}</p></div>
        <div className="top-actions"><span className="code-badge">Join code: <strong>{family.join_code}</strong></span><button className="ghost" onClick={logout}>Log out</button></div>
      </header>
      <section className="hero">
        <div><p className="eyebrow">MEMORY BRIDGE</p><h2>Keep your family's stories alive.</h2><p className="muted">Record a story for a parent or grandparent, keep the audio, edit the transcript, and let every member of this family revisit it.</p></div>
        <button className="primary hero-button" onClick={() => setShowAdd(true)}>+ Add memory</button>
      </section>
      {showAdd ? <AddMemory members={family.members} onCancel={() => setShowAdd(false)} onSaved={(memory) => { setMemories((items) => [memory, ...items]); setShowAdd(false); }} /> : (
        <section className="panel">
          <div className="search-row"><div><p className="eyebrow">FAMILY ARCHIVE</p><h2>{memories.length} {memories.length === 1 ? "memory" : "memories"}</h2></div><input className="search-input" value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === "Enter" && loadMemories(search)} placeholder="Search family memories..." /><button className="secondary" onClick={() => loadMemories(search)}>Search</button></div>
          {error && <div className="error">{error}</div>}
          {loading ? <p className="muted">Loading memories...</p> : memories.length === 0 ? <div className="empty-state"><div className="empty-icon">♡</div><h3>No family memories yet</h3><p className="muted">Record or write your first family story.</p><button className="primary" onClick={() => setShowAdd(true)}>Add first memory</button></div> : <div className="memory-grid">{memories.map((memory) => <MemoryCard key={memory.id} memory={memory} onDelete={deleteMemory} />)}</div>}
        </section>
      )}
      <section className="panel family-panel">
        <div><p className="eyebrow">FAMILY MEMBERS</p><h2>{family.members.length} members</h2><p className="muted">Only members of this family can see this list and this family's memories.</p></div>
        <div className="member-list">{family.members.map((member) => <div className="member-item" key={member.id}><strong>{member.name}</strong><span>{member.relationship}</span></div>)}</div>
      </section>
      <footer>Memory Bridge • College project for preserving intergenerational memories.</footer>
    </main>
  );
}

function App() {
  const [user, setUser] = useState(() => { try { return JSON.parse(localStorage.getItem(USER_KEY) || "null"); } catch { return null; } });
  if (!user) return <Auth onLogin={setUser} />;
  return <Dashboard user={user} onLogout={() => setUser(null)} />;
}

createRoot(document.getElementById("root")).render(<App />);
