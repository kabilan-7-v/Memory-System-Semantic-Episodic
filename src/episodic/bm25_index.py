import re
from rank_bm25 import BM25Okapi

def tokenize(text):
    return re.findall(r"\w+", text.lower())

class BM25Index:
    def __init__(self):
        self.docs = []
        self.raw = []
        self.bm25 = None

    def add(self, text):
        tokens = tokenize(text)
        if not tokens:
            return
        self.docs.append(tokens)
        self.raw.append(text)
        self.bm25 = BM25Okapi(self.docs)

    def search(self, query):
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(tokenize(query))
        return scores