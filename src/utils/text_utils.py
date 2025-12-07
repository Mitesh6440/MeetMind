"""
Shared text normalization utilities.
"""
import re
from typing import List


def normalize_text(text: str) -> str:
    """
    Normalize text for matching: lowercase, collapse whitespace, strip.
    
    Used across multiple services for consistent text processing.
    """
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """
    Extract meaningful keywords from text, filtering out common words.
    
    Args:
        text: Input text
        min_length: Minimum keyword length
        
    Returns:
        List of keywords
    """
    # Common stop words to filter
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "should", "could", "may", "might", "must", "can", "this",
        "that", "these", "those", "it", "its", "we", "you", "they", "he", "she"
    }
    
    words = re.findall(r"\b\w+\b", text.lower())
    keywords = [w for w in words if len(w) >= min_length and w not in stop_words]
    return keywords

