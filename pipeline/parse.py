"""
Parse the corpus PDFs into addressable records.

Each record is one sentence (or one page, for documents without legal
structure) tagged with its document, section, paragraph and sentence number —
enough to cite it as e.g. "D1 § 16 Abs. 1 Satz 2".

Thresholds are derived per document rather than hardcoded: body size is the
most common font size, and sentence markers are anything meaningfully smaller.
Per-document facts (heading pattern, layout, whether sentence markers exist)
live in config/sources.yaml, not here.

Run from the project root:
    python pipeline/parse.py            # all documents
    python pipeline/parse.py D1 D3      # named documents only
"""

import json
import re
import sys
from collections import Counter

import fitz
import yaml

RE_PARA = re.compile(r"^\((\d+[a-z]?)\)")

MARKER_RATIO = 0.80    # a sentence marker is < 80% of body size
NOISE_RATIO = 0.95     # smaller than body but not a marker => running header
MARGIN_X = 100         # headings start at the left margin


def body_size(doc):
    """The most common font size in the document — i.e. the body text."""
    counts = Counter()
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if span["text"].strip():
                        counts[round(span["size"], 1)] += 1
    return counts.most_common(1)[0][0]


def page_lines(page, body, want_markers):
    """Rebuild logical lines from spans, tagging sentence markers.

    Justified text scatters one sentence across many spans, so spans have to
    be regrouped by line before anything else makes sense.
    """
    out = []
    for block in page.get_text("dict")["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            parts = []
            for span in line["spans"]:
                text, size, x = span["text"], span["size"], span["bbox"][0]
                if not text.strip():
                    continue
                if size < body * MARKER_RATIO:
                    if want_markers and text.strip().isdigit():
                        parts.append(("MARKER", text.strip(), x))
                    continue
                if size < body * NOISE_RATIO:
                    continue                      # running header / footer
                parts.append(("TEXT", text, x))
            if parts:
                out.append(parts)
    return out


def is_contents(lines):
    """A contents page is dense with section references and thin on prose."""
    joined = " ".join(t for parts in lines for kind, t, x in parts if kind == "TEXT")
    return len(re.findall(r"§\s*\d+", joined)) > 8 and len(joined) < 2500


def base_record(entry, page_no, state, text):
    return {
        "doc": entry["id"],
        "programme": entry["programme"],
        "authority": entry["authority"],
        "page": page_no,
        "section": state["section"],
        "section_title": state["title"],
        "paragraph": state["para"],
        "sentence": state["sentence"],
        "text": text,
    }


def parse_sections(entry, doc):
    """Parse a document with § structure into one record per sentence."""
    body = body_size(doc)
    want_markers = entry.get("sentence_markers", True)
    re_section = re.compile(entry["heading_pattern"])

    records = []
    state = {"section": None, "title": None, "para": None, "sentence": None}
    buffer = []
    page_no = 1

    def flush():
        nonlocal buffer
        text = re.sub(r"\s+", " ", " ".join(buffer)).strip()
        if text:
            records.append(base_record(entry, page_no, state, text))
        buffer = []

    for page_no in range(1, doc.page_count + 1):
        lines = page_lines(doc[page_no - 1], body, want_markers)

        if is_contents(lines):
            print(f"  page {page_no}: contents, skipped")
            continue

        for parts in lines:
            joined = " ".join(t for kind, t, x in parts if kind == "TEXT").strip()
            left = parts[0][2]

            # --- section heading ---------------------------------------
            # search() rather than match(), because a heading can follow a
            # label on the same line. The margin guard is what stops a
            # mid-sentence cross-reference being read as a heading.
            m = re_section.search(joined)
            if m and left < MARGIN_X:
                flush()
                if m.lastindex == 1:
                    state.update(section=m.group(1), title=m.group(1))
                else:
                    state.update(section=m.group(1), title=(m.group(2) or "").strip())
                state.update(para=None, sentence=None)
                continue

            # --- paragraph marker --------------------------------------
            m = RE_PARA.match(joined)
            if m:
                flush()
                state.update(para=m.group(1), sentence=None)
                rest = joined[m.end():].strip()
                if rest:
                    buffer.append(rest)
                for kind, t, x in parts:
                    if kind == "MARKER":
                        flush()
                        state["sentence"] = t
                continue

            # --- body text ---------------------------------------------
            # A marker means the PREVIOUS sentence just ended, so flush
            # before updating state. Reversing these two lines would label
            # every sentence with the following sentence's number.
            for kind, t, x in parts:
                if kind == "MARKER":
                    flush()
                    state["sentence"] = t
                else:
                    buffer.append(t)

    flush()
    return records, body


def parse_pages(entry, doc):
    """One record per page, for documents with no § structure.

    Used for D4, the module handbook. It is descriptive rather than binding
    and loses every conflict against the statutes, so page-level granularity
    is sufficient. Documented as a deliberate limitation.
    """
    body = body_size(doc)
    records = []
    state = {"section": None, "title": None, "para": None, "sentence": None}

    for page_no in range(1, doc.page_count + 1):
        lines = page_lines(doc[page_no - 1], body, False)
        text = " ".join(
            t for parts in lines for kind, t, x in parts if kind == "TEXT"
        )
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            records.append(base_record(entry, page_no, state, text))

    return records, body


def main():
    sources = yaml.safe_load(open("config/sources.yaml", encoding="utf-8"))
    wanted = sys.argv[1:] or [e["id"] for e in sources if e.get("text_layer") == "native"]

    for entry in sources:
        if entry["id"] not in wanted:
            continue

        print(f"{entry['id']} ({entry['filename']})")
        doc = fitz.open(f"data/raw/{entry['filename']}")

        if entry.get("layout") == "pages":
            records, body = parse_pages(entry, doc)
        else:
            records, body = parse_sections(entry, doc)

        # A record count below the page count almost always means the
        # structure was not recognised. D4 once produced 1 record from 26
        # pages and reported success.
        if len(records) < doc.page_count:
            print(f"  WARNING: {len(records)} records from {doc.page_count} pages")

        out = f"data/{entry['id'].lower()}_parsed.jsonl"
        with open(out, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        print(f"  body size {body} · {len(records)} records -> {out}\n")


if __name__ == "__main__":
    main()