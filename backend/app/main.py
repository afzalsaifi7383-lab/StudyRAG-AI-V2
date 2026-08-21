from fastapi import FastAPI

app = FastAPI(title="StudyRAG-AI")


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
