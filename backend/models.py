from pydantic import BaseModel, Field
from typing import List, Optional

# --- Input Models ---
class AnalysisRequest(BaseModel):
    industry: str = Field(..., description="User's industry (e.g., SaaS, Construction)")
    risk_tolerance: str = Field(..., description="User's risk tolerance (Low, Moderate, High)")
    role: str = Field(..., description="User's role (e.g., Vendor, Client)")

class ChatMessage(BaseModel):
    role: str = Field(..., description="user or model")
    content: str

class UserDetails(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    role: Optional[str] = None
    risk_tolerance: Optional[str] = None
    email: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    contract_context: str = Field(..., description="The full text of the contract being discussed")
    user_details: Optional[UserDetails] = None

# --- Output Models (Structured AI Response) ---
class ClauseAnalysis(BaseModel):
    clause_type: str = Field(..., description="Type of clause (e.g., Indemnification)")
    risk_level: str = Field(..., description="High, Medium, or Low")
    text_snippet: str = Field(..., description="The exact text from the contract")
    reasoning: str = Field(..., description="Why this is risky based on the profile")
    recommendation: Optional[str] = Field(None, description="Suggested change")

class ContractAnalysisResponse(BaseModel):
    summary: str
    overall_risk_score: int = Field(..., ge=0, le=100)
    clauses: List[ClauseAnalysis]
    contract_text: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: Optional[int] = None

# --- Authentication Models ---
class UserSignup(BaseModel):
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    email: str
    full_name: str

class ChatSessionCreate(BaseModel):
    title: str

class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str
    message_count: int

class ChatHistoryResponse(BaseModel):
    sessions: List[ChatSessionResponse]