# Memory Bridge

Memory Bridge is a college-level family-memory web application for preserving stories, advice, experiences and memories shared across generations.

## Core idea

**One family = one private family database.**

1. One person creates a family and becomes its admin.
2. Memory Bridge creates a private SQLite database file for that family.
3. The admin receives an 8-character family join code.
4. Other relatives join using that code and create their own login accounts.
5. Every member of that family can see the family's members and memories.
6. A member can record a memory on behalf of a parent or grandparent who may not use technology.
7. Audio is stored on the backend and the browser can provide a speech-to-text transcript when supported.
8. Simple local text processing creates a short summary and keyword tags.
9. A family can search, read, listen to and delete its memories.

The backend decides the family from the authenticated account. The frontend never chooses a database filename or family database directly.

## Privacy / isolation design

There is a small master database:

- backend/memory_bridge_master.db — family registry and login/account mapping.

Each family also gets its own database:

- backend/databases/family_<FAMILY_ID>.db

A family database contains that family's:

- members
- memories
- transcripts
- summary/tag data
- memory metadata

When a user logs in, the JWT contains the user's identity and family context. Protected endpoints look up the authenticated user, obtain their family ID, and open only that family's database.

For example, if Family A requests /api/memories/5, the server searches memory 5 only inside Family A's database. Family B cannot use its token to read Family A's database.

## Features

- Create a private family
- Join an existing family using a join code
- Login with email and password
- Password hashing
- JWT authentication
- Family member list
- Add text memories
- Record audio in the browser
- Browser speech-to-text when supported
- Edit transcript before saving
- Store and replay audio
- Simple local summary generation
- Simple keyword-based tags
- Search family memories
- Delete family memories
- React frontend + Flask backend
- SQLite storage
- No OpenAI, Gemini or paid GenAI API required

## Project structure

~~~
Memory-bridge/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── memory_bridge_master.db       # created locally; ignored by Git
│   ├── databases/                    # family DBs; ignored by Git
│   └── uploads/                      # audio; ignored by Git
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
~~~

## Run the backend

Python 3.10+ is recommended.

Windows:

~~~powershell
cd backend
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
~~~

If PowerShell blocks npm scripts, use npm.cmd instead.

The API runs at http://127.0.0.1:5000.

## Run the frontend

Open a second terminal:

~~~powershell
cd frontend
npm.cmd install
npm.cmd run dev
~~~

Open the local Vite URL, normally http://localhost:5173.

## Test the family workflow

### Family A
1. Choose Create family.
2. Enter a family name, your name, relationship, email and password.
3. Copy the generated join code.
4. Add a memory.
5. Notice that the memory appears in the family archive.

### Family A member
1. Open the app in another browser/incognito window.
2. Choose Join family.
3. Enter the Family A join code and create another account.
4. The same family member list and memories should be visible.

### Family B isolation test
1. Create a completely different family with a different account.
2. Add a memory.
3. Confirm that Family B sees only Family B's memories.
4. Log back into Family A and confirm Family B's memory is not present.

## Speech-to-text note

Speech recognition is handled by the browser through the Web Speech API. Browser support varies, so the application also lets the user type or edit the transcript manually.

## AI note

The application does **not** claim to use a generative-AI model.

The summary and tags are deliberately simple local text processing:

- Summary: takes the first useful part of the transcript/text.
- Tags: checks for common family-memory keywords.

This keeps the project understandable in a BCA viva.

## Suggested viva explanation

> “Memory Bridge is a family-memory web application. One family member creates a private family space and receives a join code. Other relatives join that same family. The backend creates a separate SQLite database for each family, so family memories are isolated. A member can record a memory for a parent or grandparent, store the audio, use browser speech-to-text when supported, edit the transcript, and later search, read or play the memory. I used React for the frontend, Flask for the REST API, SQLite for storage, password hashing for account security and JWT for authentication. The summary and tags are simple local text processing rather than a fake external AI API.”
