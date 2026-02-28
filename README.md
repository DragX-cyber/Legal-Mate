# LegalMate

LegalMate is an AI-powered legal assistant web application that helps users analyze contracts, identify risks, and chat about legal documents in real-time.

## Features

- **Document Analysis**: Upload PDF or text-based contracts and receive an automated, structured risk assessment breaking down key clauses, risks, and recommendations.
- **Context-Aware AI Chat**: Ask follow-up questions about specific clauses in the contract and get detailed explanations securely.
- **User Authentication**: Secure JWT-based signup and login system.
- **Session Management**: Maintain and review past chat history seamlessly.
- **Customizable Profiles**: Tailor the AI's legal analysis based on user profiles, industry, role, and specific risk tolerance.

## Technology Stack

### Backend (`/backend`)
- **FastAPI**: High-performance Python web framework for building the RESTful API.
- **SQLAlchemy & SQLite**: ORM and database for managing users, sessions, and analysis history.
- **Google Generative AI (Gemini)**: Powers the contract analysis and intelligent chat functionality (using `gemini-2.5-flash`).
- **PyPDF**: Extracts text securely from uploaded PDF contracts.
- **Jose JWT & Passlib**: Manages secure token-based authentication and argon2 password hashing.

### Frontend (`/frontend1`)
- **Vanilla JavaScript & HTML5**: Lightweight, fast-loading, single-page application structure.
- **Tailwind CSS**: Utility-first CSS framework for responsive and modern UI styling.
- **Lucide Icons**: Clean, scalable icons used throughout the interface.

## Prerequisites

- Python 3.8+
- Google Gemini API Key

## Setup and Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd "Law ai"
```

### 2. Backend Setup
Navigate to the backend directory and set up a virtual environment:

```bash
cd backend
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the `backend` directory and add your Gemini API Key:

```env
GEMINI_API_KEY=your_google_gemini_api_key_here
```
*(Optionally configure `SECRET_KEY` in `auth.py` for production environments)*

### 4. Initialize the Database & Run the Server
From the `backend` folder, start the FastAPI unvicorn server:

```bash
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`. You can access the API documentation at `http://localhost:8000/docs`.

### 5. Frontend Setup
The frontend is a static web page and does not require a build step. You can run it easily with a local static server.

Navigate to the `frontend1` directory and use Python's built-in HTTP server:

```bash
cd ../frontend1
python -m http.server 5500
```
Then, open your browser and navigate to `http://localhost:5500`.

## Usage

1. **Sign Up / Log In**: Open the web application and enter credentials to start a secure session.
2. **New Chat**: Use the sidebar to start a conversation with the AI or access past chat history.
3. **Contract Review**: Click the "Scale" icon in the navigation bar to switch to the review view. Upload a legal document (PDF, DOCX, TXT) and configure your industry/role to get deeply personalized AI feedback.

## License

This is a Capstone project.

## Version Control

A comprehensive `.gitignore` has been included in the repository root to omit:
- Virtual environments (`.venv`, `env`)
- Environment variable files (`.env`)
- Local SQLite databases (`lexai.db`)
- Assorted OS-specific and editor-specific files (`.DS_Store`, `.vscode`, `__pycache__`)
