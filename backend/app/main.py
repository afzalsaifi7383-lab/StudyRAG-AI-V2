from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from backend.app.rag import extract_text_from_pdf, get_answer_from_text

app = FastAPI(title="StudyRAG-AI")

document_text = ""


class QuestionRequest(BaseModel):
    question: str


@app.get("/")
def home():
    return {
        "status": "success",
        "message": "StudyRAG-AI is running!"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    global document_text

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    document_text = extract_text_from_pdf(file)

    if not document_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not extract readable text from PDF."
        )

    return {
        "status": "success",
        "message": "PDF uploaded successfully!",
        "filename": file.filename,
        "characters": len(document_text)
    }


@app.post("/ask")
def ask_question(request: QuestionRequest):
    if not document_text:
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF first."
        )

    answer = get_answer_from_text(
        document_text,
        request.question
    )

    return {
        "status": "success",
        "question": request.question,
        "answer": answer
    }
