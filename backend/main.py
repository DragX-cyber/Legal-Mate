from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Annotated, List, Optional
from sqlalchemy.orm import Session
from datetime import timedelta

from .models import (
    ContractAnalysisResponse, ChatRequest, ChatResponse,
    UserSignup, UserLogin, Token, ChatSessionCreate, ChatSessionResponse, ChatHistoryResponse
)
from .services.pdf_utils import extract_text_from_pdf
from .services.ai_engine import analyze_contract_with_ai, chat_with_contract
from .config import settings
from .database import get_db, init_db, User, ChatSession, ChatMessage, ContractAnalysis
from .auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="LexAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    try:
        settings.validate()
    except ValueError as e:
        print(f"Warning: {e}")
    # Initialize database
    init_db()

@app.get("/")
def read_root():
    return {"status": "LexAI API is running"}

# --- Authentication Endpoints ---
@app.post("/signup", response_model=Token)
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(new_user.id)}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name
    }

@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name
    }

@app.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name
    }

# --- Chat Session Management ---
@app.post("/chat-sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat session."""
    new_session = ChatSession(
        user_id=current_user.id,
        title=session_data.title
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return {
        "id": new_session.id,
        "title": new_session.title,
        "created_at": new_session.created_at.isoformat(),
        "updated_at": new_session.updated_at.isoformat(),
        "message_count": 0
    }

@app.get("/chat-sessions", response_model=ChatHistoryResponse)
async def get_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all chat sessions for the current user."""
    sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).order_by(ChatSession.updated_at.desc()).all()
    
    session_list = []
    for session in sessions:
        message_count = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).count()
        session_list.append({
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "message_count": message_count
        })
    
    return {"sessions": session_list}

@app.get("/chat-sessions/{session_id}/messages")
async def get_chat_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a specific chat session."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    
    return {
        "session_id": session_id,
        "title": session.title,
        "messages": [
            {"role": msg.role, "content": msg.content, "created_at": msg.created_at.isoformat()}
            for msg in messages
        ]
    }

@app.delete("/chat-sessions/{session_id}")
async def delete_chat_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a chat session."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    db.delete(session)
    db.commit()
    return {"status": "deleted"}

# --- Chat Endpoint (No auth required) ---
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Chat endpoint with user details support."""
    # Extract user details if provided
    user_details_dict = None
    if request.user_details:
        user_details_dict = request.user_details.model_dump(exclude_none=True)
    
    # Get AI response with user context
    response_text = await chat_with_contract(
        message=request.message,
        history=request.history,
        contract_context=request.contract_context,
        user_details=user_details_dict
    )
    
    return ChatResponse(response=response_text)

# --- Analysis Endpoint (No auth required) ---
@app.post("/analyze", response_model=ContractAnalysisResponse)
async def analyze_contract(
    file: UploadFile = File(...),
    industry: Annotated[str, Form()] = "General",
    risk_tolerance: Annotated[str, Form()] = "Moderate",
    role: Annotated[str, Form()] = "Client"
):
    """Analyze a contract."""
    if file.filename.endswith('.pdf'):
        contract_text = await extract_text_from_pdf(file)
    else:
        content = await file.read()
        contract_text = content.decode("utf-8")

    analysis_result = await analyze_contract_with_ai(
        text=contract_text, 
        industry=industry, 
        risk_tolerance=risk_tolerance,
        role=role
    )
    
    # Add contract text to response
    result_dict = analysis_result.model_dump()
    result_dict['contract_text'] = contract_text
    analysis_result = ContractAnalysisResponse(**result_dict)
    
    return analysis_result

@app.post("/analyze-text", response_model=ContractAnalysisResponse)
async def analyze_contract_text(
    text: Annotated[str, Form()],
    industry: Annotated[str, Form()] = "General",
    risk_tolerance: Annotated[str, Form()] = "Moderate",
    role: Annotated[str, Form()] = "Client"
):
    """Analyze raw contract text."""
    analysis_result = await analyze_contract_with_ai(
        text=text, 
        industry=industry, 
        risk_tolerance=risk_tolerance,
        role=role
    )
    
    # Add contract text to response
    result_dict = analysis_result.model_dump()
    result_dict['contract_text'] = text
    analysis_result = ContractAnalysisResponse(**result_dict)
    
    return analysis_result
