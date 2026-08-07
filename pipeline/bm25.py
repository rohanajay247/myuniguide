"""
BM25 keyword scoring, written from scratch.

Vector search understands meaning. Identifiers have none — "Pf", "2-010",
"12,5", "XX020" are strings, not concepts, so their embeddings drift toward
whatever the surrounding words suggest. Measured on Day 5: the query "what is
Pf" retrieved neither of the two chunks containing the string.

BM25 ignores meaning entirely and scores literal token overlap, which is
exactly the gap.

Three ideas, and that is the whole algorithm:

  1. Rare terms count more. "Pf" appears in 2 of 191 chunks, "Prüfung" in
     ~80, so a match on "Pf" is far stronger evidence. That is the IDF term.
  2. Repeats count with diminishing returns, controlled by k1.
  3. Short chunks are favoured, since a match in 50 words is stronger
     evidence than the same match in 500. That is the b term.

Run from the project root to see it work:
    python pipeline/bm25.py "what is Pf"
"""

import json
import math
import re
import sys
from collections import Counter

K1 = 1.5      # repeat saturation. Higher = repeats keep counting for longer.
B = 0.75      # length normalisation. 0 = ignore length, 1 = full correction.

# German compounds and identifiers must survive tokenisation:
#   Modul-  2-010  12,5  §  XX020
# Splitting on punctuation would destroy every one of them.
RE_TOKEN = re.compile(r"[A-Za-zÄÖÜäöüß]+|\d+[-,.]?\d*|§")


def tokenize(text):
    return [t.lower() for t in RE_TOKEN.findall(text)]


class BM25:
    def __init__(self, documents):
        """documents: list of strings, in the same order as the chunk list."""
        self.docs = [tokenize(d) for d in documents]
        self.n = len(self.docs)
        self.lengths = [len(d) for d in self.docs]
        self.avg_len = sum(self.lengths) / self.n if self.n else 0

        # How many documents contain each term.
        df = Counter()
        for doc in self.docs:
            df.update(set(doc))

        # Inverse document frequency. A term in every document scores near
        # zero; a term in two documents out of 191 scores high.
        self.idf = {
            term: math.log(1 + (self.n - count + 0.5) / (count + 0.5))
            for term, count in df.items()
        }

        self.freqs = [Counter(doc) for doc in self.docs]

    def scores(self, query):
        query_terms = tokenize(query)
        out = [0.0] * self.n

        for term in query_terms:
            idf = self.idf.get(term)
            if idf is None:
                continue                      # term appears nowhere

            for i, freq in enumerate(self.freqs):
                f = freq.get(term, 0)
                if not f:
                    continue
                # Numerator saturates as f grows; denominator penalises long
                # documents. This is the standard Okapi BM25 formulation.
                norm = 1 - B + B * self.lengths[i] / self.avg_len
                out[i] += idf * (f * (K1 + 1)) / (f + K1 * norm)

        return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    query = " ".join(sys.argv[1:])
    with open("data/index.json", encoding="utf-8") as f:
        chunks = json.load(f)

    bm25 = BM25([c["text"] for c in chunks])
    scores = bm25.scores(query)

    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    print(f"\nQ: {query}\n")
    for rank, i in enumerate(ranked[:5], 1):
        if scores[i] <= 0:
            break
        print(f"{rank}. {scores[i]:6.2f}  {chunks[i]['citation']}")
        print(f"   {chunks[i]['text'][:160]}")
        print()


if __name__ == "__main__":
    main()