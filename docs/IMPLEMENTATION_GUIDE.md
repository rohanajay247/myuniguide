# Implementation Guide — IAI StuPO Assistant

**How things were actually done, and why.**

This is the file to read when you have forgotten how something works. Each
section is a step you can re-run from scratch: the commands, the code, the
reasoning behind the choice, and the traps that cost time the first time round.

Other files, so you know where to look:

| File                   | Answers                                           |
| ---------------------- | ------------------------------------------------- |
| `docs/BRD_v09.md`      | What is being built and why                       |
| `docs/WBS_10day_v4.md` | The plan and schedule                             |
| `docs/FINDINGS.md`     | What the documents contain and how they misbehave |
| `docs/PROGRESS.md`     | What was done on which day                        |
| `docs/notes.md`        | Scoring rules and measured results                |
| **this file**          | **How each step was performed**                   |

---

## Environment

**Machine:** Windows, PowerShell, project at `D:\MyUniGuide`
**Python:** 3.12.8

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If activation is blocked with "running scripts is disabled on this system",
run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

**Every new terminal needs the activate line.** If `(.venv)` is not in the
prompt, the wrong Python is being used.

**Packages installed so far:**

```powershell
pip install pymupdf pytesseract pillow pyyaml
```

**Layout:**

```
MyUniGuide/
├── .venv/
├── config/                 data files the pipeline loads
│   ├── sources.yaml
│   ├── routing.yaml
│   └── glossary.md
├── data/
│   ├── raw/                the four source PDFs, never edited
│   ├── d1_raw.txt … d4_raw.txt
│   ├── d2_page2.png
│   └── d2_page2_tesseract.txt
├── docs/                   documentation, read by humans
│   ├── BRD_v09.md
│   ├── WBS_10day_v4.md
│   ├── FINDINGS.md
│   ├── PROGRESS.md
│   ├── IMPLEMENTATION_GUIDE.md
│   └── notes.md
├── pipeline/
│   ├── peek.py
│   ├── inventory.py
│   └── ocr_compare.py
├── eval.csv
├── baseline_results.csv
├── .gitignore
└── README.md               written on Day 10
```

**The split is by consumer, not by file type.** `config/` holds files the code
reads — `glossary.md` lives there despite being Markdown, because the query
expander loads it. `docs/` holds files only humans read. `eval.csv` stays at root
because it is the project's yardstick and gets referenced constantly.

`README.md` must be at root; GitHub renders it from nowhere else.

`data/raw` is treated as read-only. Everything else can be regenerated from it,
which is what makes it safe to delete and rebuild anything downstream.

**Run scripts from the project root**, since all paths are relative to it:

```powershell
python pipeline/peek.py        # correct
cd pipeline; python peek.py    # breaks — paths resolve wrongly
```

### Two Windows traps that cost time

**Never name a script after a stdlib module.** `pipeline/inspect.py` shadowed
Python's built-in `inspect`, which PyMuPDF imports at startup. The error was a
confusing circular-import message that said nothing about filenames. Avoid:
`inspect`, `types`, `string`, `random`, `email`, `test`, `json`, `logging`,
`code`, `parser`, `select`, `platform`, `queue`, `signal`, `socket`, `time`,
`copy`.

**Use forward slashes in Python paths.** `"data\raw\StuPO..."` produces
`SyntaxWarning: invalid escape sequence` because `\r` and `\S` are read as escape
sequences. `"data/raw/StuPO..."` works fine on Windows. Alternatively prefix with
`r` for a raw string.

---

## Step 1 — Extract text from the PDFs

**Tool: PyMuPDF.** Imported as `fitz` for historical reasons; newer versions also
accept `import pymupdf`.

`pipeline/peek.py`:

```python
import fitz

PDF = "data/raw/StuPO_Master_221_20220111.pdf"
OUT = "data/d1_raw.txt"

doc = fitz.open(PDF)

pages = []
for i in range(doc.page_count):
    text = doc[i].get_text()
    pages.append(f"\n\n===== PAGE {i + 1} =====\n\n{text}")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("".join(pages))

print("wrote", OUT)
print("total characters:", sum(len(p) for p in pages))
```

Run once per document, changing `PDF` and `OUT`.

