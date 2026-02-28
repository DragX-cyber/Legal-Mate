from pypdf import PdfReader
import io
from fastapi import UploadFile, HTTPException

async def extract_text_from_pdf(file: UploadFile) -> str:
    """
    Reads a PDF file upload and returns the raw text content.
    """
    try:
        # Read file content into memory
        content = await file.read()
        pdf_file = io.BytesIO(content)
        
        reader = PdfReader(pdf_file)
        text = ""
        
        # Iterate through pages
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
                
        if not text.strip():
            raise ValueError("No text could be extracted. The PDF might be an image scan.")
            
        return text

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading PDF: {str(e)}")