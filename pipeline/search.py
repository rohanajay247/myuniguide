"""
Search the chunk index — dense, sparse, or both.

Dense (vector) search understands meaning and works across languages. Sparse
(BM25) search matches literal tokens and works on identifiers. Measured on this
corpus, they fail in opposite directions:

    query                        dense              sparse
    "what is Pf"                 0 of 3 chunks      3 of 3 chunks
    "2-020"                      —                  exact, 6.77 vs 1.92
    "how long for my thesis"     correct, 0.742     no relevant result

Neither is sufficient alone, which is the case for fusing them.

Run from the project root:
    python pipeline/search.py "how long do I have to write my thesis"
    python pipeline/search.py --dense "wie lange habe ich fuer die Master-Thesis"
"""

import json
import os
import sys

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bm25 import BM25

load_dotenv()

MODEL = "gemini-embedding-001"
DIMS = 768
TOP_K = 5
RRF_K = 60          # rank-fusion constant; 60 is the value from the original paper

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

_bm25 = None        # built once, on first hybrid call


def load_index():
    matrix = np.load("data/index.npy")
    with open("data/index.json", encoding="utf-8") as f:
        chunks = json.load(f)
    # Row i of the matrix describes chunks[i]. Nothing enforces this, so a
    # mismatch would return the wrong text for the right row, silently.
    assert matrix.shape[0] == len(chunks), "index.npy and index.json disagree"
    return matrix, chunks


def embed_query(text):
    """Embed a question.

    RETRIEVAL_QUERY, not RETRIEVAL_DOCUMENT. The model places a question near
    the documents that answer it, which is asymmetric — a question and its
    answer rarely share vocabulary. Using the document task type here degrades
    retrieval without any visible error.
    """
    response = client.models.embed_content(
        model=MODEL,
        contents=[text],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=DIMS,
        ),
    )
    vector = np.array(response.embeddings[0].values, dtype=np.float32)
    return vector / np.linalg.norm(vector)


def _ranks(scores):
    """Map each index to its rank, best first."""
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return {i: rank for rank, i in enumerate(order)}


def search(question, matrix, chunks, top_k=TOP_K, programme="iai"):
    """Dense retrieval only. Kept so the hybrid gain can be measured."""
    query = embed_query(question)

    # One matrix multiplication: (191, 768) @ (768,) -> (191,) scores.
    scores = matrix @ query

    for i, chunk in enumerate(chunks):
        if chunk["programme"] not in ("all", programme):
            scores[i] = -1.0

    order = np.argsort(scores)[::-1][:top_k]
    return [(float(scores[i]), chunks[i]) for i in order]


def hybrid(question, matrix, chunks, top_k=TOP_K, programme="iai"):
    """Reciprocal Rank Fusion of dense and sparse retrieval.

    Fusion uses ranks, not raw scores. Cosine similarity sits around 0.6-0.75
    while BM25 ranges from 0 to roughly 20 — adding those directly would let
    BM25 dominate arbitrarily. Ranks are comparable; raw scores are not.

    A chunk both systems rank highly wins. A chunk one system loves and the
    other ignores still surfaces, which is the point: dense carries "how long
    for my thesis", sparse carries "what is Pf".
    """
    global _bm25
    if _bm25 is None:
        _bm25 = BM25([c["text"] for c in chunks])

    dense = matrix @ embed_query(question)
    sparse = _bm25.scores(question)

    dense_rank = _ranks(dense)
    sparse_rank = _ranks(sparse)

    fused = []
    for i, chunk in enumerate(chunks):
        if chunk["programme"] not in ("all", programme):
            continue
        # score = 1 / (RRF_K + dense_rank[i]) + 1 / (RRF_K + sparse_rank[i])
        score = 1 / (RRF_K + dense_rank[i]) + 0.25 / (RRF_K + sparse_rank[i])
        fused.append((score, i))

    fused.sort(key=lambda pair: pair[0], reverse=True)
    return [(score, chunks[i]) for score, i in fused[:top_k]]


def main():
    args = sys.argv[1:]
    dense_only = "--dense" in args
    if dense_only:
        args.remove("--dense")
    if not args:
        print(__doc__)
        raise SystemExit(1)

    question = " ".join(args)
    matrix, chunks = load_index()

    fn = search if dense_only else hybrid
    print(f"\nQ: {question}   [{'dense' if dense_only else 'hybrid'}]\n")

    for rank, (score, chunk) in enumerate(fn(question, matrix, chunks), 1):
        flag = "" if chunk["authority"] == "binding" else "  [descriptive]"
        print(f"{rank}. {score:.4f}  {chunk['citation']}{flag}")
        print(f"   {chunk['text'][:200]}")
        print()


if __name__ == "__main__":
    main()