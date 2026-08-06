# BUSINESS REQUIREMENTS DOCUMENT

## IAI StuPO Assistant

*English-language access to the examination regulations governing the IAI Master's programme*

**Version 0.9 · 6 August 2026**

Owner: Rohan
Hochschule Albstadt-Sigmaringen
M.Sc. Industrial Artificial Intelligence · Cohort SS 2026

*Status: Evaluation set written, baseline measured at 84%. Ready to build ingestion.*

---

### Changes from v0.8

| # | Change | Why |
|---|--------|-----|
| 1 | **Success criteria rewritten around the measured baseline.** | Long context scored 100% on lookup and 0% on conflict detection. Beating it on lookup is not a realistic or interesting goal. |
| 2 | **Conflict detection promoted to the project's primary claim.** | It is the only measured gap, and it is where the amendment and authority work lands. |
| 3 | Model fixed: Gemini 3.6 Flash for baseline and all generation. | Changing models mid-project confounds every accuracy delta. |
| 4 | Model cost/accuracy comparison added as a Day 9 deliverable. | The eval set makes this measurable rather than a guess. |

### Changes from v0.7

| # | Change | Why |
|---|--------|-----|
| 1 | **Multi-programme design constraints added** (see *Designing for expansion*). | Half the corpus is already shared across all 12 Master programmes. Three cheap decisions now avoid a rebuild later. |
| 2 | **OCR decision resolved: Tesseract.** | Beat the embedded layer on every damaged token. Gemini Vision not needed. |
| 3 | **Corpus confirmed complete.** Master General Section stops at 22.1; exactly one amendment; IAI special part at 25.2. | Verified against the Rechtsgrundlagen index. |
| 4 | Prüfungsamt question 6 (further amendments) closed. | No second Master amendment exists. |

### Changes from v0.6

Everything below was established by extracting and reading the documents, not by assumption. Full detail in `docs/FINDINGS.md`.

| # | Change | Why |
|---|--------|-----|
| 1 | **D3 is in English, not German.** The framing "the regulations exist only in German" is wrong for the programme-specific statute. | Verified in extraction. Only D1 and D2 are German. |
| 2 | **D2 is a scan *with* a bad embedded OCR layer**, not a scan with no text. | PyMuPDF returns 13,625 characters of damaged German. Fails silently rather than loudly. |
| 3 | **Amendment renumbering added as a first-class requirement.** | D2 doesn't append to § 12's list, it reorders it. Position 4 means different things before and after July 2022. |
| 4 | **Table extraction added as a required capability.** | D3's study plan is the single highest-value page in the corpus and flat text extraction destroys its column alignment. |
| 5 | **"The documents contradict each other" promoted to a designed answer type.** | ~20 catalogued source defects and conflicts make this a routine outcome, not an edge case. |
| 6 | **`Pf` finding narrowed.** Portfolioprüfung *is* defined in binding text (D2 annex). Only the abbreviation is undefined. | Narrower claim, but defensible. |
| 7 | Baseline resequenced to precede OCR work. | Day 3 previously depended on Day 4's output. |

---

## What we're building

A question-answering system over the examination regulations for the IAI Master's programme.

A student asks a question in English. The system finds the governing provision, answers in English, shows the original text with a section reference, and links the source PDF.

**The language gap is real but narrower than v0.6 stated.** The programme-specific statute (D3) and the module handbook (D4) are in English. The *base rulebook* — which contains most of the rules a student actually needs, on registration, retakes, grading, deadlines and the thesis — exists only in German, as does the amendment that modifies it. So roughly two thirds of the binding text governing an English-taught international cohort is inaccessible to most of that cohort.

**What an answer looks like:**

> **Q:** How long do I have to write my Master's thesis?
> **A:** Six months. If you're delayed for reasons outside your control, the first examiner can extend it by up to two months.
> Source: IAI Supplementary Statute 25.2, Re § 21 Para. 5 → [PDF]

