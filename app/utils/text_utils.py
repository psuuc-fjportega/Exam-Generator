import re
from difflib import SequenceMatcher

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "than", "that", "this",
    "these", "those", "is", "are", "was", "were", "be", "been", "being", "to",
    "of", "in", "on", "for", "with", "as", "by", "at", "from", "it", "its",
    "into", "about", "which", "what", "when", "where", "who", "how", "not",
    "no", "yes", "true", "false", "can", "could", "should", "would", "may",
    "might", "do", "does", "did", "have", "has", "had", "you", "your", "we",
}

_WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def normalize_text(value: str) -> str:
    collapsed = re.sub(r"\s+", " ", (value or "").strip().lower())
    return collapsed


def tokenize(value: str) -> list[str]:
    return [match.group(0).lower() for match in _WORD_RE.finditer(value or "")]


def significant_terms(value: str) -> set[str]:
    return {token for token in tokenize(value) if len(token) > 3 and token not in _STOPWORDS}


def overlap_ratio(left: str, right: str) -> float:
    left_terms = significant_terms(left)
    right_terms = significant_terms(right)
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / len(left_terms)


def similarity_ratio(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def is_near_duplicate(left: str, right: str, threshold: float = 0.86) -> bool:
    return similarity_ratio(left, right) >= threshold
