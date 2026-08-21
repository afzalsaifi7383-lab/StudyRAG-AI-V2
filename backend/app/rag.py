import os
import re
import requests
from fastapi import UploadFile
from pypdf import PdfReader


def extract_text_from_pdf(file: UploadFile) -> str:
    """Extract readable text from uploaded PDF."""
    reader = PdfReader(file.file)

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""

        if text.strip():
            pages.append(text.strip())

    return "\n\n".join(pages)


def detect_language(question: str) -> str:
    """Detect whether the user is asking in English, Hindi or Hinglish."""

    q = question.lower()

    hindi_words = [
        "क्या", "क्यों", "कैसे", "बताओ", "बताइए",
        "कहानी", "का", "की", "के", "में", "है",
        "मुझे", "और", "से", "यह"
    ]

    hinglish_words = [
        "kya", "kyu", "kyon", "kaise", "btao", "batao",
        "bta", "story", "iska", "iski", "iske",
        "me", "mein", "hai", "h", "mujhe", "or",
        "aur", "btao", "krke", "wala", "wali"
    ]

    if any(word in q for word in hindi_words):
        if any(word in q for word in hinglish_words):
            return "hinglish"
        return "hindi"

    if any(word in q for word in hinglish_words):
        return "hinglish"

    return "english"


def find_relevant_context(text: str, question: str, max_chunks: int = 5) -> str:
    """Find only the most relevant parts of the PDF."""

    question_words = set(
        word.lower()
        for word in re.findall(r"\b[a-zA-Z0-9]+\b", question)
        if len(word) > 2
    )

    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n", text)
        if p.strip()
    ]

    scored = []

    for paragraph in paragraphs:

        paragraph_words = set(
            word.lower()
            for word in re.findall(r"\b[a-zA-Z0-9]+\b", paragraph)
        )

        score = len(question_words.intersection(paragraph_words))

        # Give extra importance to important question words
        important_words = [
            "moral",
            "lesson",
            "meaning",
            "summary",
            "main",
            "why",
            "how",
            "what"
        ]

        for word in important_words:
            if word in question.lower() and word in paragraph.lower():
                score += 3

        if score > 0:
            scored.append((score, paragraph))

    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        return text[:12000]

    return "\n\n".join(
        paragraph for _, paragraph in scored[:max_chunks]
    )[:12000]


def get_answer_from_text(text: str, question: str) -> str:
    """
    Generate a short answer from the uploaded PDF
    using Gemini AI.
    """

    if not text.strip():
        return "PDF me readable text nahi mila."

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return "AI service is not configured. Please add GEMINI_API_KEY in Render."

    language = detect_language(question)

    context = find_relevant_context(text, question)

    language_instruction = {
        "english": "Answer only in English.",
        "hindi": "Answer only in Hindi using Devanagari script.",
        "hinglish": "Answer in natural Hinglish using Roman English letters."
    }[language]

    prompt = f"""
You are StudyRAG-AI, a PDF question-answering assistant.

Your job is to answer ONLY what the user asked.

STRICT RULES:

1. Use ONLY the information available in the provided PDF context.
2. Do NOT retell the whole story.
3. Do NOT include unrelated stories or paragraphs.
4. Do NOT repeat the PDF title unless it is necessary.
5. Give a direct and natural answer.
6. Keep the answer short and focused.
7. If the user asks for 2 lines, give approximately 2 lines.
8. If the user asks for a moral, give only the moral.
9. If the user asks for a definition, give only the definition.
10. If the answer is not available in the PDF, clearly say that it is not available.
11. Match the user's language exactly:
   {language_instruction}
12. Never start with phrases like:
   "According to the PDF..."
   "The PDF says..."
   "Five Short Stories..."
   unless the user specifically asks about the PDF.
13. Never add information from your own knowledge.

PDF CONTEXT:
----------------
{context}
----------------

USER QUESTION:
{question}

Now give ONLY the final answer.
"""

    try:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            "models/gemini-2.5-flash:generateContent"
            f"?key={api_key}"
        )

        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json"
            },
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 300
                }
            },
            timeout=60
        )

        data = response.json()

        if not response.ok:
            raise Exception(
                data.get("error", {}).get(
                    "message",
                    "Gemini request failed."
                )
            )

        answer = (
            data["candidates"][0]["content"]["parts"][0]["text"]
            .strip()
        )

        return answer

    except Exception as error:
        return f"AI answer generate nahi ho paya: {str(error)}"