*(§ is the section symbol used in German law. "§ 21" means Section 21.)*

---

## The documents

Four documents, 59 pages.

**D1 — Master StuPO, General Part 22.1** (11.01.2022). 20 pages, German, native text layer, extracts cleanly. The base rulebook for all Master's programmes: exam registration, retakes, grading, thesis, deadlines. Binding.

**D2 — First Amendment to 22.1** (14.07.2022). 6 pages, German, **scanned with a poor embedded OCR layer**. Modifies D1 — notably replacing the list of examination types and adding five new sections on online examinations. Binding.

**D3 — IAI Supplementary Statute 25.2** (28.02.2025). 7 pages, **English**, native text layer, extracts cleanly. IAI-specific rules and the study plan, written as deltas against D1 ("Re § 2", "Re § 12"). Binding.

**D4 — Module Handbook** (07.04.2025). 26 pages, English with German intrusions, native text layer, extracts cleanly. Describes what each module teaches. **Not binding**, and the least carefully produced of the four.

---

## How it works

Six steps: **fetch → parse → chunk → embed → retrieve → generate.**

Documents are fingerprinted by content hash. PDFs are converted to text — three via PyMuPDF, one via re-OCR. The study plan table is extracted structurally rather than as flowing text. Text is split at section boundaries so each chunk is a complete legal provision with its heading attached. Each chunk becomes a vector. When a question arrives it is vectorised too, and the closest chunks are found by cosine similarity.

Everything is cached by content hash, so re-running after a small change only reprocesses what changed.

### Two halves, running at different times

**The build pipeline runs once, offline.** Produces an index: a normalised numpy array plus a metadata file recording document, section, paragraph, sentence, page, language and applicable cohort for each chunk. Small enough to load at startup and ship inside the container image. No database.

**The query path runs per question.** The question is expanded through the German↔English glossary so keyword search can reach German terms from an English question. Vector similarity and BM25 run in parallel and their scores are fused.

Retrieved chunks then pass through a rules layer before generation: amendments are applied over base text, out-of-cohort chunks are filtered, binding documents outrank the Module Handbook where they disagree.

Finally the system checks whether it retrieved anything good enough, and branches three ways — answer, decline, or flag a conflict. That branch is the important one: a confident wrong answer about an exam deadline is worse than no answer.

---

## What the system has to handle

Each of these is required by how the documents are actually put together, not chosen for interest.

**Combining documents.** The current rule is rarely in one place. D3 modifies D1; D2 modifies it too. "What happens if I fail a module exam?" needs three of the four at once.

**Applying amendments, including renumbering.** D2 does not append to § 12's list of examination types — it replaces it, and the order changes. `Nr. 4` was *Hausarbeiten* before July 2022 and *Referat* after. A system that returns the pre-amendment text, or that treats the amendment as additive, gives a wrong answer that looks right.

**Following references.** D1 repeatedly says "the Special Part governs the details" without giving them. The system has to follow that pointer into D3 rather than stopping.

**Knowing which source wins.** Where D4 and the binding documents disagree — and they do, on module codes and on which semester the elective modules fall in — the binding document is correct. The system applies that rule and names the source it used.

**Reading the study plan as a table.** D3 page 6 answers most real student questions — ECTS per module, semester, examination type, teaching language — and nothing else does. Flat text extraction destroys its column alignment in a way that produces *silently wrong* values rather than errors. Structural table extraction is required, not optional.

**Cohort filtering.** D1 § 44: students are governed by the version in force when they started. The right answer depends on enrolment date. This is written into the regulation itself.

**Searching for codes, not just meaning.** Module codes like `2-010` and abbreviations like `Pf` carry almost no meaning for a vector search. BM25 runs alongside and the results are fused. Note that D3 writes `12,5` where D4 writes `12.5` — the tokeniser has to cope.

