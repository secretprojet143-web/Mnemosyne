import math
import re
from collections import Counter
from typing import List, Dict, Optional, Tuple


# Common English stop words to ignore in matching
STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "about", "also", "and", "but", "or", "if", "while", "that", "this",
    "it", "its", "we", "our", "they", "them", "their", "what", "which",
    "who", "whom", "these", "those", "i", "me", "my", "you", "your",
    "he", "him", "his", "she", "her", "up", "down",
}

# Semantic synonym groups — words that mean similar things
SYNONYM_GROUPS = [
    {"fix", "debug", "diagnose", "troubleshoot", "resolve", "repair", "patch"},
    {"create", "build", "write", "add", "implement", "develop", "make"},
    {"test", "verify", "validate", "check", "confirm", "assert", "prove"},
    {"deploy", "ship", "release", "publish", "launch", "rollout"},
    {"configure", "setup", "set", "initialize", "prepare", "provision"},
    {"delete", "remove", "drop", "destroy", "clean", "purge"},
    {"auth", "login", "authentication", "authorization", "credential", "token", "jwt", "oauth"},
    {"database", "db", "sql", "postgres", "postgresql", "sqlite", "migration", "schema"},
    {"api", "endpoint", "route", "handler", "controller", "service"},
    {"error", "bug", "issue", "problem", "failure", "crash", "exception"},
    {"security", "permission", "access", "role", "privilege", "firewall"},
    {"performance", "speed", "latency", "optimization", "cache", "slow"},
    {"ui", "interface", "frontend", "design", "layout", "component", "view"},
    {"backend", "server", "service", "worker", "process"},
    {"config", "setting", "option", "parameter", "env", "environment", "variable"},
    {"monitor", "log", "track", "observe", "alert", "metric"},
    {"review", "inspect", "audit", "examine", "analyze", "evaluate"},
    {"document", "readme", "doc", "comment", "explain"},
    {"install", "update", "upgrade", "downgrade", "dependency", "package"},
    {"integrate", "connect", "link", "hook", "wire", "bridge"},
    {"backup", "restore", "recover", "snapshot", "archive"},
    {"staging", "production", "dev", "development", "local"},
    {"header", "request", "response", "payload", "body", "param"},
    {"variable", "env", "secret", "key", "credential", "token"},
]

# Build reverse lookup: word -> canonical form
_SYNONYM_MAP: Dict[str, str] = {}
for group in SYNONYM_GROUPS:
    canonical = sorted(group)[0]  # alphabetical first as canonical
    for word in group:
        _SYNONYM_MAP[word] = canonical


def _normalize(text: str) -> List[str]:
    """Extract normalized tokens from text."""
    text = text.lower()
    # Split on non-alphanumeric
    tokens = re.findall(r"[a-z0-9]+", text)
    # Remove stop words, map synonyms to canonical form
    result = []
    for token in tokens:
        if token in STOP_WORDS:
            continue
        canonical = _SYNONYM_MAP.get(token, token)
        result.append(canonical)
    return result


def _compute_tf(tokens: List[str]) -> Dict[str, float]:
    """Compute term frequency for a list of tokens."""
    counts = Counter(tokens)
    total = len(tokens) if tokens else 1
    return {word: count / total for word, count in counts.items()}


def compute_similarity(text_a: str, text_b: str) -> float:
    """Compute cosine similarity between two texts using TF-IDF-like scoring.

    Returns a float between 0.0 (no similarity) and 1.0 (identical meaning).
    """
    tokens_a = _normalize(text_a)
    tokens_b = _normalize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    tf_a = _compute_tf(tokens_a)
    tf_b = _compute_tf(tokens_b)

    # Build vocabulary
    vocab = set(tf_a.keys()) | set(tf_b.keys())

    # Compute cosine similarity
    dot_product = sum(tf_a.get(w, 0.0) * tf_b.get(w, 0.0) for w in vocab)
    norm_a = math.sqrt(sum(v ** 2 for v in tf_a.values()))
    norm_b = math.sqrt(sum(v ** 2 for v in tf_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def find_best_matches(
    query: str,
    candidates: List[Dict],
    text_key: str = "title",
    top_k: int = 3,
    threshold: float = 0.15,
) -> List[Tuple[Dict, float]]:
    """Find the most semantically similar candidates to a query.

    Args:
        query: The text to match against.
        candidates: List of dicts containing text to compare.
        text_key: Key in each candidate dict to use for comparison.
        top_k: Maximum number of results to return.
        threshold: Minimum similarity score to include.

    Returns:
        List of (candidate, similarity_score) tuples, sorted by score descending.
    """
    scored = []
    query_combined = query  # already a string

    for candidate in candidates:
        candidate_text = candidate.get(text_key, "")
        # Also include description if available for richer matching
        desc = candidate.get("description", "")
        full_text = f"{candidate_text} {desc}" if desc else candidate_text

        score = compute_similarity(query_combined, full_text)
        if score >= threshold:
            scored.append((candidate, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def compute_batch_similarity(
    query: str,
    texts: List[str],
) -> List[float]:
    """Compute similarity of a query against multiple texts at once."""
    return [compute_similarity(query, t) for t in texts]
