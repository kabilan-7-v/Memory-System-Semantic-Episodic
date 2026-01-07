import numpy as np
from datetime import datetime, timezone
from embeddings import EmbeddingModel
from bm25_index import BM25Index
from db import get_conn

embedder = EmbeddingModel()

class HybridRetriever:
    def __init__(self):
        self.bm25 = BM25Index()
        self.episodes = []

    def load(self, user_id, deepdive_id=None):
        with get_conn() as conn, conn.cursor() as cur:
            if deepdive_id:
                cur.execute("""
                    SELECT * FROM episodes
                    WHERE source_type='deepdive' AND source_id=%s AND vector IS NOT NULL
                """, (deepdive_id,))
            else:
                cur.execute("""
                    SELECT * FROM episodes
                    WHERE user_id=%s AND vector IS NOT NULL
                """, (user_id,))
            self.episodes = cur.fetchall()

        self.bm25 = BM25Index()
        for ep in self.episodes:
            text = " ".join(m["content"] for m in ep["messages"])
            self.bm25.add(text)

        print(f"📚 Loaded {len(self.episodes)} episodes for retrieval.")

    def search(self, query, k=3):
        qvec = embedder.encode(query)
        bm25_scores = self.bm25.search(query)

        # Get top k by vector similarity using pgvector
        with get_conn() as conn, conn.cursor() as cur:
            if self.episodes:
                episode_ids = [ep['id'] for ep in self.episodes]
                cur.execute("""
                    SELECT id, vector <=> %s::vector AS distance
                    FROM episodes
                    WHERE id = ANY(%s)
                    ORDER BY vector <=> %s::vector
                    LIMIT %s
                """, (qvec.tolist(), episode_ids, qvec.tolist(), k))
                vector_results = cur.fetchall()
            else:
                vector_results = []

        now = datetime.utcnow()
        scored = []

        for res in vector_results:
            ep_id = res['id']
            vector_distance = res['distance']
            vector_score = 1 - vector_distance  # cosine similarity = 1 - distance

            # Find the episode
            ep = next(ep for ep in self.episodes if ep['id'] == ep_id)
            i = self.episodes.index(ep)
            bm25_score = float(bm25_scores[i]) if i < len(bm25_scores) else 0.0

            age_days = (now - ep["created_at"]).days
            recency = max(0.0, 1 - age_days / 30)

            score = 0.6 * vector_score + 0.3 * bm25_score + 0.1 * recency
            scored.append((score, ep, vector_score, bm25_score))

        scored.sort(reverse=True, key=lambda x: x[0])
        print(f"🏆 Top {min(k, len(scored))} episode scores: {[round(s, 3) for s, _, _, _ in scored[:k]]}")
        results = []
        for score, ep, vector_score, bm25_score in scored[:k]:
            results.append({
                'episode': ep,
                'total_score': score,
                'vector_score': vector_score,
                'bm25_score': bm25_score,
            })
        return results