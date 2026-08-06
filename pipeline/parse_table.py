"""
Extract D3's study and examination plan as structured rows.

Flat text extraction destroys the column alignment on this page. Empty cells
produce inconsistent blank counts, long module names wrap onto a second line,
and the first row merges its code and name — so the distance from a module
code to its ECTS value is 8, 8, 9, 10, 8 across five consecutive rows. Any
code that locates a value by counting will read the wrong column for some
rows and raise no error.

find_tables() uses cell coordinates instead, which sidesteps all of it.

Known limitation: vertically merged cells collapse into the first row of each
block, so column 2 shows 'CM CM CM CEM' on row 4 and nothing on rows 5-7. The
columns that matter — code, name, semester, ECTS, examination type, language —
come through clean on every row.

Run from the project root:
    python pipeline/parse_table.py
"""

import json
import re

import fitz

PDF = "data/raw/IAI_StuPO-specialPart_20250228_Ausfertigung.pdf"
PAGE = 5                      # zero-indexed: printed page 6
OUT = "data/d3_studyplan.jsonl"

# Column positions, verified against the extracted table.
COL_CODE = 0
COL_NAME = 1
COL_SEMESTER = 9
COL_ECTS = 10
COL_EXAM = 12
COL_PRELIM = 13
COL_LANGUAGE = 14

# A module row is one whose first cell is a module code. Detecting them by
# pattern rather than by row index means the script survives the table
# gaining or losing a header row.
RE_MODULE_CODE = re.compile(r"^\d+-?\d+$")


def clean(cell):
    return (cell or "").replace("\n", " ").strip()


doc = fitz.open(PDF)
tables = doc[PAGE].find_tables()

if not tables.tables:
    raise SystemExit(f"No table found on page {PAGE + 1} of {PDF}")

rows = tables.tables[0].extract()
print(f"{len(rows)} rows x {len(rows[0])} columns")

records = []

for row in rows:
    cells = [clean(c) for c in row]
    code = cells[COL_CODE]

    if not RE_MODULE_CODE.match(code):
        continue                              # header, section title or total

    name = cells[COL_NAME]
    semester = cells[COL_SEMESTER]
    ects = cells[COL_ECTS]
    exam = cells[COL_EXAM]
    prelim = cells[COL_PRELIM]
    language = cells[COL_LANGUAGE]

    # Everything downstream embeds and searches `text`, so each row needs to
    # become a searchable sentence. The structured fields ride alongside for
    # exact lookups.
    text = (
        f"Module {code} {name}: {ects} ECTS, semester {semester}, "
        f"examination {exam}"
        + (f" with preliminary examination {prelim}" if prelim else "")
        + f", taught in {language}."
    )

    records.append({
        "doc": "D3",
        "programme": "iai",
        "authority": "binding",
        "page": PAGE + 1,
        "section": "47",
        "section_title": "Study and examination schedule",
        "paragraph": None,
        "sentence": None,
        "module_code": code,
        "module_name": name,
        "semester": semester,
        "ects": ects,
        "examination": exam,
        "preliminary": prelim or None,
        "language": language,
        "text": text,
    })

with open(OUT, "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"{len(records)} module records -> {OUT}\n")

for r in records:
    print(f"  {r['module_code']:6} {r['ects']:>5} ECTS  sem {r['semester']:4} "
          f"{r['examination']:22} {r['module_name'][:40]}")

# The programme is 90 ECTS across 9 modules including the thesis. A mismatch
# means a row was missed or a column moved.
total = sum(float(r["ects"].replace(",", ".")) for r in records if r["ects"])
print(f"\ntotal ECTS: {total:g}")
if len(records) != 9 or total != 90:
    print(f"  WARNING: expected 9 modules totalling 90 ECTS, "
          f"got {len(records)} totalling {total:g}")