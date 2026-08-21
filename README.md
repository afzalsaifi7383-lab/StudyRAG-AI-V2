# StudyRAG-AI Frontend

This is a simple, deployable frontend for the existing StudyRAG-AI FastAPI backend.

Backend currently configured:
https://studyrag-ai-v2.onrender.com

Endpoints used:
- POST /upload-pdf
- POST /ask

## Run locally

You can open index.html with VS Code Live Server.

For deployment, upload this folder to GitHub and deploy it as a static site on Vercel, Netlify, or GitHub Pages.

## Important: CORS

The FastAPI backend must allow requests from the frontend domain.

Add this to your FastAPI backend after `app = FastAPI(...)`:

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

For production, replace `["*"]` with your exact frontend URL.

Then push the backend change to GitHub. Render will auto-deploy.

## If your /upload-pdf response does not contain `characters`

The frontend already works without it; it will simply show a blank character count.
