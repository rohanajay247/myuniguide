"""
Parse D2 from its Gemini OCR transcription rather than from the PDF.

D2 is a scan, so there is no font-size information to work with. The same
section/paragraph/sentence state machine applies, but markers are found by
regex instead of by size.

NOTE: RE_PAGE parses the page separator written by ocr_d2.py. The two files
share that convention with nothing enforcing it — change one and the other
silently stops finding pages and every record gets page 1.
"""

import json
import re
import yaml

RE_PAGE = re.compile(r"^=+\s*PAGE (\d+)\s*=+$")

# Two heading shapes appear in an amending statute:
#   "1. § 12 wird wie folgt geändert:"   the section being amended
#   "„§ 12a Online-Prüfungen"            the section being inserted
# The optional "n." prefix is what catches the first form. Without it, § 12
# itself is never labelled — and § 12 is the most important change D2 makes.
RE_SECTION = re.compile(r"^(?:\d{1,2}\.\s*)?„?§\s*(\d+[a-z]?)\b\s*(.*)")

RE_PARA = re.compile(r"^„?\((\d+[a-z]?)\)\s*")

# Gemini produced real superscripts on page 1 and plain digits on pages 2-6
# from the same prompt. Accept both. The lookbehind prevents matching inside
# dates (12.07.2022) and grades (1,0).
RE_MARKER = re.compile(r"(?<![\w,\.])([0-9¹²³⁴⁵⁶⁷⁸⁹])(?=[A-ZÄÖÜ][a-zäöüß])")
SUPER = str.maketrans("¹²³⁴⁵⁶⁷⁸⁹", "123456789")

# The annex table lists exam types with definitions. Page 6's row lost its
# leading pipe in transcription, so a numbered row containing a pipe counts
# too — that row is the only binding definition of Portfolioprüfung.
RE_TABLE_ROW = re.compile(r"^\d{1,2}\.\s+\S.*\|")

# Page furniture, dropped the way the running header is in the PDF parser.
FOOTER = re.compile(r"Albstadt-Sigmaringen University|^Hochschule$|^\d{1,2}$")

entry = next(e for e in yaml.safe_load(open("config/sources.yaml", encoding="utf-8"))
             if e["id"] == "D2")
table_marker = entry.get("table_marker")

records = []
state = {"section": None, "title": None, "para": None, "sentence": None}
page_no = 1
buffer = []


def flush():
    global buffer
    text = re.sub(r"\s+", " ", " ".join(buffer)).strip()
    if text:
        records.append({
            "doc": "D2",
            "programme": entry["programme"],
            "authority": entry["authority"],
            "page": page_no,
            "section": state["section"],
            "section_title": state["title"],
            "paragraph": state["para"],
            "sentence": state["sentence"],
            "text": text,
        })
    buffer = []


def strip_footer(line):
    """Remove page furniture that Gemini transcribed inline."""
    line = re.sub(r"Hochschule\s+Albstadt-Sigmaringen\s+"
                  r"Albstadt-Sigmaringen University\s*\d*", " ", line)
    return line.strip()


for raw in open(entry["ocr_source"], encoding="utf-8"):
    line = raw.strip()
    if not line:
        continue

    m = RE_PAGE.match(line)
    if m:
        page_no = int(m.group(1))
        continue

    if FOOTER.fullmatch(line):
        continue

    line = strip_footer(line)
    if not line:
        continue

    # --- annex table rows: one record each ---------------------------
    is_row = (table_marker and line.startswith(table_marker)) \
             or RE_TABLE_ROW.match(line)
    if is_row:
        flush()
        state.update(section="Anhang", title="Ausgewählte Prüfungsarten und Definitionen",
                     para=None, sentence=None)
        buffer.append(line.lstrip("| ").strip())
        flush()
        continue

    # --- section heading ---------------------------------------------
    m = RE_SECTION.match(line)
    if m:
        flush()
        state.update(section=m.group(1), title=m.group(2).strip(),
                     para=None, sentence=None)
        continue

    # --- paragraph marker ---------------------------------------------
    m = RE_PARA.match(line)
    if m:
        flush()
        state.update(para=m.group(1), sentence=None)
        line = line[m.end():]

    # --- sentence markers ---------------------------------------------
    # A marker means the previous sentence just ended, so flush before
    # updating state. Reversing these would label every sentence with the
    # following sentence's number.
    pos = 0
    for mm in RE_MARKER.finditer(line):
        chunk = line[pos:mm.start()].strip()
        if chunk:
            buffer.append(chunk)
        flush()
        state["sentence"] = mm.group(1).translate(SUPER)
        pos = mm.end()
    tail = line[pos:].strip()
    if tail:
        buffer.append(tail)

flush()

with open("data/d2_parsed.jsonl", "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

sections = sorted({r["section"] for r in records if r["section"]})
print(f"{len(records)} records -> data/d2_parsed.jsonl")
print(f"sections: {sections}")

for must in ("12", "Anhang"):
    if must not in sections:
        print(f"  WARNING: section {must} not found")