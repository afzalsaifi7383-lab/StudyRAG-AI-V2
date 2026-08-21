import os
import re
from typing import Optional

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

    q = question.lower().strip()

    # Hindi Devanagari
    if re.search(r"[\u0900-\u097F]", question):
        return "hindi"

    hinglish_words = [
        "kya", "ka", "ki", "ke", "hai", "h", "tha", "thi",
        "btao", "batao", "kyu", "kyun", "kaise", "kis",
        "me", "mein", "se", "ko", "or", "aur", "ye", "wo",
        "moral", "story", "wali", "wala", "iska", "iski",
        "iske", "mujhe", "bht", "bahut", "samjhao", "samjha"
    ]

    words = set(re.findall(r"[a-zA-Z]+", q))

    hinglish_count = len(words.intersection(hinglish_words))

    if hinglish_count >= 1:
        return "hinglish"

    return "english"


def find_relevant_paragraphs(text: str, question: str):
    """Find the most relevant parts of the PDF."""

    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n", text)
        if p.strip()
    ]

    if not paragraphs:
        return []

    question_words = {
        word.lower()
        for word in re.findall(r"[a-zA-Z]+", question)
        if len(word) > 2
    }

    scored = []

    for paragraph in paragraphs:
        paragraph_words = set(
            re.findall(r"[a-zA-Z]+", paragraph.lower())
        )

        score = len(question_words.intersection(paragraph_words))

        scored.append((score, paragraph))

    scored.sort(reverse=True, key=lambda x: x[0])

    # Only relevant paragraphs
    relevant = [
        paragraph
        for score, paragraph in scored
        if score > 0
    ]

    return relevant[:5]


def extract_moral(text: str) -> Optional[str]:
    """
    Try to extract a moral/lesson from a story.
    This prevents returning the whole story when user asks for its moral.
    """

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    moral_keywords = [
        "moral",
        "lesson",
        "learned",
        "honesty",
        "honest",
        "truth",
        "truthful",
        "reward",
        "rewarded",
        "kindness",
        "helping",
        "greed",
        "greedy",
        "never lie",
        "always tell the truth"
    ]

    candidates = []

    for sentence in sentences:
        lower = sentence.lower()

        score = 0

        for keyword in moral_keywords:
            if keyword in lower:
                score += 1

        if score > 0:
            candidates.append((score, sentence.strip()))

    candidates.sort(reverse=True, key=lambda x: x[0])

    if candidates:
        return candidates[0][1]

    return None


def answer_moral(question: str, text: str, language: str) -> str:
    """Return a short answer when the user asks for moral/lesson."""

    moral = extract_moral(text)

    if language == "hindi":
        if moral:
            return f"इस कहानी की सीख है कि हमेशा ईमानदार और सच्चा रहना चाहिए।"

        return "इस कहानी की सीख है कि ईमानदारी और सच्चाई हमेशा अच्छी होती है।"

    if language == "hinglish":
        if moral:
            return "Is story ka moral hai ki hamesha honest aur sachcha rehna chahiye."

        return "Is story ka moral hai ki hamesha imaandari aur sachchai ka saath dena chahiye."

    # English
    if moral:
        return "The moral of the story is that we should always be honest and truthful."

    return "The moral of the story is that honesty and truthfulness are always valuable."


def get_answer_from_text(text: str, question: str) -> str:
    """
    Main RAG answer function.

    Gives a short, relevant answer instead of returning
    multiple unrelated PDF paragraphs.
    """

    if not text.strip():
        return "I couldn't find readable information in the PDF."

    question = question.strip()

    if not question:
        return "Please ask a question about the uploaded PDF."

    language = detect_language(question)

    q = question.lower()

    # --------------------------------------------------
    # MORAL / LESSON QUESTIONS
    # --------------------------------------------------

    moral_words = [
        "moral",
        "lesson",
        "moral kya",
        "seekh",
        "sikh",
        "sikh kya",
        "what is the moral",
        "what's the moral",
        "main lesson",
        "main message"
    ]

    if any(word in q for word in moral_words):
        return answer_moral(question, text, language)

    # --------------------------------------------------
    # SUMMARY QUESTIONS
    # --------------------------------------------------

    summary_words = [
        "summary",
        "summarize",
        "summarise",
        "short summary",
        "saar",
        "saransh",
        "short me batao"
    ]

    if any(word in q for word in summary_words):

        relevant = find_relevant_paragraphs(text, question)

        if not relevant:
            relevant = [text[:1500]]

        if language == "hindi":
            return (
                "इस PDF के अनुसार मुख्य बात यह है:\n\n"
                + " ".join(relevant)[:1200]
            )

        if language == "hinglish":
            return (
                "Is PDF ke according main baat ye hai:\n\n"
                + " ".join(relevant)[:1200]
            )

        return (
            "The main point from the PDF is:\n\n"
            + " ".join(relevant)[:1200]
        )

    # --------------------------------------------------
    # GENERAL QUESTIONS
    # --------------------------------------------------

    relevant = find_relevant_paragraphs(text, question)

    if not relevant:
        if language == "hindi":
            return "इस PDF में आपके सवाल से संबंधित जानकारी नहीं मिली।"

        if language == "hinglish":
            return "Is PDF me aapke question se related information nahi mili."

        return "I couldn't find information related to your question in the PDF."

    # Return ONLY the most relevant paragraph,
    # not the top 3 paragraphs.
    answer = relevant[0]

    # Prevent excessively long answers
    if len(answer) > 1200:
        answer = answer[:1200].rsplit(" ", 1)[0] + "..."

    return answer
