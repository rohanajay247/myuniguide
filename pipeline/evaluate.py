"""
Run the full evaluation set through the system and record the results.

Produces data/eval_run.csv — eval.csv plus what the system actually did, ready
for manual scoring against the rules in docs/notes.md.

Two things are recorded that manual reading alone would miss:

  retrieved     the citations of the top 5 chunks
  recall_hit    whether any retrieved chunk matches the expected source

recall_hit is the single most useful column. If accuracy is low and recall is
high, the prompt is at fault. If recall is low, retrieval is. Without it you
are guessing at which half of the pipeline to fix.

Run from the project root:
    python pipeline/evaluate.py
    python pipeline/evaluate.py 5      # first 5 only, for a smoke test
"""

import csv
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from answer import answer
from search import load_index

IN = "eval.csv"
# OUT = "data/eval_run.csv"
# OUT = "data/eval_hybrid_k5.csv"
# OUT = "data/eval_hybrid_weighted.csv"
OUT =  "data/eval_dense_v3.csv"

RE_OUTCOME = re.compile(r"^\s*(ANSWER|DECLINE|CONFLICT)\b", re.I)


def outcome_of(text):
    """The system is instructed to begin with the response type in capitals."""
    m = RE_OUTCOME.match(text or "")
    return m.group(1).lower() if m else "unparsed"


def recall_hit(row, results):
    """Did retrieval surface a chunk from the expected provision?

    Checks the section, not just the document. Matching on document ID alone
    over-reports badly — "D3 retrieved" counted as a hit even when the wrong
    provision within D3 came back, which would have made retrieval look fine
    and pointed Day 8 at the prompt instead.
    """
    expected = row["source_doc"].strip()
    if not expected or expected == "-":
        return ""                       # decline rows have no expected source

    wanted_docs = {d.strip() for d in expected.split("/")}
    wanted_secs = set(re.findall(r"§\s*(\d+[a-z]?)", row.get("section", "")))

    for score, chunk in results:
        if chunk["doc"] not in wanted_docs:
            continue
        if not wanted_secs:
            return "yes"                # no section specified, doc match is enough
        if str(chunk.get("section")) in wanted_secs:
            return "yes"
    return "no"


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    with open(IN, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if limit:
        rows = rows[:limit]

    matrix, chunks = load_index()
    print(f"{len(rows)} questions\n")

    out_rows = []
    for i, row in enumerate(rows, 1):
        text, results = answer(row["question"], matrix, chunks)

        got = outcome_of(text)
        expected = row["outcome"].strip()
        match = "MATCH" if got == expected else f"got {got}"

        out_rows.append({
            **row,
            "actual_outcome": got,
            "actual_answer": (text or "").replace("\n", " ").strip(),
            "retrieved": " | ".join(c["citation"] for s, c in results),
            "top_score": f"{results[0][0]:.3f}",
            "recall_hit": recall_hit(row, results),
            "correct": "",              # filled in by hand
            "failure_note": "",
        })

        print(f"{i:3}. {row['id']}  expected {expected:9} {match}")
        time.sleep(1)

    fields = list(out_rows[0].keys())
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"\n{len(out_rows)} rows -> {OUT}")

    # Outcome-type agreement is not accuracy — a response can be the right
    # type and still be wrong on substance or citation. It is a first look
    # before the manual scoring pass.
    agree = sum(1 for r in out_rows if r["actual_outcome"] == r["outcome"].strip())
    print(f"outcome type matched: {agree}/{len(out_rows)}")

    checked = [r for r in out_rows if r["recall_hit"]]
    hits = sum(1 for r in checked if r["recall_hit"] == "yes")
    if checked:
        print(f"recall (source doc in top 5): {hits}/{len(checked)}")

    print("\nNow score the `correct` column by hand against docs/notes.md.")


if __name__ == "__main__":
    main()