**Searching across languages.** Questions arrive in English; two of the four documents are German. The system searches German text directly rather than translating the corpus, because the German wording is the legally binding version.

**Knowing when to stop — and when to say the documents disagree.** Three outcomes, not two:

- *Answer* — the documents support a clear response, cited.
- *Decline* — the documents don't cover it; route to the right office.
- *Conflict* — the documents contradict each other. Name both sources, quote both, and point to the Prüfungsamt. Do not pick a side.

The third outcome was an afterthought in v0.6. It is now a designed feature, because the corpus contains around twenty documented defects and contradictions and a student hitting one deserves to be told so.

---

## Scope

**In:** the IAI programme, four documents, questions in English or German, one question at a time.

**Out:** other Master's programmes, student services, life-in-Germany topics, immigration law, anything personal like grades or timetables — those live in HISinOne, not in documents.

### Designing for expansion

Scope stays IAI-only for v1, but the corpus is already half shared:

```
D1  Allgemeiner Teil  → all 12 Master programmes
D2  Amendment         → all 12
D3  IAI Special Part  → IAI only
D4  Module Handbook   → IAI only
```

The university's own numbering partitions the rest — each programme owns a
section of D1's Special Part (§ 32 BWM, § 39 BSA, § 43 DEC), and IAI is § 47,
added later by supplementary statute. Adding a programme therefore means adding
two documents, not rebuilding anything.

Three constraints apply from the start, because they are cheap now and painful
to retrofit:

1. **Every chunk carries a `programme` field** — `all` for D1/D2, `iai` for
   D3/D4. Query-time filter keeps chunks where `programme in ("all",
   current_programme)`. Roughly five lines in the search function; adding it
   later means re-embedding the corpus.
2. **"IAI" never appears in prompts or code, only in data.** The programme is a
   parameter. The glossary and routing table are keyed by topic, not written
   around one course.
3. **`eval.csv` has a `programme` column from row one** — otherwise a later
   accuracy drop can't be attributed to retrieval versus a larger question set.

Known costs of expansion, recorded so they aren't a surprise: most other special
parts are in German (IAI is English because the programme is); question
disambiguation becomes a real feature, since "how many ECTS is the project?"
has twelve answers rather than one; and acquiring and verifying 22 further
documents is the same work Day 1 took for four.

**Explicitly excluded from the corpus:** D4 sections 3 and 4, the qualification and competence matrices. German-labelled tables of bare numbers with a varying count of values per row; there is no reliable way to bind a number to a competence. The exclusion is documented rather than silent.

---

## Why we're building it from scratch

No LangChain, LlamaIndex, LangGraph, n8n, or managed RAG service. Manual chunking, embeddings and cosine similarity, written directly against the APIs.

**n8n** is workflow automation — a working demo that shows nothing about engineering ability. **LangChain and LlamaIndex** earn their keep across many data sources and swappable components; with four documents they'd save perhaps 60 lines out of 200. **LangGraph** handles agent loops; this system answers one question and stops. **Managed services** are right for many businesses and wrong for a portfolio, because nothing gets built.

The real reason is that none of the hard parts above exist in any framework. Applying amendments with renumbering, following references between documents, ranking sources by authority, chunking on section boundaries, extracting a study plan table without silently corrupting it — all of it gets written by hand either way, and a framework just adds a layer to debug through.

**Stack:** Python 3.12, PyMuPDF for PDFs, Tesseract or Gemini Vision for D2, numpy for vectors, Gemini for embeddings and generation, FastAPI and Docker, deployed on Google Cloud Run. The index is a numpy array — a vector database isn't warranted at this size.

**Possible follow-up:** port it to LangChain over a weekend and publish the comparison. Two portfolio pieces from one project.

---

## What success looks like

**The baseline has been measured, and it changes the target.**

Gemini 3.6 Flash, four PDFs uploaded directly, 50 questions, scored by hand:

