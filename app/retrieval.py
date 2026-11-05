import math
import re
from collections import Counter

STOP = {'the', 'a', 'an', 'is', 'are', 'of', 'to', 'and', 'long', 'take', 'takes', 'when', 'what', 'how', 'does', 'do', 'can', 'i', 'it', 'in', 'for', 'on', 'our', 'my', 'with', 'be', 'this', 'that', 'как', 'что', 'и', 'в', 'на'}
def tokens(text):
    terms = [t for t in re.findall(r'\w+', text.lower()) if t not in STOP]
    return [t[:-1] if t.isascii() and len(t) > 4 and t.endswith('s') and not t.endswith('ss') else t for t in terms]

def chunks(text, size=800, overlap=100):
    return [text[start:start + size] for start in range(0, len(text), size - overlap) if text[start:start + size].strip()]

def search(rows, question, limit=4):
    query = set(tokens(question))
    if not query or not rows:
        return []
    bags = [Counter(tokens(r['text'])) for r in rows]
    avg_len = sum(sum(b.values()) for b in bags) / len(bags) or 1
    df = {term: sum(term in bag for bag in bags) for term in query}
    ranked = []
    for row, bag in zip(rows, bags):
        score = 0.0
        for term in query:
            tf = bag[term]
            idf = math.log(1 + (len(rows) - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * sum(bag.values()) / avg_len))
        if score > 0:
            ranked.append({**row, 'score': round(score, 6)})
    return sorted(ranked, key=lambda r: (-r['score'], r['id']))[:limit]
