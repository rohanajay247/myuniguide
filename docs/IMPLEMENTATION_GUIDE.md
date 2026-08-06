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
at all. Corrected and dated _before_ any system existed, so nothing could be
biased in its favour. Corrections after that point would not be legitimate.

---

## Step 5 — The long-context baseline

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