| Category | Baseline |
|---|---|
| Lookup | **33/33 — 100%** |
| Declines | 9/11 — 82% |
| **Conflicts** | **0/6 — 0%** |
| Overall | 42/50 — 84% |

Long context is perfect at finding and combining provisions. It applied D3's
override of D1 on thesis duration, reasoned from the *absence* of a provision to
conclude there is no oral examination, and read the scanned amendment through
vision — sidestepping the entire OCR problem this pipeline has to solve.

And it reported none of the six documented contradictions. Three of those
failures are independent of prompt wording.

**So the goal is not to beat 84%.** Targets:

- **Conflict detection ≥ 5/6.** The measured gap, and the only one worth having.
- **False answer rate ≤ 1/11.** Baseline was 2/11; both cases used adjacent text
  instead of declining.
- **Lookup ≥ 28/33.** Some loss is acceptable. Retrieval sees fragments where
  long context sees everything; the trade buys contradiction-awareness.
- Recall@5 ≥ 85%, so retrieval failures can be told apart from generation ones.
- Under four seconds, a citation on every answer.

Two non-negotiables beyond the numbers: **the published baseline comparison**,
and **at least eight documented failures** with an explanation of each.

**The claim this project makes:**

> Long context achieves 100% on lookup over a 59-page corpus and 0% on conflict
> detection. The retrieval system trades some lookup accuracy for the ability to
> surface contradictions between binding and descriptive sources.

That is a specific, measured, falsifiable claim. It is more defensible than
"retrieval is better", and it is only available because the baseline was run
before anything was built.

**On model choice.** Gemini 3.6 Flash for the baseline and for all generation —
holding the model constant is what makes later accuracy deltas attributable to
retrieval changes. On Day 9 the same eval runs against cheaper models to produce
a cost/accuracy table. That table is a portfolio artifact in its own right: most
projects pick a model by intuition, this one picks it with evidence.

---

## What I need to know to build this

**Concepts.** Embeddings — what a vector represents and why similar texts land near each other. Cosine similarity — why normalising once at index time turns comparison into a single matrix multiplication. BM25 — why it beats vector search on exact tokens like `2-010`; roughly 40 lines, written by hand. Chunking strategy — why fixed-size chunks break legal text. Recall@k and precision — how retrieval quality is measured separately from answer quality. Content hashing — how the pipeline skips unchanged work.

**Tools.** Python 3.12, PyMuPDF, numpy, PyYAML, pandas, FastAPI, Docker. Tesseract with German language data for D2.

**PDF-specific knowledge established on Day 1:**
- `get_text("dict")` rather than `get_text()`, to recover font size and position — needed to distinguish superscript sentence numbers from ordinary digits, and to recover indentation
- `find_tables()` for the study plan page
- never strip a hyphen at end of line when joining wrapped text

**Accounts.** Google AI Studio key for Gemini. Google Cloud with billing linked for deployment. **A hard spend cap goes on before the first API call, not after.** GitHub, since the repo is part of the portfolio.

**Skills to pick up.** Regular expressions good enough for German section patterns — `§ 12 Abs. 1 Satz 2` and variants, including letter suffixes (`§ 11a`, `§ 33a`) and the double form (`§§ 32 bis 43`). Basic Docker. Prompt design for grounded answers that cite reliably and abstain honestly.

**Non-technical.** Confirm matriculation date and Fachsemester in HISinOne — ground truth for cohort filtering. Get access to the IAI cohort group chat. Send the Prüfungsamt email early; replies take days.

---

## Plan

**Phase 0 — Discovery.** ✅ Done. Documents found, extracted, inventoried. Roughly twenty source defects catalogued in `docs/FINDINGS.md`, each a candidate evaluation question.

**Phase 1 — Evaluation set and baseline.** Write 50 real questions with known correct answers. Run them against a long-context prompt with the four PDFs uploaded directly, and record the score. No pipeline code yet — without a test set, changes to retrieval can be described but not measured.