**`encoding="utf-8"` is not optional on Windows.** Without it Python uses a
legacy code page that cannot represent `ü`, `ä`, `ß` or `§`, and the write
crashes.

**Result:** D1, D3 and D4 extract cleanly. D2 returns 13,625 characters of
damaged German — it is a scan carrying a poor embedded OCR layer.

### Verify against the file, never against a rendering

Three separate times, text pasted into a chat window appeared corrupted
(`Modulbzw`, `ofthe`, `forthe`, `CRISPDM`) when the actual `.txt` was clean.
Different extractors fail differently. **When something looks broken, grep the
file:**

```powershell
Select-String -Path data\d1_raw.txt -Pattern "Modulbzw" | Measure-Object
```

---

## Step 2 — Decide the OCR path for D2

D2 is a scan. Worse, it ships with a poor embedded OCR layer, so
`get_text()` returns 13,625 characters of plausible-looking damaged German
rather than nothing. **It fails silently.** Zero `§` symbols across six pages;
sentence numbering destroyed.

Sentence numbering matters because German legal citation addresses it directly:
`§ 12 Abs. 2 Satz 3` means section 12, paragraph 2, **sentence 3**.

### Render pages to images

```python
import fitz

PDF = "data/raw/2022-07-14_StuPO_Master_Erste_AEnderungssatzung_beurkundet.pdf"
doc = fitz.open(PDF)
doc[1].get_pixmap(dpi=300).save("data/d2_page2.png")
```

**300 dpi** is the standard floor for OCR — below ~200 the letterforms degrade
sharply, above 600 gains little. **PNG, not JPEG** — JPEG compression puts
artifacts around letter edges, exactly what OCR does not want.

### Attempt 1 — Tesseract (rejected)

Windows installer from the UB Mannheim build. **Tick German under "Additional
language data"** — easy to click past, and without it every umlaut is mangled.

The installer does not add itself to PATH:

```powershell
$env:Path += ";C:\Program Files\Tesseract-OCR"    # this session only
tesseract --version
tesseract --list-langs                             # must include: deu
```

```python
import io, fitz, pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

pix = doc[i].get_pixmap(dpi=300)
img = Image.open(io.BytesIO(pix.tobytes("png")))     # pixmap -> PIL, in memory
text = pytesseract.image_to_string(img, lang="deu")
```

**Word accuracy was excellent** — correct on every token the embedded layer had
damaged: `Prüfungszeitraums`, `Adoptionsurkunde`, `Landeshochschulgesetz`,
`Erfolgskontrollen`, `12.07.2022`.

**But it cannot read superscripts.** They come out as punctuation:

```
¹ -> ! " ' 1        ² -> ? 2
³ -> ? ® dropped    ⁴ -> * "      ⁵ -> ? ® "
```

### The strategy that died, and why

Reading the glyph was never necessary — sentences run in order, so the Nth
marker in a paragraph is sentence N. Count, don't decode.

**That worked perfectly on page 2**, which is why it looked settled.

**Page 3 broke it.** In § 12b Abs. 2, six sentences, Tesseract produced five
markers — the ³ was **gone entirely**, not misread. Count five, label them 1–5,
and everything from the third onward is off by one. The system would cite
`Satz 3` and quote sentence 4. A citation that looks entirely correct and points
at the wrong rule.

**Lesson: one page is an anecdote.** Page 2 made both Tesseract and positional
recovery look sound. Six pages killed both.

### Attempt 2 — Gemini Vision (adopted)

```python
import os, time, fitz
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

PROMPT = """Transcribe this page of German legal text exactly.

This document numbers individual sentences with superscript digits.
Preserve every one as a normal digit attached to the start of its
sentence, e.g. the superscript 1 in "Macht" becomes "1Macht".

Transcribe the section symbol § correctly wherever it appears.

If a character or number is unclear, write [?] rather than guessing.

Do not summarise, correct, translate or reformat. Transcribe only.
Output the page text and nothing else."""

for i in range(doc.page_count):
    png = doc[i].get_pixmap(dpi=300).tobytes("png")
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[types.Part.from_bytes(data=png, mime_type="image/png"), PROMPT],
        config=types.GenerateContentConfig(temperature=0),
    )
    pages.append(response.text)
    time.sleep(2)
```

**Three deliberate choices:**

