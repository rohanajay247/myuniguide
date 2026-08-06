# WORK BREAKDOWN STRUCTURE

## IAI StuPO Assistant

*10-day build plan · revision 4*

**10 working days · ~62 hours · 6 August 2026**

Owner: Rohan
Hochschule Albstadt-Sigmaringen
M.Sc. Industrial Artificial Intelligence · Cohort SS 2026

*Companion to BRD v0.9*

---

### Changes from revision 3

**Days 2 and 3 are complete.** Baseline measured at 42/50 (84%): 100% lookup,
0% conflict detection.

**Day 8 is re-prioritised.** Conflict detection moves from a Day 6 sub-task to
the headline Day 8 feature, because it is the only measured gap. BM25 and
cross-references drop below it.

**Day 9 gains a model comparison** — run the eval against cheaper models and
publish the cost/accuracy table.

**Day 7's target is restated:** the goal is not to beat 84% overall. It is
conflict detection ≥ 5/6 while holding lookup ≥ 28/33.

### Changes from revision 2

**Day 2's OCR comparison is done** — Tesseract wins; see `PROGRESS.md`. Day 2's
remaining carryover is `sources.yaml` alone.

**Day 4 and Day 5 gain the `programme` metadata field**, so multi-programme
expansion doesn't require re-embedding later (BRD v0.8, *Designing for
expansion*).

**Day 2 gains a `programme` column in `eval.csv`.**

### Changes from revision 1

**A sequencing bug is fixed.** Day 3 ran the long-context baseline over all four documents; Day 4 produced D2's OCR. Day 3 therefore depended on Day 4's output, and the headline comparison would have been measured against a broken baseline for one of four documents. **Fix:** the baseline uploads the four PDFs directly to Gemini rather than pasting text. Gemini reads scanned PDFs natively, so D2's damaged text layer never enters the picture — and "upload the PDFs and ask" is a more honest naive baseline anyway.

**Day 1 is complete**, and produced more than planned: all four documents extracted, quality assessed per document, and roughly twenty source defects catalogued in `FINDINGS.md`. Two Day 1 items remain and move to Day 2.

**Day 2's seed count rises** from 6 findings to ~20, which shortens the hardest part of writing the eval set.

**Day 4 gains structural table extraction** for D3's study plan. This was not in revision 1 and is not optional — it is the page most student questions resolve to.

---

## Day 1 — Setup and parsing verdict · ✅ COMPLETE

| Task | Status |
|------|--------|
| Environment: Python 3.12, venv, PyMuPDF | done |
| Repo folders `data/raw`, `pipeline` | done |
| Extract all four PDFs to `data/d*_raw.txt` | done |
| Read and inventory every document | done |
| Parsing verdict per document | done |
| `sources.yaml` | **moved to Day 2** |
| OCR comparison for D2 | **moved to Day 2** |

**Verdict reached:** D1, D3 and D4 extract cleanly with PyMuPDF. D2 is a scan carrying a poor embedded OCR layer — 13,625 characters of German with zero `§` symbols and systematically destroyed sentence numbering. It needs re-OCR, not first OCR.

**Also established:** `get_text("dict")` is required to recover superscripts and indentation; `find_tables()` handles the study plan; never strip a hyphen at end of line.

Full detail in `FINDINGS.md`.

---

## Day 2 — Carryover, then the evaluation set · 8 h

The most important day. Everything downstream is measured against this.

### Carryover from Day 1 · 1 h

| Task | Time | Tools | Status |
|------|------|-------|--------|
| OCR comparison on D2 page 2 | 1 h | Tesseract | ✅ done — Tesseract wins |
| `sources.yaml` — filename, URL, SHA-256, dates, language, authority, text_layer, page count | 1 h | PyYAML | outstanding |

The OCR comparison came in under time and resolved cleanly. Hashes are already
computed and all four source URLs identified; `sources.yaml` is transcription.

### The evaluation set · 6 h

All 50 questions come from the documents and your own experience.

