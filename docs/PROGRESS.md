# Progress log — IAI StuPO Assistant

Daily record of what was done. Brief by design.

Findings live in `FINDINGS.md`. Plan lives in `WBS_10day_v4.md`.
How things were done lives in `IMPLEMENTATION_GUIDE.md`. All in this `docs/` folder.

| | |
|---|---|
| Started | 4 Aug 2026 |
| Plan | 10 working days, ~62 h |
| Days elapsed | 3 |
| Phase | 1 complete — moving to ingestion |
| Pipeline code written | none yet (gated behind the eval set) |

---

## Day 1 — 4 Aug · Setup and parsing verdict ✅

**Done**

- Python 3.12.8 + venv (`.venv`), PyMuPDF installed
- Repo folders: `data/raw`, `data`, `pipeline`
- All four PDFs extracted to `data/d1_raw.txt` … `d4_raw.txt`
- Every document read end to end; extraction quality assessed per document
- ~20 source defects and contradictions catalogued in `FINDINGS.md`
- `FINDINGS.md` created

**Decided**

- D1, D3, D4 extract cleanly with PyMuPDF — no OCR needed
- D2 is a scan carrying a *bad embedded OCR layer* — needs re-OCR, not first OCR
- `get_text("dict")` required later, to recover superscripts and indentation
- `find_tables()` required for D3's study plan
- Never strip a hyphen at end of line when joining wrapped text

**Corrected**

- D3 is in **English**, not German — BRD premise was wrong
- No `\x02` hyphen corruption — that came from a different extractor
- Real module codes are `2-010`, `1-010`, `55010` — not D4's `XX010` placeholders

**Hit**

- Naming a script `inspect.py` shadowed Python's stdlib `inspect` and broke
  PyMuPDF's import with a misleading circular-import error. Renamed to `peek.py`.
- Windows backslashes in Python string literals produce invalid escape
  sequences. Use forward slashes.

**Carried to Day 2:** `sources.yaml`, OCR comparison

---

## Day 2 — 5 Aug · Carryover, then the eval set 🔄

**Done**

- Rendered D2 page 2 at 300 dpi via `get_pixmap(dpi=300)` — scan is clean
- Tesseract 5.5.3 installed with German language data (`deu`)
- OCR comparison run: embedded layer vs Tesseract

**Decided**

- **Tesseract wins.** Correct on every known-damaged word; found 10 sentence
  markers where the embedded layer found 8.
- Gemini Vision not tested — it was the tiebreaker and there was no tie.
- Marker recovery is positional, not glyph-based: the Nth marker in a
  paragraph is sentence N.
- `§` recovery via regex on `[&8]` followed by space and a digit.

**Learned**

- My first scoring metric — "count surviving digits" — was wrong. It ranked
  the embedded layer higher (6/10 vs 1/10) and would have picked the worse
  option. The right criterion is **recoverability, not raw correctness**:
  wrong-but-consistent beats wrong-but-random. Worth a line in the README.

**Hit**

- The Tesseract installer does not add itself to PATH. Fixed permanently via
  Windows environment variables; scripts also set `tesseract_cmd` explicitly
  so the pipeline never depends on shell configuration.

- SHA-256 hashes computed for all four PDFs
- All four source URLs identified on the Rechtsgrundlagen index
- **Corpus verified complete**: Master General Section stops at 22.1 (Bachelor
  has reached 26.1 — Master untouched since Jan 2022), exactly one Master
  amendment, IAI special part at 25.2. Nothing missing, nothing newer.
- Prüfungsamt question 6 closed: no second Master amendment exists.

**Decided (cont.)**

- **Multi-programme expansion designed in, not deferred.** Three constraints
  adopted now because they are cheap and painful to retrofit: a `programme`
  field on every chunk (`all` / `iai`), no programme name in prompts or code,
  and a `programme` column in `eval.csv`. Half the corpus (D1, D2) is already
  shared across all twelve Master programmes. v2 adds exactly one further
  programme, not all eleven.

**Noted**

- The university runs an AI chat at `haski.hs-albsig.de`. Not currently
  accessible — possibly WIP. Worth re-checking before Day 10; "the university
  already has an AI chat" is the first objection a reviewer will raise, and the
  answer is that it doesn't cite § references or apply the 2022 amendment.

**Next:** the 50-question eval set

---

## Day 3 — 6 Aug · Eval set and baseline ✅

**Done**

- `sources.yaml` written and validated — 4 entries parse cleanly
- `eval.csv` completed: 50 questions with expected answers
  (33 answer · 11 decline · 6 conflict)
- `notes.md` created; scoring rules fixed **before** any output was seen
- Gemini API key set up, ₹200 budget cap, Postpay threshold understood
- **Long-context baseline run and scored by hand: 42/50 = 84%**

**Decided**

- **Gemini 3.6 Flash**, not 3.1 Pro. Flash has the long-context retrieval
  advantage, which is precisely the task; Pro is still Preview with weaker
  stability guarantees, and the baseline must be reproducible.
- Same model for baseline and all later generation. Changing models mid-project
  would confound every accuracy delta.
- Model choice revisited on Day 9 with data — run the eval against Flash-Lite
  and 2.5 Flash and publish the cost/accuracy table.

**Result**

```
Lookup     33/33  100%
Declines    9/11   82%
Conflicts   0/6     0%
Overall    42/50   84%
```

**This reshapes the project.** Retrieval will not beat 100% on lookup, and
should not try. The target is the 0/6 on conflict detection.

**Corrected**

- E04's expected answer was wrong. It assumed acute illness required a medical
  certificate; D1 § 11a Abs. 1 allows withdrawal by non-attendance with no
  reasons at all. Fixed and dated before any retrieval system existed.

**Hit**

- Batch numbering slipped by one partway through — a question was repeated and
  one skipped. Caught at row 15. Check `id` alignment when scoring in batches.

- `glossary.md` — ~140 German↔English terms in 9 groups, drawn from D1 and D2
- `routing.yaml` — 19 routes for the abstention path

**Noted while writing them**

- `§` is *section*; `Absatz` is *paragraph*. Translating `§` as "paragraph"
  yields citations that look right and point to the wrong level.
- `Verteidigung` appears 30 times in D1 and applies to IAI **not at all**
  (D3 Re § 3 Para. 1). Term frequency is not relevance — a retrieval system
  weighting on frequency alone will over-rank those passages.
- `Näheres regelt der Besondere Teil` is the pointer phrase sending a reader from
  D1 to D3. Any chunk containing it is incomplete on its own.
- Several routing contacts are marked TODO. The baseline invented "CAS/LSF" as
  the student portal; unverified values must not ship.

**Day 3 complete.**

**Next:** Day 4 — ingestion. Re-OCR D2, parse with `get_text("dict")`, extract
the study plan table, write the chunker. First day of pipeline code.

---

## Open risks

| Risk | Status |
|---|---|
| Paragraphs cross page boundaries — positional renumbering will silently mis-number D2 if it assumes every paragraph starts at 1 | open, hits Day 4 |
| Table extraction returns wrong values without erroring | open, hits Day 4 |
| Long-context baseline may beat retrieval at 59 pages | expected; publish either way |
| First project of five in 45 days — no schedule slack | ongoing |

**Pattern worth noting:** nearly every risk here is *silently wrong output*,
not a crash. Spot-checking against the source PDFs is the only defence.

---

## Log template

```
## Day N — DD Mon · Title

**Done**
-

**Decided**
-

**Hit**
-

**Next:**
```
