# Memory Bridge - Viva Notes

## 1. What is Memory Bridge?

Memory Bridge is a family-memory application. It helps preserve stories, advice, experiences and memories shared by grandparents or other family members.

## 2. Why did you make it?

Older family members may have valuable memories that are not written down. The application gives the family a simple way to record and preserve them so that other members can listen to or read them later.

## 3. How does the system work?

1. A family member creates an account or logs in.
2. They enter the name and relationship of the person sharing the memory.
3. They can type a memory or record audio.
4. The browser can convert speech into a transcript using Web Speech API when supported.
5. The transcript can be edited before saving.
6. Flask stores the memory information in SQLite and the audio file in the uploads folder.
7. The backend creates a short local summary and simple keyword tags.
8. The dashboard shows saved memories and allows search and audio playback.

## 4. Why React?

React makes it easier to build a responsive interface using reusable components such as login, dashboard, recorder and memory cards.

## 5. Why Flask?

Flask is lightweight and easy to understand for a college project. It provides REST API endpoints for authentication and memory operations.

## 6. Why SQLite?

SQLite is simple for local development because it does not require a separate database server. The same SQLAlchemy models can later be connected to another relational database.

## 7. What is JWT?

JWT is a token used to identify the logged-in user when the frontend sends requests to protected backend endpoints.

## 8. How is the password stored?

The password is never stored as plain text. Flask/Werkzeug stores a password hash, and login checks the entered password against that hash.

## 9. Is this Generative AI?

No external Generative AI model is integrated into the current application.

The summary and tags are local text-processing features:
- The summary takes the first useful part of the memory.
- Tags are selected by checking for predefined keywords.

If asked about AI tools used during development, explain that AI tools were used as development assistants for understanding code, debugging and improving structure. Do not claim that an external GenAI API is running inside the application.

## 10. What is the hardest part?

The important practical part is connecting the complete flow: React form -> HTTP request -> Flask API -> authentication -> database/file storage -> response -> React dashboard.

## 11. What would you improve later?

Possible future improvements are:
- Better speech-to-text with a dedicated model/API
- Stronger AI summarization
- More advanced search
- Cloud storage for audio
- Family-level sharing and permissions
- Deployment on a public server
