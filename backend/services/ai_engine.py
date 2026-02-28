import google.generativeai as genai
import json
import re
from typing import List, Optional
from ..config import settings
from ..models import ContractAnalysisResponse, ChatMessage

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

def get_analysis_prompt(text: str, industry: str, risk_tolerance: str, role: str) -> str:
    return f"""
    You are an expert Legal Risk Analyst acting as a copilot for a client in the '{industry}' industry.
    Their risk tolerance is '{risk_tolerance}'. Their role in this contract is '{role}'.

    Analyze the following contract text. Identify key clauses and assess their risk strictly based on the client's profile.
    
    CRITICAL INSTRUCTION:
    Return the output ONLY as a valid JSON object matching this structure:
    {{
        "summary": "A brief 2-sentence executive summary.",
        "overall_risk_score": (integer 0-100),
        "clauses": [
            {{
                "clause_type": "Name of clause",
                "risk_level": "High/Medium/Low",
                "text_snippet": "Exact quote from text",
                "reasoning": "Explanation relative to {industry} standards.",
                "recommendation": "Brief suggestion."
            }}
        ]
    }}

    Contract Text:
    {text[:30000]} 
    """

def _extract_text_from_response(response) -> Optional[str]:
    """Try multiple ways to pull text from the Gemini response object."""
    raw_text = getattr(response, "text", None)
    if raw_text:
        return raw_text

    candidates = getattr(getattr(response, "_result", None), "candidates", None)
    if candidates and getattr(candidates[0], "content", None):
        parts = getattr(candidates[0].content, "parts", [])
        for part in parts:
            if hasattr(part, "text"):
                return part.text
            if isinstance(part, str):
                return part
    return None


def _parse_json_fallback(raw_text: str) -> dict:
    """Try to parse JSON; if it fails, attempt to extract the first JSON object."""
    try:
        return json.loads(raw_text)
    except Exception:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


async def analyze_contract_with_ai(text: str, industry: str, risk_tolerance: str, role: str) -> ContractAnalysisResponse:
    prompt = get_analysis_prompt(text, industry, risk_tolerance, role)

    def _call_model(model_name: str) -> ContractAnalysisResponse:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)

        raw_text = _extract_text_from_response(response)
        if not raw_text:
            raise ValueError("No response text returned from model.")

        result_json = _parse_json_fallback(raw_text)
        return ContractAnalysisResponse(**result_json)

    try:
        return _call_model("gemini-2.5-flash")
    except Exception as e:
        err_msg = str(e)
        print(f"AI Error (flash): {err_msg}")
        try:
            return _call_model("gemini-1.0-pro")
        except Exception as e2:
            err_msg = str(e2)
            print(f"AI Error (fallback pro): {err_msg}")
        # Final safe fallback
        return ContractAnalysisResponse(
            summary=f"Error analyzing contract: {err_msg[:100]}... Please try again.",
            overall_risk_score=0,
            clauses=[]
        )

async def chat_with_contract(message: str, history: List[ChatMessage], contract_context: str, user_details: dict = None) -> str:
    """
    Handles follow-up questions about the contract using chat history.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Transform Pydantic history models to Gemini format
    gemini_history = []
    
    # Build user context if available
    user_context = ""
    if user_details:
        user_info = []
        if user_details.get('name'):
            user_info.append(f"Name: {user_details['name']}")
        if user_details.get('industry'):
            user_info.append(f"Industry: {user_details['industry']}")
        if user_details.get('role'):
            user_info.append(f"Role: {user_details['role']}")
        if user_details.get('risk_tolerance'):
            user_info.append(f"Risk Tolerance: {user_details['risk_tolerance']}")
        
        if user_info:
            user_context = f"\n\nUSER PROFILE:\n" + "\n".join(user_info) + "\n\nPlease personalize your responses based on this user's profile when relevant."
    
    # 1. Inject the Contract Context as the first "User" message (System Context)
    system_context = f"""
    You are an expert lawyer and legal assistant. You are capable of answering general legal questions, providing guidance on legal principles, and analyzing specific contracts.
    
    If the user asks a general legal question, answer it clearly and professionally as a lawyer would.
    If the user asks about the contract provided below, refer explicitly to its clauses and answer based on the text.
    
    Always maintain a professional, knowledgeable, and helpful tone.
    {user_context}
    
    --- 
    PROVIDED CONTRACT TEXT (if any):
    {contract_context[:30000]}
    ---
    """
    gemini_history.append({"role": "user", "parts": [system_context]})
    gemini_history.append({"role": "model", "parts": ["Understood. I am ready to provide legal guidance or analyze the contract. How can I assist you today?"]})

    # 2. Append the actual conversation history
    for msg in history:
        role = "user" if msg.role == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg.content]})

    # 3. Start the chat session
    chat = model.start_chat(history=gemini_history)
    
    try:
        response = chat.send_message(message)
        return getattr(response, "text", None) or str(response)
    except Exception as e:
        return f"Error processing chat: {str(e)}"