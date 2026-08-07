"""
Search the chunk index by meaning.

The question is embedded the same way the chunks were, then compared against
every chunk with one matrix multiplication. Because every vector was
normalised to length 1 at index time, cosine similarity reduces to a dot
product — so the whole search is `index @ query`.

Run from the project root:
    python pipeline/search.py "how long do I have to write my thesis"
    python pipeline/search.py "wie lange habe ich für die Master-Thesis"
"""

import json
import os
import sys

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = "gemini-embedding-001"
DIMS = 768
TOP_K = 5

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


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


def search(question, matrix, chunks, top_k=TOP_K, programme="iai"):
    query = embed_query(question)

    # One matrix multiplication: (191, 768) @ (768,) -> (191,) scores.
    scores = matrix @ query

    # Keep chunks that apply to this programme. D1 and D2 are tagged "all"
    # because they govern every Master's programme; D3 and D4 are "iai".
    # Setting a filtered score to -1 removes it without reindexing.
    for i, chunk in enumerate(chunks):
        if chunk["programme"] not in ("all", programme):
            scores[i] = -1.0

    order = np.argsort(scores)[::-1][:top_k]
    return [(float(scores[i]), chunks[i]) for i in order]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    question = " ".join(sys.argv[1:])
    matrix, chunks = load_index()

    print(f"\nQ: {question}\n")
    for rank, (score, chunk) in enumerate(search(question, matrix, chunks), 1):
        flag = "" if chunk["authority"] == "binding" else "  [descriptive]"
        print(f"{rank}. {score:.3f}  {chunk['citation']}{flag}")
        print(f"   {chunk['text'][:220]}")
        print()


if __name__ == "__main__":
    main()