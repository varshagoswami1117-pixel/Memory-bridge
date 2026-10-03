# Memory Bridge - Viva Notes

## 1. What is Memory Bridge?

Memory Bridge is a family-memory application that preserves stories, advice, experiences and memories shared by grandparents and other family members.

## 2. What is the main idea?

One family gets one private family database.

- One person creates the family and becomes admin.
- The backend creates a separate SQLite database for that family.
- The admin receives an 8-character join code.
- Other relatives join using that code.
- Members of the same family can access that family's memories.
- A family cannot access another family's memory database.

## 3. How does the system work?

1. A person creates a family.
2. The backend creates the family record and a private SQLite family database.
3. The creator becomes the family admin and receives a join code.
4. Other relatives use the join code to create accounts in the same family.
5. A logged-in member opens the family dashboard.
6. The member selects who the memory is about, such as a grandparent.
7. The member can type the story or record audio.
8. The browser can convert speech into a transcript using the Web Speech API when supported.
9. The transcript can be edited before saving.
10. The backend stores the memory in the current family's database and the audio file in the uploads folder.
11. The backend creates a short local summary and keyword tags.
12. All members of that family can later search, read and play the memory.

## 4. Why separate databases?

The project requirement is to keep family data isolated.

The server generates the database filename. Users do not choose a filename.

For example:

- Family A -> family_A1B2C3D4E5F6.db
- Family B -> family_7G8H9J0K1L2M.db

The exact IDs are generated automatically.

The authenticated user determines which family database the backend opens. This prevents a user from simply changing a family ID in the browser to access another family's data.

## 5. What is the master database?

The master database is a small registry. It stores:

- family ID
- family name
- join code
- database filename
- user login/account information
- the family ID belonging to each user

The family database stores the family's members and memories.

## 6. Why React?

React makes it easier to build a responsive interface using reusable components such as authentication, dashboard, recorder and memory cards.

## 7. Why Flask?

Flask is lightweight and easy to understand for a college project. It provides REST API endpoints for family creation, joining, authentication and memory operations.

## 8. Why SQLite?

SQLite is simple for local development because it does not require a separate database server. In this project it also makes the one-family-one-database idea easy to demonstrate.

## 9. What is JWT?

JWT is a token used to identify the logged-in user when the frontend sends requests to protected backend endpoints.

The backend uses the authenticated user to determine the user's family. The client does not choose which family database to open.

## 10. How is the password stored?

The password is never stored as plain text. Werkzeug stores a password hash, and login checks the entered password against that hash.

## 11. Is this Generative AI?

No external Generative AI model is integrated into the current application.

The summary and tags are local text-processing features:

- Summary: takes the first useful part of the memory.
- Tags: checks the text for predefined keywords.

Do not claim that OpenAI or Gemini is running inside the application.

## 12. How can a grandparent use it if they do not know technology?

Another family member can log in, select the grandparent as the person the memory is about, and record the grandparent's story using the microphone.

The grandparent does not need to manage an account just to have their story preserved.

## 13. How do you prove family isolation in a demo?

Create Family A and add a memory.

Then create Family B with another account and add a different memory.

Family A should show only Family A's memory.

Family B should show only Family B's memory.

The backend does not accept an arbitrary family database filename from the frontend.

## 14. What is the hardest part?

The important practical part is connecting the complete flow:

React form -> HTTP request -> Flask API -> JWT authentication -> family lookup -> family database -> response -> React dashboard.

## 15. What would you improve later?

Possible future improvements are:

- Dedicated speech-to-text service
- Better AI summarization
- More advanced search
- Cloud storage for audio
- Fine-grained family permissions
- Email invitations
- Deployment on a public server
- Automated backups
