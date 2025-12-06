from __future__ import annotations

from typing import List
import re

from models.nlp import PreprocessedSentence
from services.stt_service import TranscriptResult


# --- 1. Normalization helpers -------------------------------------------------


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines into a single space."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def basic_cleanup(text: str) -> str:
    """
    Basic clean up:
    - remove extra spaces
    - normalize quotes
    - remove stray brackets often coming from STT
    """
    text = text.replace("“", '"').replace("”", '"').replace("’", "'")
    text = normalize_whitespace(text)
    return text


# --- 2. Sentence segmentation -------------------------------------------------


def split_into_sentences(text: str) -> List[str]:
    """
    Simple regex-based sentence segmentation.
    Not perfect, but good enough for meeting transcripts.

    Splits on: '.', '?', '!' (with some handling for multiple dots).
    """
    text = basic_cleanup(text)

    # Add a space after sentence-end punctuation if missing
    text = re.sub(r"([.?!])([^\s])", r"\1 \2", text)

    # Split on punctuation marks treated as sentence boundaries
    raw_sentences = re.split(r"[.?!]+", text)

    sentences = [s.strip() for s in raw_sentences if s.strip()]
    return sentences


# --- 3. Tokenization ----------------------------------------------------------


def tokenize(text: str) -> List[str]:
    """
    Very simple tokenizer:
    - lowercase
    - split on spaces & punctuation
    """
    text = text.lower()
    # Replace common punctuation with spaces
    text = re.sub(r"[,\-:;\"'()/\\]", " ", text)
    # Collapse whitespace and split
    text = normalize_whitespace(text)
    return text.split(" ")


# --- 4. Filler word removal & normalization -----------------------------------


# You can expand this list as you see patterns in your meetings.
FILLER_WORDS = {
    # English fillers
    "um", "uh", "like", "you know", "actually", "basically", "literally",
    "so", "well", "okay", "ok",
    # Hindi/Gujarati-ish fillers 
    "matlab", "toh", "accha", "haan", "na", "ke", "jo", "tho",
}

def remove_filler_words(tokens: List[str]) -> List[str]:
    """
    Remove simple filler words from token list.
    Note: this is naive and may remove legit words if list is too aggressive.
    """
    return [t for t in tokens if t not in FILLER_WORDS]


def reconstruct_text_from_tokens(tokens: List[str]) -> str:
    """
    Join tokens back into text after cleaning.
    """
    return " ".join(tokens).strip()


# --- 5. High-level preprocessing on transcript -------------------------------


def preprocess_transcript(transcript: TranscriptResult) -> List[PreprocessedSentence]:
    """
    Main entry point for text preprocessing.

    Steps:
    1. Take full transcript text
    2. Split into sentences
    3. For each sentence:
       - tokenize
       - remove filler words
       - normalize and reconstruct cleaned sentence
    4. Return list of PreprocessedSentence objects
    """
    sentences = split_into_sentences(transcript.text)

    preprocessed: List[PreprocessedSentence] = []

    for idx, sent in enumerate(sentences, start=1):
        raw = sent
        tokens = tokenize(raw)
        tokens_no_filler = remove_filler_words(tokens)
        cleaned = reconstruct_text_from_tokens(tokens_no_filler)

        # Skip empty sentences after cleaning
        if not cleaned:
            continue

        preprocessed.append(
            PreprocessedSentence(
                id=idx,
                raw_text=raw,
                cleaned_text=cleaned,
                tokens=tokens_no_filler,
            )
        )

    return preprocessed
