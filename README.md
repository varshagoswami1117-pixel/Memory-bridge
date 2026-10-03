# Memory Bridge

Memory Bridge is a simple family-memory web application for preserving stories, advice, experiences, and memories shared by grandparents and other family members.

The project is intentionally kept at a college-project level so that every major feature can be explained in a viva.

## Features

- Family member registration and login
- Password hashing and JWT-based authentication
- Add a memory as text
- Record audio in the browser
- Speech-to-text using the browser's Web Speech API when supported
- Edit the transcript before saving
- Store audio files on the backend
- View and play saved memories
- Simple local summary generation
- Simple keyword-based automatic tags
- Search memories
- Delete memories
- SQLite database by default
- React frontend + Flask REST API backend

## Project structure

```
Memory-bridge/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── .env.example
│   └── uploads/
├── frontend/
│   ├── index.html
│   ├── package.json
│   └── src/
│       ├── main.jsx
│       └── styles.css
├── docs/
│   └── VIVA_NOTES.md
├── .gitignore
└── README.md
```

## Run the backend

Python 3.10+ is recommended.

```bash
cd backend
python -m venv venv
```

Windows:

```bash
venv\\Scripts\\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start Flask:

```bash
python app.py
```

The API runs at `http://127.0.0.1:5000`.

## Run the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL shown by Vite, normally `http://localhost:5173`.

## Speech-to-text note

Speech recognition is handled by the browser through the Web Speech API. Browser support varies, so the application also allows the user to type or edit the transcript manually. This avoids pretending that a paid AI API is being used.

## AI note

The current project does not use OpenAI, Gemini, or another external generative-AI API.

The small summary and tagging functions are local text-processing features. They are deliberately simple and easy to explain:
- Summary: takes the first useful part of the memory text.
- Tags: checks the text for common family-memory keywords.

Generative AI tools may have been used during development as coding assistants, but the application itself does not claim an external GenAI model.

## Suggested viva explanation

"Memory Bridge is a web application that helps families preserve memories shared by older family members. A family member can log in, record or type a memory, save the audio and transcript, and later search and replay it. I used React for the frontend, Flask and SQLAlchemy for the backend, and SQLite for storage. Speech-to-text uses the browser's speech recognition capability, while the summary and tags are simple local text-processing features."

## Important

Uploaded audio files are stored in `backend/uploads/` during local development. The uploads folder is ignored by Git so personal audio is not accidentally committed to GitHub.
