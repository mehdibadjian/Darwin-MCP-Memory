import re

def run(text: str) -> dict:
    """Word count, char count, sentence count, avg word length."""
    if not text or not text.strip():
        return {"words": 0, "chars": 0, "sentences": 0, "avg_word_len": 0.0}
    words = text.split()
    sentences = len(re.findall(r'[.!?]+', text)) or 1
    avg = round(sum(len(w.strip('.,!?;:')) for w in words) / len(words), 2)
    return {"words": len(words), "chars": len(text), "sentences": sentences, "avg_word_len": avg}
