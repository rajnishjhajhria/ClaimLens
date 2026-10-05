"""Order results by how close each fact-check is to the user's claim (multilingual embedding similarity).

Works the same whichever judge is used, so the first result shown is the closest one, not just the newest.
Adds a "rank_score" to each candidate. If the embedding model is unavailable, the old order is kept.
"""
import os

MODEL_NAME = os.getenv("RANK_MODEL", "intfloat/multilingual-e5-small")
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _text(c):
    return "query: " + f"{c.get('title') or ''}. {c.get('claim') or ''}".strip()[:400]


def add_rank_scores(claim, candidates):
    """Set candidate["rank_score"] (cosine similarity to the claim) on each candidate. Returns True if it worked."""
    if not candidates:
        return True
    try:
        model = _get_model()
        vecs = model.encode(["query: " + claim] + [_text(c) for c in candidates], normalize_embeddings=True)
        sims = vecs[1:] @ vecs[0]
        for c, s in zip(candidates, sims):
            c["rank_score"] = round(float(s), 4)
        return True
    except Exception as e:
        print("  ranking by similarity failed, keeping the old order:", e)
        return False


def sort_key(c):
    return (c.get("rank_score") if c.get("rank_score") is not None else (c.get("score") or 0), c.get("date") or "")