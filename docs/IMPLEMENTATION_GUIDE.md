# Implementation Guide — IAI StuPO Assistant

**How things were actually done, and why.**

This is the file to read when you have forgotten how something works. Each
section is a step you can re-run from scratch: the commands, the code, the
reasoning behind the choice, and the traps that cost time the first time round.

Other files, so you know where to look:

| File | Answers |
|---|---|
| `docs/BRD_v09.md` | What is being built and why |
| `docs/WBS_10day_v4.md` | The plan and schedule |
| `docs/FINDINGS.md` | What the documents contain and how they misbehave |
| `docs/PROGRESS.md` | What was done on which day |
| `docs/notes.md` | Scoring rules and measured results |
| **this file** | **How each step was performed** |

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

### Render the page

```python
import fitz

PDF = "data/raw/2022-07-14_StuPO_Master_Erste_AEnderungssatzung_beurkundet.pdf"
doc = fitz.open(PDF)
doc[1].get_pixmap(dpi=300).save("data/d2_page2.png")
```

**300 dpi** is the standard floor for OCR — below about 200 the letterforms
degrade and accuracy drops sharply; above 600 gains little. **PNG, not JPEG** —
JPEG compression puts artifacts around letter edges, which is exactly what OCR
does not want.

### Install Tesseract

Windows installer from the UB Mannheim build. **Tick German under "Additional
language data"** during setup — easy to click past, and without it every umlaut
is mangled.

The installer does not add itself to PATH. Either add
`C:\Program Files\Tesseract-OCR` via Windows environment variables, or set it
per-session:

```powershell
$env:Path += ";C:\Program Files\Tesseract-OCR"
```

Verify:

```powershell
tesseract --version
tesseract --list-langs     # must include: deu
```

### Run it

`pipeline/ocr_compare.py`:

```python
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

img = Image.open("data/d2_page2.png")
text = pytesseract.image_to_string(img, lang="deu")

with open("data/d2_page2_tesseract.txt", "w", encoding="utf-8") as f:
    f.write(text)
```

**Keep `tesseract_cmd` even when PATH works.** It makes the pipeline independent
of shell configuration. The portable form:

```python
import os
pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
```

### The decision, and the lesson

Compared on one page: Tesseract was correct on every word the embedded layer had
damaged (`Prüfungszeitraums`, `Adoptionsurkunde`, `Landeshochschulgesetz`,
`durchgeführt`, `§ 12b`), and found 10 sentence markers where the embedded layer
found 8.

But Tesseract renders superscripts as punctuation:

```
Tesseract:  ? ? * ! 2 ! ? ! ! !
Actual:     2 3 4 1 2 1 2 1 1 1

!  -> superscript 1   *  -> superscript 4   ?  -> 2 or 3 (ambiguous)
```

**The first scoring metric was wrong.** Counting surviving digits ranked the
embedded layer higher (6/10 vs 1/10) and would have selected the worse option.
The embedded layer corrupts real words irrecoverably; Tesseract's failures are
consistent glyph substitutions that a post-processing pass can undo.

**The right criterion is recoverability, not raw correctness.**
Wrong-but-consistent beats wrong-but-random.

Recovery is positional: sentence numbers run sequentially within a paragraph and
Tesseract preserves every marker's position, so the Nth marker is sentence N —
the glyph never needs reading. `§` is recovered from `[&8]` followed by space and
a digit.

**Known trap for the parser:** paragraphs cross page boundaries. Page 2's first
paragraph continues from page 1, so its markers start at 2. Code that assumes
every paragraph starts at 1 will renumber silently and wrongly.

---

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

## Step 4 — The evaluation set

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
at all. Corrected and dated *before* any system existed, so nothing could be
biased in its favour. Corrections after that point would not be legitimate.

---

## Step 5 — The long-context baseline

**Deliberately low-tech: no code.** It runs once, and reading fifty raw responses
by hand teaches you what the failure modes look like.

**Setup.** Google AI Studio → Gemini 3.6 Flash → temperature 0 → upload the four
**original PDFs** from `data/raw`.

*Upload PDFs, do not paste text.* Gemini reads scans natively via vision, so
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
to check the response *kind*, then check the content.

**Method.** Batches of five. Score as you go into `baseline_results.csv`
(`eval.csv` plus `actual_outcome`, `correct`, `failure_note`). Never tune the
prompt or switch models mid-run.

*Trap:* batch numbering slipped by one partway through — one question repeated,
one skipped. Check `id` alignment as you go.

**Result: 42/50 — 84%.** Lookup 33/33, declines 9/11, conflicts 0/6.

**What it means.** Long context is perfect at lookup and structurally blind to
contradiction. Synthesis and contradiction-reporting pull in opposite directions:
a system good at combining sources is inclined to *resolve* their disagreements
rather than surface them. That 0/6 is the gap the retrieval system targets.

---

## Design decisions and their reasons

| Decision | Reason |
|---|---|
| No LangChain / LlamaIndex / vector DB | None of the hard parts (amendment renumbering, authority ranking, § chunking, table extraction) exist in any framework. With four documents a framework saves ~60 lines of 200 and adds a layer to debug through. |
| Tesseract over the embedded OCR layer | Recoverable failures beat irrecoverable ones. |
| Gemini 3.6 Flash, held constant | Long-context retrieval advantage; GA rather than Preview, so the baseline is reproducible. Changing models mid-project would confound every accuracy delta. |
| Eval set before pipeline code | Otherwise no claim is falsifiable and no failure analysis is possible. |
| Three outcomes, not two | ~20 documented contradictions make conflict a routine result. |
| `programme` field from the start | Half the corpus (D1, D2) is shared across all 12 Master programmes. Adding it later means re-embedding everything. |
| PDFs excluded from git | They are the university's. `sources.yaml` hashes prove which files were used. |

---

## Still to write

Sections for ingestion, chunking, embedding, retrieval, answer generation and
deployment get added as those steps are built. Each should follow the same shape:
**the commands, the code, why that choice, and what went wrong the first time.**
