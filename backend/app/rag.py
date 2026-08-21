import os
from typing import Optional

from fastapi import UploadFile
from pypdf import PdfReader


def extract_text_from_pdf(file: UploadFile) -> str:
    """Extract readable text from an uploaded PDF."""
    reader = PdfReader(file.file)

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""

        if text.strip():
            pages.append(text.strip())

    return "\n\n".join(pages)


def get_answer_from_text(text: str, question: str) -> str:
    """
    Temporary RAG-style search.
    AI integration will be added in the next step.
    """

    if not text.strip():
        return "PDF me readable text nahi mila."

    question_words = {
        word.lower()
        for word in question.split()
        if len(word) > 2
    }

    paragraphs = text.split("\n\n")

    matches = []

    for paragraph in paragraphs:
        score = sum(
            1
            for word in question_words
            if word in paragraph.lower()
        )

        if score > 0:
            matches.append((score, paragraph.strip()))

    matches.sort(reverse=True, key=lambda item: item[0])

    if not matches:
        return "Is PDF me is question se related information nahi mili."

    return "\n\n".join(
        paragraph
        for _, paragraph in matches[:3]
    )
