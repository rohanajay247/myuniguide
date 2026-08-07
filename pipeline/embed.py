"""
Embed the chunks and build the search index.

Each chunk's text goes to Gemini's embedding model and comes back as 768
numbers representing its meaning. Chunks with similar meaning produce similar
vectors, which is what lets an English question match German text without any
translation step.

Output:
    data/index.npy    float32 array, one normalised row per chunk
    data/index.json   chunk metadata in the same row order

Embeddings are cached by a hash of the text, so re-running after editing one
chunk only re-embeds that chunk.

Run from the project root:
    python pipeline/embed.py
"""

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = "gemini-embedding-001"
DIMS = 768
BATCH = 20
CACHE = Path("data/embed_cache.json")

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def text_hash(text):
    """Cache key. Changing the text changes the hash, so it re-embeds."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_cache():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def embed_batch(texts, task_type):
    """One API call for a batch of texts."""
    response = client.models.embed_content(
        model=MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=DIMS,
        ),
    )
    return [e.values for e in response.embeddings]


def normalise(matrix):
    """Scale every row to length 1.

    gemini-embedding-001 only returns normalised vectors at the default 3072
    dimensions; truncated output must be normalised manually.

    Once every vector has length 1, cosine similarity is just a dot product,
    so search becomes one matrix multiplication instead of a division per row.
    """
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def main():
    chunks = [json.loads(line) for line in
              open("data/chunks.jsonl", encoding="utf-8") if line.strip()]
    print(f"{len(chunks)} chunks")

    cache = load_cache()
    todo = [c for c in chunks if text_hash(c["text"]) not in cache]
    print(f"{len(cache)} cached, {len(todo)} to embed")

    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        # RETRIEVAL_DOCUMENT, not RETRIEVAL_QUERY. The model places a question
        # near the documents that answer it, which is an asymmetric
        # relationship — using the same task type for both degrades retrieval
        # quietly rather than visibly.
        vectors = embed_batch([c["text"] for c in batch], "RETRIEVAL_DOCUMENT")
        for chunk, vector in zip(batch, vectors):
            cache[text_hash(chunk["text"])] = vector
        print(f"  embedded {i + len(batch)}/{len(todo)}")
        time.sleep(1)

    CACHE.write_text(json.dumps(cache), encoding="utf-8")

    matrix = np.array([cache[text_hash(c["text"])] for c in chunks],
                      dtype=np.float32)
    print(f"\nmatrix: {matrix.shape}")

    matrix = normalise(matrix)
    np.save("data/index.npy", matrix)

    # Metadata in the same row order. Row i of the matrix describes chunk i
    # of this list — nothing enforces that, so never reorder one alone.
    with open("data/index.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)

    # A normalised vector has length 1. If this is not 1.0, normalisation
    # failed and every similarity score will be wrong.
    lengths = np.linalg.norm(matrix, axis=1)
    print(f"row lengths: min {lengths.min():.4f}, max {lengths.max():.4f}")
    if not np.allclose(lengths, 1.0, atol=1e-4):
        print("  WARNING: rows are not unit length")

    print(f"\nsaved data/index.npy and data/index.json")
    print(f"index size: {matrix.nbytes / 1024:.0f} KB")


if __name__ == "__main__":
    main()