**No `tools` parameter at all.** In AI Studio, Gemini kept web-searching during
transcription and citing _other universities'_ regulations — and continued doing
so after the grounding toggle was switched off. That is dangerous: a model that
has seen similar German regulations can "correct" yours toward what it expects,
producing fluent, plausible, wrong text with no error raised. Passing no tools
through the API makes search unavailable regardless of any UI setting. This is
the main reason to script it rather than use the web interface.

**`os.environ["GEMINI_API_KEY"]`** with square brackets, not `.get()` — it
crashes immediately if the key is missing instead of silently sending an
unauthenticated request.

**`[?]` for uncertainty.** Gemini's failure mode is filling gaps plausibly
rather than visibly. In the manual run it turned amendment item `4.` into `1.`.
Asking for an explicit marker gives a visible flag instead of a confident
invention. (It complied — 0 flags in the final run — and got item 4 right.)

### Result

```
§ symbols        22   (embedded layer: 0, Tesseract: 0)
[?] flags         0
Amendment items   1–7 all correct
Sentence markers  match the source in every paragraph checked
```

Words clean throughout where Tesseract gave `Nachwelse` and `Persön`.

### Why the metric mattered more than the tool

The first scoring metric — _count surviving digits_ — ranked the **embedded
layer** highest (6/10 vs Tesseract's 1/10) and would have selected the worst
option available. Tesseract would have won any general OCR benchmark on word
accuracy. Both would have been wrong choices.

**The right criterion is: does the structure the system depends on survive?**
Not general accuracy. Wrong-but-consistent beats wrong-but-random, and
present-but-mislabelled beats missing.

### Four quirks the chunker must handle

**Marker style is inconsistent between pages.** Page 1 produced real
superscripts (`„²Modul-`, `¹Macht`); pages 2–6 produced plain digits (`2Dies`).
Same prompt, same call, same temperature. Accept both:

```python
r'[0-9¹²³⁴⁵⁶⁷⁸⁹](?=[A-ZÄÖÜ])'
```

Worth knowing generally: temperature 0 does not guarantee identical formatting
across independent requests.

**It reformatted the annex table as Markdown** despite being told not to
reformat. Useful here — the table structure survived, which flat extraction
destroys — but it disobeyed an instruction.

**The annex table splits across a page boundary.** Rows 1–10 on page 5, row 11
(Portfolioprüfung) on page 6, and page 6's row lost its leading `|`. These must
be rejoined or the Portfolioprüfung definition ends up orphaned — which matters,
since the `Pf` finding turns on it.

**`GBl.` came out as `GBI.`** (capital i for lowercase L) twice. Harmless — it
sits in the legal preamble, not in a rule.

## Step 3 — Fingerprint the sources

`pipeline/inventory.py`:

```python
import hashlib
from pathlib import Path

RAW = Path("data/raw")

for pdf in sorted(RAW.glob("*.pdf")):
    data = pdf.read_bytes()
    print(pdf.name)
    print(f"  sha256: {hashlib.sha256(data).hexdigest()}")
    print(f"  bytes:  {len(data):,}")
```

`read_bytes()`, not text — a PDF is binary.

The hashes go into `config/sources.yaml`, which does three jobs beyond documentation:

- **`authority`** (`binding` / `descriptive`) drives the Day 8 ranking rule
- **`text_layer`** (`native` / `scan_bad_ocr`) routes D2 to Tesseract and the
  rest to PyMuPDF — data-driven, not `if filename ==` buried in code
- **`programme`** (`all` / `iai`) is the multi-programme filter

Validate:

```powershell
python -c "import yaml; d=yaml.safe_load(open('config/sources.yaml',encoding='utf-8')); print(len(d),'entries')"
```

**Finding the URLs.** Google search misses the newer programme-specific statutes.
The Rechtsgrundlagen page on `hs-albsig.de` is the authoritative index, and
programmatic fetching truncates before the Master section — read it in a browser
and copy the links by hand. Note that D1 sits in `.../stupos/` while D2 and D3
are one level deeper in `.../stupos/master/`.

---

## Step 4 — Parse the documents into addressable records

**Goal:** turn each PDF into records like

```json
{
  "doc": "D1",
  "section": "21",
  "paragraph": "5",
  "sentence": "2",
  "text": "Sie ist innerhalb von vier bis sechs Monaten zu bearbeiten.",
  "authority": "binding",
  "programme": "all",
  "page": 10
}
```

One legal provision, its exact address, plus the metadata later stages need.
`authority` drives the Day 8 ranking rule; `programme` is the multi-programme
filter.

### The key insight: a PDF encodes appearance, never meaning

There is no "this is a heading" flag. There is only "this text is 6pt at
x=70.9". Structure has to be reverse-engineered from visual properties, which
is why parsers are per-document rather than universal.

`get_text()` returns a flat string and throws all of that away.
`get_text("dict")` returns nested blocks → lines → **spans**, where a span is a
run of characters sharing one font and size, carrying `size` and `bbox`.

### Three mechanisms

**1. Font size identifies sentence markers.**

In D1 the body is 9pt and sentence markers are 6pt. Nothing else uses 6pt. So
these become separable, where in flat text they are identical characters:

```
1,0 ; 1,3 ; 1,7          grades           9pt
§ 16 Abs. 1 Satz 1       cross-reference  9pt
15 Minuten               duration         9pt
1Die Studierenden        sentence marker  6pt
```

**Do not hardcode the threshold.** D4's body is 10.1pt with small text at 5.2,
5.7, 6.0 and 6.6 — a fixed `< 7` misclassifies it. Derive it instead:

```python
def body_size(doc):
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

MARKER_RATIO = 0.80    # marker if < 80% of body
NOISE_RATIO  = 0.95    # smaller than body but not a marker => running header
```

**2. Position disambiguates headings from cross-references.**

`§ 21` appears both as a heading and inside sentences like _"Näheres regelt
§ 21 Abs. 5"_. Text alone cannot separate them. Position can — headings sit at
the left margin (x≈70), cross-references sit mid-line (x≈250):

```python
if re_section.search(joined) and left < MARGIN_X:
```

**3. A state machine assembles sentences.**

The PDF yields lines, but a sentence can begin mid-line. Text accumulates in a
buffer; four variables track position. When a marker appears it means _the
previous sentence just ended_:

```python
flush()               # save with the OLD sentence number
state["sentence"] = t # then move on
```

**Reverse those two lines and every sentence is labelled with the following
sentence's number.** Silently, and every citation wrong.

### Justified text scatters spans

```
'über ' 'den ' 'Rücktritt ' 'von ' 'Studierenden ' 'von ' 'bereits '
```

The PDF stretches word spacing to justify, and each stretched gap becomes a
span boundary. Spans must be regrouped into lines before anything else.

### Three bugs, each found by checking a known fact

None of these raised an error. Each was found by asking whether a specific
provision landed where it should.

**`§§ 32 bis 43` parsed as "section 32, titled bis 43".** Fixed with
`(?!bis\b)`. German legal grammar, so it belongs in code — it will appear in
any German regulation.

**§ 44's text filed under § 31.** `§ 44` sits alone on its line with
`Inkrafttreten` on the next, and the regex demanded a title on the same line.
Made the title optional: `\s*(.*)` instead of `\s+(.+)`. § 44 is the cohort
rule — the version in force when you enrolled governs you — so this would have
produced confident citations to a section that does not exist in the document.

**D4 produced 1 record from 26 pages** and reported success. It has no `§`
structure at all; modules are headed `Module: X`. Nothing matched, nothing
flushed, everything accumulated into a single record.

Hence the cheapest possible alarm:

```python
if len(records) < doc.page_count:
    print(f"  WARNING: {len(records)} records from {doc.page_count} pages")
```

### Where the config/code line falls

**Per-document facts go in `config/sources.yaml`. Structural rules go in code.**

```yaml
# D1, D2
  heading_pattern: '^§\s*(\d+[a-z]?)\b\s*(?!bis\b)(.*)'
# D3 — writes "Re § 2" for references and "Para. 3" where D1 writes "(3)"
  heading_pattern: '^(?:Re\s+)?§\s*(\d+[a-z]?)\b\s*(?!bis\b)(.*)'
# D4 — no § structure at all
  layout: pages
  sentence_markers: false
```

Contents-page detection stays in code, because it is a property of contents
pages generally rather than of D1 page 3:

```python
def is_contents(lines):
    joined = " ".join(...)
    return len(re.findall(r"§\s*\d+", joined)) > 8 and len(joined) < 2500
```

`SKIP_PAGES = {2, 3, 4}` would have been genuine hardcoding — a magic number
true of one file.

### D4: an accepted limitation

D4 is parsed one record per page rather than per provision. It is descriptive
rather than binding and loses every conflict against the statutes, so page-level
granularity is sufficient for its role as the source cited _against_. Recorded
in `sources.yaml` as `layout: pages` rather than left as a silent failure.

Cost: a question like "what is the workload for Operational Excellence?"
retrieves the whole page rather than that field.

### Result

```
d1_parsed.jsonl   271 records
d3_parsed.jsonl    41
d4_parsed.jsonl    24   (WARNING fired: 24 from 26 pages — two image-only pages)
```

---

## Step 5 — Parse D2 from OCR text

D2 has no font-size information, so the same state machine runs over
`data/d2_ocr.txt` with markers found by regex instead of by size.

```python
# Gemini produced real superscripts on page 1 and plain digits on pages 2-6
# from the same prompt. Accept both. The lookbehind prevents matching inside
# dates (12.07.2022) and grades (1,0).
RE_MARKER = re.compile(r"(?<![\w,\.])([0-9¹²³⁴⁵⁶⁷⁸⁹])(?=[A-ZÄÖÜ][a-zäöüß])")
SUPER = str.maketrans("¹²³⁴⁵⁶⁷⁸⁹", "123456789")
```

### An amending statute has two heading shapes

```
1. § 12 wird wie folgt geändert:     the section being amended
„§ 12a Online-Prüfungen              the section being inserted
```

The first run only matched the second form, so **§ 12 was missing entirely** —
and § 12 is the most important change D2 makes, the one that reorders the exam
list so `Nr. 4` means _Hausarbeiten_ before July 2022 and _Referat_ after.

```python
RE_SECTION = re.compile(r"^(?:\d{1,2}\.\s*)?„?§\s*(\d+[a-z]?)\b\s*(.*)")
```

The `„?` allows the German opening quote, since the statute quotes the text it
inserts.

### The annex row that nearly vanished

Gemini rendered the annex as a Markdown table, but the table splits across
pages 5 and 6, and page 6's row lost its leading `|`. That row is
**the only binding definition of Portfolioprüfung**, the exam type covering 30
of the programme's 90 ECTS.

It was first parsed as part of § 12e with the page footer attached:

```
§12e :: Hochschule Albstadt-Sigmaringen ... University 5 11. Portfolioprüfung | Prüfung...
```

Two fixes — a second row pattern, and footer stripping:

```python
RE_TABLE_ROW = re.compile(r"^\d{1,2}\.\s+\S.*\|")
```

Annex rows are labelled `section: "Anhang"` rather than inheriting the previous
section number.

**`table_marker: '|'` lives in `sources.yaml`**, not in code — it assumes Gemini
emits Markdown, which it did _despite being told not to reformat_. A model or
prompt change breaks that assumption, so it belongs in config where it is
visible.

### Known coupling

`RE_PAGE` parses the `===== PAGE n =====` separator written by `ocr_d2.py`. The
two files share a convention with nothing enforcing it — change one and the
other silently stops finding pages, and every record gets `page: 1`. Writing
JSONL with a real `page` field from the OCR step would remove the coupling.

### Result

```
d2_parsed.jsonl   73 records
sections: 12, 12a, 12b, 12c, 12d, 12e, Anhang
```

§ 12b Abs. 2 has all six sentences correctly numbered, including the ³ that
Tesseract dropped. Built-in warnings now check for § 12 and Anhang.

Remaining blemishes, accepted: three records after the annex inherit
`section: Anhang`, the Markdown separator row survives, and § 12's eleven-item
exam list is one blob rather than eleven items. None affects retrievability.

---

## Step 6 — Extract the study plan table

D3 page 6 answers more real student questions than any other page — ECTS per
module, semester, examination type, teaching language — and nothing else does.

Flat extraction destroys the column alignment. Empty cells produce inconsistent
blank counts, long module names wrap, and the first row merges its code and
name, so the distance from a module code to its ECTS value runs **8, 8, 9, 10,
8** across five consecutive rows. Counting positions returns `4` where `5`
belongs, with no error.

```python
tables = doc[5].find_tables()
rows = tables.tables[0].extract()      # 20 rows x 15 columns, aligned
```

Column map, verified against the extracted table:

```
 0  module code        2-010, 55010
 1  module name
 9  semester           1, 2, 1+2, 3
10  ECTS               5, 12,5, 7,5, 30
12  examination type   R (5), Pf (5), Ma (30)
13  preliminary exam   Ha**  (only 2-010)
14  language           EN, EN/ DE
```

**Known limitation:** vertically merged cells collapse into the first row of
each block — row 4 shows `'CM CM CM CEM'` and rows 5–7 show nothing. The columns
that matter come through clean on every row.

Module rows are detected by pattern rather than row index, so the script
survives the table gaining a header row:

```python
RE_MODULE_CODE = re.compile(r"^\d+-?\d+$")
```

Each row becomes a searchable sentence, because everything downstream embeds
`text`. Structured fields ride alongside for exact lookups.

**The guard that makes the remaining hardcoding acceptable:**

```python
total = sum(float(r["ects"].replace(",", ".")) for r in records if r["ects"])
if len(records) != 9 or total != 90:
    print("  WARNING: expected 9 modules totalling 90 ECTS")
```

`PAGE = 5` and the column indices are hardcoded. That is defensible only
because this check fires if either assumption breaks. Generalising would mean
detecting the page by content and mapping columns by header text — real work,
for a case that does not exist yet.

### Result

```
9 modules, 90 ECTS, no warning

2-010   5      sem 1     R (5)               Artificial Intelligence
2-020   5      sem 1     Pf (5)              Data Science
2-030   12,5   sem 1     Pf (12,5)           Project - AI and Data Engineering
2-040   7,5    sem 1+2   X (7,5)             WPM - AI and Data Engineering
1-010   5      sem 2     R (2,5) + La (2,5)  Digital Technology and Management
1-020   5      sem 2     Ha (5)              Operational Excellence
1-030   12,5   sem 2     Pf (12,5)           Project - Industrial Operations
1-040   7,5    sem 1+2   X (7,5)             WPM - Industrial Operations
55010   30     sem 3     Ma (30)             Master's Thesis
```

Confirms three findings from structured data rather than eyeballing: `Pf`
covers exactly 30 of 90 ECTS; both WPM modules are `1+2` where D4 says 2nd
semester; and `55010` really is five digits with no hyphen where every other
code is `n-0n0`.

---

## The pattern: this pipeline fails silently

Seven times through parsing and OCR, a stage produced plausible output that was
wrong in a specific, checkable way:

| Stage                 | Failure                               | How it was caught                  |
| --------------------- | ------------------------------------- | ---------------------------------- |
| Flat table extraction | ECTS read from the wrong column       | Compared distances across rows     |
| Tesseract             | Dropped a sentence marker entirely    | Counted markers against the source |
| D1 parser             | `§§ 32 bis 43` read as a section      | Looked at the section list         |
| D1 parser             | § 44's text filed under § 31          | Searched for a known provision     |
| D4 parser             | 1 record from 26 pages                | Noticed the record count           |
| D2 parser             | § 12 missing entirely                 | Listed the sections found          |
| D2 parser             | Portfolioprüfung merged with a footer | Searched for a known definition    |

**Not one raised an error.** Every one was caught by checking a specific known
fact — which is what `FINDINGS.md` is actually for. It is the checklist.

Hence every stage now asserts something it can verify itself: record count
against page count, § 12 and Anhang present, nine modules totalling 90 ECTS.

---

## Step 7 — The evaluation set

**50 questions with known answers, written before any pipeline code.** This is
the gate: without it, no claim about the system is falsifiable.

`eval.csv` columns:

```
id,question,expected_answer,outcome,source_doc,section,programme,category
```

**Three outcomes, not two.** `answer`, `decline`, and `conflict`. The third
exists because the corpus contains around twenty documented contradictions —
"the documents disagree" is a routine result here, not an edge case.

Composition: 33 answer · 11 decline · 6 conflict · 34 `all` · 16 `iai`.

**Two rules while writing.** Write the question before looking up the answer,
or you will only write questions the documents happen to answer well. And
deliberately include questions you expect to fail — a set that passes on the
first run was written too kindly.

**Fix the scoring rules before seeing any output** (they live at the top of
`docs/notes.md`). Deciding what counts as correct after seeing results is how
goalposts move without anyone noticing.

**One expected answer was wrong** — E04 assumed acute illness required a medical
certificate; D1 § 11a Abs. 1 allows withdrawal by non-attendance with no reasons
at all. Corrected and dated _before_ any system existed, so nothing could be
biased in its favour. Corrections after that point would not be legitimate.

---

## Step 8 — The long-context baseline

**Deliberately low-tech: no code.** It runs once, and reading fifty raw responses
by hand teaches you what the failure modes look like.

**Setup.** Google AI Studio → Gemini 3.6 Flash → temperature 0 → upload the four
**original PDFs** from `data/raw`.

_Upload PDFs, do not paste text._ Gemini reads scans natively via vision, so
D2's damaged OCR layer never enters the picture — and "upload the PDFs and ask"
is what a naive user would actually do, which makes it the honest baseline.

**System instruction** — this must be as good as the one the real system gets,
or the comparison measures prompt quality rather than architecture:

```
You answer questions about the examination regulations for the M.Sc.
Industrial Artificial Intelligence programme at Hochschule
Albstadt-Sigmaringen, using only the four attached documents.

The documents are:
D1 - Master StuPO General Part 22.1 (German, binding)
D2 - First Amendment to D1, July 2022 (German, binding)
D3 - IAI Supplementary Statute 25.2 (English, binding)
D4 - Module Handbook (English, descriptive, NOT binding)

Answer in English, briefly.

Always cite the document and the exact provision, e.g.
"D1 § 16 Abs. 1" or "D3 Re § 21 Para. 5".

Give one of three response types:

1. ANSWER - the documents answer the question. Answer and cite.
2. DECLINE - the documents do not cover it. Say so and name the office
   or system to contact. Do not guess.
3. CONFLICT - the documents contradict each other. Say so, name both
   sources, quote both, and do not choose between them.

Begin every response with the type in capitals.

Where an amendment or supplementary statute modifies the general part,
the more specific and more recent provision applies. Where D4 conflicts
with D1, D2 or D3, the statutes govern.
```

**"Begin with the type in capitals" makes scoring mechanical** — read one word
to check the response _kind_, then check the content.

**Method.** Batches of five. Score as you go into `baseline_results.csv`
(`eval.csv` plus `actual_outcome`, `correct`, `failure_note`). Never tune the
prompt or switch models mid-run.

_Trap:_ batch numbering slipped by one partway through — one question repeated,
one skipped. Check `id` alignment as you go.

**Result: 42/50 — 84%.** Lookup 33/33, declines 9/11, conflicts 0/6.

**What it means.** Long context is perfect at lookup and structurally blind to
contradiction. Synthesis and contradiction-reporting pull in opposite directions:
a system good at combining sources is inclined to _resolve_ their disagreements
rather than surface them. That 0/6 is the gap the retrieval system targets.

---

## Design decisions and their reasons

| Decision                              | Reason                                                                                                                                                                                                            |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| No LangChain / LlamaIndex / vector DB | None of the hard parts (amendment renumbering, authority ranking, § chunking, table extraction) exist in any framework. With four documents a framework saves ~60 lines of 200 and adds a layer to debug through. |
| Tesseract over the embedded OCR layer | Recoverable failures beat irrecoverable ones.                                                                                                                                                                     |
| Gemini 3.6 Flash, held constant       | Long-context retrieval advantage; GA rather than Preview, so the baseline is reproducible. Changing models mid-project would confound every accuracy delta.                                                       |
| Eval set before pipeline code         | Otherwise no claim is falsifiable and no failure analysis is possible.                                                                                                                                            |
| Three outcomes, not two               | ~20 documented contradictions make conflict a routine result.                                                                                                                                                     |
| `programme` field from the start      | Half the corpus (D1, D2) is shared across all 12 Master programmes. Adding it later means re-embedding everything.                                                                                                |
| PDFs excluded from git                | They are the university's. `sources.yaml` hashes prove which files were used.                                                                                                                                     |

---

## Still to write

Sections for ingestion, chunking, embedding, retrieval, answer generation and
deployment get added as those steps are built. Each should follow the same shape:
**the commands, the code, why that choice, and what went wrong the first time.**