**Phase 2 — Ingestion.** Re-OCR D2. Parse the rest, extract the study plan structurally, chunk on section boundaries, attach metadata.

**Phase 3 — Retrieval.** Embeddings, search, answer generation with citations, and the abstention path. First real accuracy number.

**Phase 4 — Depth.** BM25, amendment application including renumbering, cross-references, conflict detection. Re-run the evaluation after each addition and record what it changed.

**Phase 5 — Ship.** Deploy, write the failure analysis, write the README.

**Later (v2):** add exactly one other programme — Systems Engineering or BSA. That makes programme filtering genuinely testable rather than theoretical, and it is a weekend rather than a month. If it works cleanly with one, twelve is bookkeeping. Then student services pages, then life-in-Germany guidance.

---

## What gets produced

The corpus (indexed, not republished), a manifest listing every document with source URL and fingerprint, the 50-question evaluation set, a German↔English glossary, a routing table mapping topics to offices, `docs/FINDINGS.md`, a notes file with baseline and accuracy history, the pipeline code, and a README covering method, results and failures.

**One rule about content:** the system only ever indexes official documents. The glossary and routing table are things I wrote — they help the system *find* and *route*, but nothing I wrote is ever quoted back as an answer. When student services content is added later it gets fetched from university pages with URL and date recorded, never summarised.

---

## Risks

**The embedded OCR layer in D2 looks plausible but is wrong.** It produces readable German with zero `§` symbols and destroyed sentence numbering, and nothing errors. *Resolved:* Tesseract on 300 dpi renders beats it on every damaged token. Its own failures are systematic glyph substitutions (`!`→¹, `*`→⁴, `[&8]`→`§`) recoverable by position and regex. Residual risk: paragraphs cross page boundaries, so positional renumbering must not assume every paragraph starts at 1.

**Table extraction fails silently.** Position-counting on the study plan returns `4` where `5` belongs, with no error. *Mitigation:* structural extraction via `find_tables()`, spot-checked row by row against the PDF.

**The baseline may beat retrieval.** *Mitigation:* publish it, then expand the corpus.

**Scope creep back toward covering everything.** *Mitigation:* a document only gets added if it makes an evaluation question answerable.

**A public endpoint burns API quota.** *Mitigation:* per-IP rate limits, daily cap, hard spend limit at the provider.

**Mistaken for an official university service.** *Mitigation:* clear disclaimer, no university logo, no lookalike domain, always link the source.

---

## Still to confirm

Resolved: whether D2 needs OCR (yes — and it ships with a bad one), whether the other three parse cleanly (they do), the real module codes (`2-010`, `1-010`, `55010`, not `XX010`), which OCR engine to use (Tesseract), and whether a newer Master base version or a second amendment exists (neither does — Master has sat at 22.1 since January 2022 while Bachelor has reached 26.1).

Open, for the Prüfungsamt and Studiendekan:

1. Is there a German original of D3, and which language version is legally binding? The filename says *Ausfertigung*, implying the English text is the executed version — unusual.
2. What does `Pf` stand for, and where is it defined for IAI? It covers 30 of 90 ECTS.
3. D4's thesis prerequisite names the wrong programme (WIW, not IAI) and cites a 50-ECTS threshold that appears nowhere in binding text. Error?
4. D3's entry-into-force date (01.03.2025) precedes its own announcement window (03.03–17.03.2025). Which date applies?
5. D1 § 1 lists twelve programmes and IAI is not among them. Oversight, or handled elsewhere?
6. ~~Are there amendments beyond D2?~~ **Closed** — the Rechtsgrundlagen index lists exactly one Master amendment.
7. How does exam registration and module ordering work for a summer-semester intake? D4's `Frequency` field implies SS starters take the "semester 2" modules first, but only the non-binding document says so.

---

## Next action

Write `sources.yaml`, then the 50 evaluation questions. No pipeline code until they exist.