| Source | Count | Time |
|--------|-------|------|
| The ~20 defects and contradictions already in `FINDINGS.md` | 15 | 0.75 h |
| Your own first semester — what you had to ask, look up, or got wrong | 8 | 0.75 h |
| D1 §§ 11–19: registration, withdrawal, exam types, grading, retakes, recognition | 9 | 1.25 h |
| D1 §§ 20–30 + D3 Re § 21: thesis, deadlines, final grade, failing the degree | 6 | 0.75 h |
| D3 study plan + D4: modules, ECTS, exam formats, languages | 6 | 0.75 h |
| Personal-data refusals — grades, timetable, registration status | 3 | 0.25 h |
| Unanswerable — advice, opinions, predictions | 3 | 0.25 h |
| **Write the scoring rules — what counts as correct — before seeing any output** | — | 1.25 h |

**Two rules while writing:**

Write the question first, then look up the answer. If you look first, you'll only write questions you already know are answerable.

Deliberately include 5–8 questions you expect the system to get **wrong** — ones needing two or three documents combined, or where the documents contradict each other. An eval set that scores 95% on the first run was written too kindly.

**Scoring rules must cover three outcomes, not two:** correct answer, correct refusal, and correct conflict-flagging. A question like "what does Pf stand for" has a right answer that is neither a fact nor a refusal — it's *"the abbreviation is defined nowhere in binding text; here is what can be inferred and from where."* Decide now how that scores.

**Columns:** question · expected answer · expected outcome type · source doc · § reference · answerable · category · **programme**

The `programme` column costs one field now (`all` or `iai`) and is what lets you attribute a later accuracy change to retrieval rather than to a larger question set.

**Done when:** `eval.csv` has 50 rows with answers verified against the documents.

---

## Day 3 — Baseline and support files · 6 h · ✅ COMPLETE

| Task | Time | Tools |
|------|------|-------|
| **Upload the four PDFs directly** to a long-context call, run all 50 questions | 2 h | Gemini web UI or API |
| Score the results, record in `notes.md` | 1.5 h | — |
| `glossary.md` — ~60 German↔English terms | 1.5 h | — |
| `routing.yaml` — ~30 topic → office → contact rows | 1 h | — |

**Upload the PDFs, do not paste text.** Gemini reads scanned PDFs natively. Pasting text would feed it D2's damaged OCR layer and corrupt the baseline. This also makes the baseline a fair representation of what a user would actually do.

**Glossary seeds you already have:** `Prüfungsleistung`, `Modulteilprüfung`, `Nachteilsausgleich`, `Prüfungsanspruch`, `Regelstudienzeit`, `Fachsemester`, `Wahlpflichtmodul`, `Satz`/`Absatz`, `Änderungssatzung`, `Bekanntmachung`, `Inkrafttreten`, `Beurkundung`.

**Result: 42/50 — 84%.** Lookup 33/33, declines 9/11, conflicts 0/6. Full
breakdown in `notes.md`.

**Outstanding from this day:** `glossary.md` and `routing.yaml`.

**The number that matters is not 84%.** It is 0/6. Long context is perfect at
lookup and blind to contradiction — that is the gap the rest of the build
targets.

---

## Day 4 — Parse, extract, chunk · 8 h

| Task | Time | Tools |
|------|------|-------|
| Re-OCR D2 using the Day 2 winner | 1.5 h | Tesseract or Gemini Vision |
| Post-OCR repair pass on D2: `$`/`S`/`5`/`9` → `§`, `l`/`z`/`s` → sentence digits | 1 h | Python, regex |
| Parse D1, D3, D4 with `get_text("dict")` — retain font size and x-position | 2 h | PyMuPDF |
| **Structural extraction of D3's study plan table** | 1.5 h | `find_tables()` |
| Chunker: split on § boundaries, carry the § heading into each chunk | 1.5 h | Python, regex |
| Attach `programme` metadata — `all` for D1/D2, `iai` for D3/D4 | 0.25 h | Python |
| Spot-check 10 random chunks for correct § / Abs. / Satz attribution | 0.5 h | — |

**Superscript detection.** Sentence numbers render at a smaller font size than body text. Use the size difference from the dict output rather than trying to regex plain digits — `1,0`, `§ 16 Abs. 1`, `15 Minuten` and `3. Fachsemester` are all indistinguishable from sentence markers in flat text.

**Table extraction caveat, already known:** vertically merged cells collapse — the `CM`/`CEM` and `L+E` columns pile into the first row of each block. Module code, semester, ECTS, examination type and language come through clean. Fix the two bad columns by hand or document the limitation.

