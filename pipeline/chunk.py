"""
Merge the parsed record files into one chunk file for embedding.

Records are one sentence each, which is too fine for retrieval — a lone
sentence often lacks the subject it refers to. Sentences are therefore
grouped by paragraph, with the sentence range kept in the citation.

Run from the project root:
    python pipeline/chunk.py
"""

import json
from pathlib import Path

INPUTS = [
    "data/d1_parsed.jsonl",
    "data/d2_parsed.jsonl",
    "data/d3_parsed.jsonl",
    "data/d4_parsed.jsonl",
    "data/d3_studyplan.jsonl",
]
OUT = "data/chunks.jsonl"

MIN_CHARS = 40          # below this a chunk carries no usable information


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def group_key(r):
    """Records sharing this key belong in the same chunk."""
    return (r["doc"], r.get("section"), r.get("paragraph"), r.get("page"))


def citation(doc, section, paragraph, sentences):
    parts = [doc]
    if section:
        parts.append(f"§ {section}" if section.isdigit() or section[0].isdigit()
                     else section)
    if paragraph:
        parts.append(f"Abs. {paragraph}")
    nums = [s for s in sentences if s]
    if nums:
        parts.append(f"Satz {nums[0]}" if len(nums) == 1
                     else f"Sätze {nums[0]}–{nums[-1]}")
    return " ".join(parts)


chunks = []
seq = 0

for path in INPUTS:
    if not Path(path).exists():
        print(f"  missing: {path}")
        continue

    records = load(path)

    # Study plan rows are already complete statements — one chunk each.
    if "studyplan" in path:
        for r in records:
            seq += 1
            chunks.append({
                "id": f"C{seq:04d}",
                "doc": r["doc"],
                "programme": r["programme"],
                "authority": r["authority"],
                "page": r["page"],
                "section": r["section"],
                "section_title": r["section_title"],
                "paragraph": None,
                "sentences": None,
                "citation": f"{r['doc']} study plan, module {r['module_code']}",
                "text": r["text"],
                "module_code": r["module_code"],
            })
        print(f"  {path}: {len(records)} rows -> {len(records)} chunks")
        continue

    # Everything else groups consecutive records sharing doc/section/paragraph.
    made = 0
    buf = []
    key = None

    def emit():
        global seq, made, buf
        if not buf:
            return
        text = " ".join(r["text"] for r in buf).strip()
        if len(text) >= MIN_CHARS:
            first = buf[0]
            seq += 1
            made += 1
            chunks.append({
                "id": f"C{seq:04d}",
                "doc": first["doc"],
                "programme": first["programme"],
                "authority": first["authority"],
                "page": first["page"],
                "section": first["section"],
                "section_title": first["section_title"],
                "paragraph": first["paragraph"],
                "sentences": [r["sentence"] for r in buf if r["sentence"]] or None,
                "citation": citation(first["doc"], first["section"],
                                     first["paragraph"],
                                     [r["sentence"] for r in buf]),
                "text": text,
            })
        buf = []

    for r in records:
        k = group_key(r)
        if k != key:
            emit()
            key = k
        buf.append(r)
    emit()

    print(f"  {path}: {len(records)} records -> {made} chunks")

with open(OUT, "w", encoding="utf-8") as f:
    for c in chunks:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

lengths = [len(c["text"]) for c in chunks]
print(f"\n{len(chunks)} chunks -> {OUT}")
print(f"chars: min {min(lengths)}, median {sorted(lengths)[len(lengths)//2]}, "
      f"max {max(lengths)}")