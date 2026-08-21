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
    """Detect English, Hindi or Hinglish."""

    q = question.lower().strip()

    hindi_words = {
        "क्या", "क्यों", "कैसे", "बताओ", "बताइए",
        "कहानी", "का", "की", "के", "में", "है",
        "मुझे", "और", "से", "यह"
    }

    hinglish_words = {
        "kya", "kyu", "kyon", "kaise", "btao", "batao",
        "bta", "story", "iska", "iski", "iske",
        "me", "mein", "hai", "mujhe", "or",
        "aur", "krke", "wala", "wali"
    }

    # Hindi script
    has_hindi = any(
        word in q for word in hindi_words
    )

    # Roman words
    words = set(re.findall(r"\b[a-zA-Z]+\b", q))

    has_hinglish = bool(words.intersection(hinglish_words))

    if has_hindi and has_hinglish:
        return "hinglish"

    if has_hindi:
        return "hindi"

    if has_hinglish:
        return "hinglish"

    return "english"


def find_relevant_context(
    text: str,
    question: str,
    max_chunks: int = 6
) -> str:
    """
    Find the most relevant PDF sections.

    Important:
    Common question words like what/how/why are ignored.
    Actual topic words such as stack, queue, tree etc.
    receive much higher importance.
    """

    # Convert question into useful words
    question_words = [
        word.lower()
        for word in re.findall(r"\b[a-zA-Z0-9]+\b", question)
        if len(word) > 2
    ]

    # Words that should NOT be used for matching
    stop_words = {
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "how",
        "does",
        "did",
        "the",
        "is",
        "are",
        "was",
        "were",
        "this",
        "that",
        "tell",
        "give",
        "explain",
        "please",
        "about",
        "can",
        "you",
        "me",
        "for",
        "from",
        "with",
        "and",
        "or"
    }

    useful_words = [
        word for word in question_words
        if word not in stop_words
    ]

    # Split PDF into paragraphs
    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n", text)
        if p.strip()
    ]

    scored = []

    for paragraph in paragraphs:

        paragraph_lower = paragraph.lower()

        paragraph_words = set(
            word.lower()
            for word in re.findall(
                r"\b[a-zA-Z0-9]+\b",
                paragraph
            )
        )

        score = 0

        # Strong match for actual question/topic words
        for word in useful_words:

            if word in paragraph_words:
                score += 10

            # Exact phrase/substring match
            if word in paragraph_lower:
                score += 5

        # Extra boost for definition questions
        definition_words = {
            "define",
            "definition",
            "meaning",
            "what"
        }

        if any(
            word in question.lower()
            for word in definition_words
        ):

            definition_patterns = [
                " is ",
                " are ",
                "defined as",
                "refers to",
                "means",
                "called"
            ]

            if any(
                pattern in paragraph_lower
                for pattern in definition_patterns
            ):
                score += 5

        if score > 0:
            scored.append((score, paragraph))

    # Highest relevance first
    scored.sort(
        key=lambda item: item[0],
        reverse=True
    )

    # If relevant context found
    if scored:

        selected = [
            paragraph
            for _, paragraph in scored[:max_chunks]
        ]

        return "\n\n".join(selected)[:12000]

    # If nothing matches, send limited PDF context
    return text[:12000]


def get_answer_from_text(
    text: str,
    question: str
) -> str:
    """
    Generate a focused answer from the uploaded PDF
    using Gemini AI.
    """

    if not text.strip():
        return "PDF me readable text nahi mila."

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return (
            "AI service is not configured. "
            "Please add GEMINI_API_KEY in Render."
        )

    language = detect_language(question)

    context = find_relevant_context(
        text,
        question
    )

    language_instruction = {
        "english": (
            "Answer only in English."
        ),
        "hindi": (
            "Answer only in Hindi using Devanagari script."
        ),
        "hinglish": (
            "Answer in natural Hinglish using "
            "Roman English letters."
        )
    }[language]

    prompt = f"""
You are StudyRAG-AI, a PDF question-answering assistant.

Your job is to answer ONLY the user's question
using the provided PDF context.

STRICT RULES:

1. Use ONLY information available in the PDF context.
2. Answer the exact question asked.
3. Do NOT answer a different question.
4. Do NOT retell the whole PDF.
5. Do NOT include unrelated stories.
6. Do NOT include unrelated paragraphs.
7. Do NOT repeat the PDF title unless necessary.
8. Keep the answer short and focused.
9. If the user asks a definition, give the definition only.
10. If the user asks "What is X?", explain ONLY X.
11. If the user asks for a moral, give ONLY the moral.
12. If the user asks for a summary, summarize ONLY the requested content.
13. If the answer cannot be found in the provided PDF context,
    clearly say that the information is not available in the PDF.
14. Never invent information from your own knowledge.
15. Match the user's language:
    {language_instruction}

IMPORTANT:
The context below may contain multiple unrelated sections.
You MUST select only the information relevant to the user's
exact question.

PDF CONTEXT:
-------------------------
{context}
-------------------------

USER QUESTION:
{question}

Return ONLY the final answer.
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
                    "temperature": 0.1,
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

        candidates = data.get("candidates", [])

        if not candidates:
            return "AI ne koi answer generate nahi kiya."

        answer = (
            candidates[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )

        if not answer:
            return "AI ne koi answer generate nahi kiya."

        return answer

    except Exception as error:

        return (
            f"AI answer generate nahi ho paya: "
            f"{str(error)}"
)