**Regex must handle:** letter suffixes (`§ 11a`, `§ 33a`, `§ 38a`), the double form (`§§ 32 bis 43`, `§§ 11 ff`), en-dash vs hyphen in headings, D3's `Re § 2` / `Para. 3` convention alongside D1's `(3)`.

**Do not create phantom sections.** A naive `^§ \d+` regex matches §§ 32–43 in D1's table of contents, but their text is not in that PDF. Twelve empty chunks that match queries and return nothing.

**Strip running headers** — 20 in D1, 6 in D3 — before embedding.

**Risk:** if D2's OCR still loses sentence numbering after the repair pass, stop at 2.5 h total and accept §-level citation for that document. Note it and move on.

**`programme` field is not optional.** `all` for D1/D2, `iai` for D3/D4. Half the corpus is shared across all twelve Master programmes; adding this later means re-embedding everything. Five lines now.

**Done when:** all four documents are chunked with metadata, and the study plan exists as structured rows.

---

## Day 5 — Embed and retrieve · 6 h

| Task | Time | Tools |
|------|------|-------|
| Embedding module with chunk-hash cache, batched calls | 2 h | google-genai |
| Build the index — normalised numpy array + metadata JSONL | 1.5 h | numpy |
| Cosine search, top-k, with `programme in ("all", current)` filter | 1.5 h | numpy |
| Sanity check: query by hand, look at what comes back | 1 h | — |

**Done when:** you can type a question and see the right chunks come back.

---

## Day 6 — Generate answers · 7 h

| Task | Time | Tools |
|------|------|-------|
| Answer prompt: retrieved chunks in, English answer + original text + § reference out | 2.5 h | Gemini or Claude API |
| Abstention — score floor, decline path, route from `routing.yaml` | 1.5 h | Python |
| **Conflict detection — the third outcome** | 1.5 h | Python |
| Refuse personal-data questions | 0.5 h | Python |
| Manual testing on 10 questions | 1 h | — |

**The three outcomes.** Where the documents genuinely contradict each other — D4's thesis prerequisite naming WIW, D1 § 1 omitting IAI, D3's impossible entry-into-force date, D4's semester values conflicting with the binding study plan — the correct answer is to say so, quote both sources, and point to the Prüfungsamt. Not to pick a side, and not to decline.

**Done when:** end-to-end answers with citations, a working "I don't know," and a working "these documents disagree."

---

## Day 7 — Measure · 6 h

| Task | Time |
|------|------|
| Evaluation harness — run all 50, output accuracy, recall@5, abstention rate, conflict-detection rate | 2 h |
| First full run, record against the baseline | 1 h |
| Read every wrong answer and note why it failed | 2 h |
| Fix the cheapest one or two failures | 1 h |

**Done when:** `notes.md` shows baseline vs retrieval side by side.

---

## Day 8 — Depth · 7 h

Do these one at a time and re-run the evaluation after each, recording the change.

| Task | Time | Targets |
|------|------|---------|
| **Conflict detection** — surface disagreements instead of resolving them | 2.5 h | **E25–E30, the measured gap** |
| **Amendment application including renumbering** — apply D2 over D1 on § 12 | 2 h | E48, and the demonstrable engineering |
| BM25 from scratch, fused with vector scores | 2 h | module codes, `Pf`, `12,5` vs `12.5` |
| Glossary query expansion | 0.5 h | cross-lingual recall |
| Cross-reference resolution — D1 ↔ D3 | 0.5 h | baseline already handles these well |

**Conflict detection is now the headline feature, not a side task.** The
baseline scored 0/6 on it. Three of those failures were independent of prompt
wording — dropping "WIW" from a prerequisite, ignoring a self-contradictory
date, missing an omission in a scope clause. This is the one place a retrieval
system with an explicit authority model can beat a model that reads everything.

Cross-reference resolution is de-prioritised because the baseline handled it
well unaided (E10, E40 chained provisions across sections correctly).

**On renumbering.** D2 replaces § 12's list rather than appending to it, and the order changes: `Nr. 4` was *Hausarbeiten* before July 2022 and *Referat* after. A system that treats the amendment as additive gives a wrong answer that looks right. This is the single most demonstrable piece of engineering in the project — make sure the eval set contains a question that catches it.

**Done when:** you have a table of feature → accuracy delta.

---

## Day 9 — Deploy · 6 h

