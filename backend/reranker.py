import os
from pathlib import Path
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util

load_dotenv(Path(__file__).parent / ".env")

MODEL_NAME = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small")
SAME_T = float(os.getenv("SAME_THRESHOLD", "0.88"))
RELATED_T = float(os.getenv("RELATED_THRESHOLD", "0.82"))

_model = None


def _get_model():
    global _model
    if _model is None:
        print(f"  loading embedding model {MODEL_NAME} ...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def candidate_text(c):
    title = (c.get("title") or "").strip()
    claim = (c.get("claim") or "").strip()[:300]
    return f"{title}. {claim}".strip(". ")


def score_candidates(claim, candidates):
    model = _get_model()
    # e5 models expect a "query: " prefix on both sides for similarity tasks
    texts = ["query: " + claim] + ["query: " + candidate_text(c) for c in candidates]
    emb = model.encode(texts, normalize_embeddings=True)
    return util.cos_sim(emb[0], emb[1:])[0].tolist()


def judge_embedding(claim, candidates):
    sims = score_candidates(claim, candidates)
    verdicts = {}
    for i, s in enumerate(sims):
        candidates[i]["score"] = round(s, 3)
        if s >= SAME_T:
            verdicts[i] = "same"
        elif s >= RELATED_T:
            verdicts[i] = "related"
        else:
            verdicts[i] = "unrelated"
    return verdicts