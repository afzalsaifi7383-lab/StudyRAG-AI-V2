from typing import Optional
from fastapi import UploadFile
from pypdf import PdfReader
import re


def extract_text_from_pdf(file: UploadFile) -> str:
    """Extract readable text from an uploaded PDF."""
    reader = PdfReader(file.file)

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""

        if text.strip():
            pages.append(text.strip())

    return "\n\n".join(pages)


def detect_language(question: str) -> str:
    """
    Detect the language/style of the question.
    Returns: english, hindi, or hinglish
    """

    q = question.lower().strip()

    # Common Hindi words written in English
    hinglish_words = [
        "kya", "hai", "hain", "ka", "ki", "ke",
        "btao", "batao", "mujhe", "mera", "meri",
        "isko", "iska", "iske", "kyu", "kyun",
        "kaise", "kesi", "wala", "wali", "mein",
        "me", "aur", "or", "se", "ko", "krna",
        "karo", "chahiye", "chiye"
    ]

    hindi_words = [
        "क्या", "है", "हैं", "का", "की", "के",
        "मुझे", "बताओ", "इसका", "इसके", "क्यों",
        "कैसे", "और", "में", "से", "को"
    ]

    if any(word in q.split() for word in hinglish_words):
        return "hinglish"

    if any(word in q for word in hindi_words):
        return "hindi"

    return "english"


def clean_text(text: str) -> str:
    """Clean unnecessary spaces and line breaks."""

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def find_relevant_content(text: str, question: str) -> str:
    """
    Find the most relevant part of the PDF.
    Unlike the old version, it does NOT return 3 complete paragraphs.
    """

    question_lower = question.lower()

    # Split document into paragraphs
    paragraphs = [
        clean_text(p)
        for p in re.split(r"\n\s*\n", text)
        if clean_text(p)
    ]

    if not paragraphs:
        return ""

    # Words from question
    question_words = {
        word.lower()
        for word in re.findall(r"[a-zA-Z\u0900-\u097F]+", question)
        if len(word) > 2
    }

    scored = []

    for paragraph in paragraphs:

        paragraph_lower = paragraph.lower()

        score = 0

        # Normal keyword matching
        for word in question_words:
            if word in paragraph_lower:
                score += 1

        # Special handling for moral / lesson questions
        if any(x in question_lower for x in [
            "moral",
            "lesson",
            "message",
            "seekh",
            "sikh",
            "sabak"
        ]):

            if any(x in paragraph_lower for x in [
                "moral",
                "lesson",
                "honest",
                "truth",
                "truthfulness",
                "reward",
                "honesty",
                "greed"
            ]):
                score += 5

        if score > 0:
            scored.append((score, paragraph))

    if not scored:
        return ""

    scored.sort(reverse=True, key=lambda x: x[0])

    # Return ONLY the best matching paragraph
    return scored[0][1]


def make_concise_answer(content: str, question: str) -> str:
    """
    Create a short answer from the relevant PDF content.
    """

    if not content:
        return ""

    question_lower = question.lower()

    # Moral / lesson question
    if any(x in question_lower for x in [
        "moral",
        "lesson",
        "message",
        "seekh",
        "sabak"
    ]):

        sentences = re.split(r"(?<=[.!?])\s+", content)

        useful = []

        for sentence in sentences:

            s = sentence.lower()

            if any(word in s for word in [
                "moral",
                "lesson",
                "honest",
                "honesty",
                "truth",
                "truthful",
                "greed",
                "reward",
                "good",
                "kind"
            ]):
                useful.append(sentence.strip())

        if useful:
            return " ".join(useful[:2])

    # For normal questions, give maximum 2 relevant sentences
    sentences = re.split(r"(?<=[.!?])\s+", content)

    sentences = [
        s.strip()
        for s in sentences
        if s.strip()
    ]

    return " ".join(sentences[:2])


def get_answer_from_text(text: str, question: str) -> str:
    """
    Main RAG answer function.
    """

    if not text.strip():
        return "The PDF text could not be read."

    language = detect_language(question)

    relevant_content = find_relevant_content(
        text,
        question
    )

    if not relevant_content:
        if language == "hinglish":
            return "Is PDF mein is question se related information nahi mili."

        if language == "hindi":
            return "इस PDF में इस प्रश्न से संबंधित जानकारी नहीं मिली।"

        return "I could not find information related to this question in the PDF."

    answer = make_concise_answer(
        relevant_content,
        question
    )

    # Fallback
    if not answer:
        answer = relevant_content

    return answer