| Task | Time | Tools |
|------|------|-------|
| FastAPI wrapper, one endpoint, index loaded at startup | 1.5 h | FastAPI |
| Rate limits, daily cap, max query length | 1 h | Python |
| Single HTML page: query box, answer, original text, citation, disclaimer | 2 h | HTML/JS |
| Dockerfile with the index baked in, deploy, verify spend cap | 1.5 h | Docker, Cloud Run |
| **Model comparison** — run the eval against 3.6 Flash, Flash-Lite, 2.5 Flash | 1 h | eval harness |

**The model comparison is a portfolio artifact in its own right.** Most projects
pick a model by intuition. With a fixed 50-question set you can produce a table
of accuracy, false-answer rate and cost per 1,000 queries, and choose with
evidence.

**Done when:** a public URL works.

---

## Day 10 — Write it up · 6 h

| Task | Time |
|------|------|
| `FAILURES.md` — 8–10 failing queries, each with a diagnosis | 2.5 h |
| `README.md` — problem, method, baseline vs retrieval, feature deltas, limitations | 2.5 h |
| 8 example questions on the landing page | 0.5 h |
| Final tidy, push | 0.5 h |

**`FINDINGS.md` is a deliverable, not a scratchpad.** It documents twenty source defects found by reading the corpus before writing any pipeline code. Most portfolio RAG projects skip that step entirely. Link it from the README.

**Done when:** someone can read the README and understand what you built, what you measured, and what doesn't work.

---

## If you fall behind

Cut in this order:

1. **Day 8 depth features** — keep BM25 and amendment application, drop the rest
2. **Day 9 deployment** — record a 2-minute demo video instead, deploy later
3. **Eval set down to 30 questions** — last resort

**Never cut:** the evaluation set, the baseline comparison, or the failure analysis. Those three are what make it a portfolio project instead of a tutorial. A local system with real numbers beats a deployed system with none.

---

## Two honest notes

**10 days is tight but real** if you don't gold-plate. The failure mode is spending Day 5 making retrieval "nicer" instead of measuring it. Measure first, improve second.

**This is project 1 of 5 in 45 days.** There's no slack, and the first project always runs longest because you're learning the tooling. If Day 10 arrives and you're on Day 8's work, ship what you have and move on — an honest README saying "hybrid retrieval not yet implemented" is fine. Four finished projects beat five abandoned ones.

**The eval set is self-sourced.** Say so in the README. Questions written by the builder skew toward what the documents cover, and naming that is better than having a reviewer notice. It also gives a clean v2 line: validate the question set against real students.

---

## Tools, all in one place

**Install:** Python 3.11+, Tesseract 5.x with German language data (`deu`), Docker, git

*Windows note: the Tesseract installer does not add itself to PATH. Add
`C:\Program Files\Tesseract-OCR` via Windows environment variables, and set
`pytesseract.pytesseract.tesseract_cmd` in code so the pipeline never depends on
shell configuration.*

**Python packages:** `google-genai`, `numpy`, `pymupdf`, `pyyaml`, `pandas`, `python-dotenv`, `fastapi`, `uvicorn`, `pytesseract`

**Services:** Google AI Studio (Gemini), Google Cloud Run, GitHub. Anthropic API optional.

**Not using:** LangChain, LlamaIndex, LangGraph, n8n, any vector database.

*Note: poppler-utils is no longer required. PyMuPDF handles rendering to images for OCR via `get_pixmap(dpi=300)`.*

---

## Files you'll produce

| File | Contents |
|------|----------|
| `docs/FINDINGS.md` | corpus inventory, extraction limits, source defects — ✅ maintained |
| `docs/PROGRESS.md` | daily task log — ✅ maintained |
| `config/sources.yaml` | the four documents with hashes and dates |
| `eval.csv` | 50 questions with expected answers and outcome types |
| `config/glossary.md` | German↔English terms |
| `config/routing.yaml` | topic → office → contact |
| `docs/notes.md` | scoring rules, baseline, accuracy history, decisions — ✅ maintained |
| `docs/IMPLEMENTATION_GUIDE.md` | how each step was actually done, reproducibly — ✅ maintained |
| `pipeline/` | parse, ocr, chunk, embed, search, answer, evaluate |
| `app/` | FastAPI + Dockerfile + index.html |
| `docs/FAILURES.md` | what doesn't work and why |
| `README.md` | the writeup |
