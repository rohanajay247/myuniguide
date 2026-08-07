# Progress log — IAI StuPO Assistant

Daily record of what was done. Brief by design.

Findings live in `FINDINGS.md`. Plan lives in `WBS_10day_v4.md`.
How things were done lives in `IMPLEMENTATION_GUIDE.md`. All in this `docs/` folder.

|                       |                                                       |
| --------------------- | ----------------------------------------------------- |
| Started               | 4 Aug 2026                                            |
| Plan                  | 10 working days, ~62 h                                |
| Days elapsed          | 8                                                     |
| Phase                 | 4 complete — depth measured, simplest config retained |
| Pipeline code written | OCR, parsing, chunking, embedding, search, generation |

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
- D2 is a scan carrying a _bad embedded OCR layer_ — needs re-OCR, not first OCR
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

- `§` is _section_; `Absatz` is _paragraph_. Translating `§` as "paragraph"
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

## Day 4 — 6 Aug · Ingestion 🔄

**Done**

- `git init`, first commit, branch renamed to `main`
- Repo restructured: `config/`, `docs/`, `data/`, `pipeline/`
- **D2 re-OCR'd with Gemini Vision** — 22 § symbols, 0 unreadable flags,
  amendment items 1–7 correct, sentence markers matching the source

**Decided**

- **Gemini Vision over Tesseract for D2.** Tesseract had better word accuracy
  but could not read superscript sentence numbers — and on page 3 dropped one
  entirely, which kills positional recovery.
- Scripted via the API rather than AI Studio, specifically to pass **no `tools`
  parameter**. AI Studio kept web-searching during transcription and citing
  other universities' regulations, even with grounding switched off.

**Learned**

- **One page is an anecdote.** Page 2 made Tesseract look adequate and made
  positional renumbering look sound. Page 3 killed both.
- **The metric decides the tool.** Scoring on "surviving digits" ranked the
  broken embedded layer highest and would have picked the worst option.
  Tesseract would have won any general OCR benchmark. The right question was
  narrower: does the structure the system depends on survive?
- **Gemini fails invisibly.** Tesseract's errors look broken (`®Für`); Gemini's
  look plausible — it turned amendment item `4.` into `1.` in the manual run,
  invented "CAS/LSF" during the baseline, and computed "45 ECTS" unprompted.
  The more dangerous failure mode.

**Hit**

- Temperature 0 did not give consistent formatting across pages: page 1 returned
  real superscripts (`¹Macht`), pages 2–6 plain digits (`2Dies`). The chunker
  regex must accept both.
- Gemini reformatted the annex table as Markdown despite being told not to
  reformat. Helpful, but disobedient.
- The annex table splits across pages 5 and 6 and must be rejoined — row 11 is
  the Portfolioprüfung definition the `Pf` finding depends on.

**Done (cont.)**

- `pipeline/parse.py` — D1, D3, D4 parsed with `get_text("dict")`
- `pipeline/parse_d2.py` — D2 parsed from the OCR transcription
- `pipeline/parse_table.py` — D3's study plan as 9 structured module records

```
d1_parsed.jsonl     271
d2_parsed.jsonl      73
d3_parsed.jsonl      41
d4_parsed.jsonl      24
d3_studyplan.jsonl    9
```

**Decided**

- **Thresholds derived, not hardcoded.** Body size is the most common font size
  per document; markers are below 80% of it. A fixed `< 7` would have
  misclassified D4, whose body is 10.1pt.
- **Per-document facts in `config/sources.yaml`, structural rules in code.**
  `heading_pattern`, `layout`, `sentence_markers`, `table_marker` are config.
  German legal grammar (`(?!bis\b)`) and contents-page detection are code.
- **D4 parsed at page level** — it has no § structure. It is non-binding and
  loses every conflict, so page granularity suffices. Recorded as
  `layout: pages`, not left as a silent failure.
- **Table hardcoding accepted but guarded.** `parse_table.py` hardcodes the page
  and column indices; a nine-module / 90-ECTS assertion fires if either breaks.

**Hit — seven silent failures, none of which errored**

| Failure                                   | Caught by                        |
| ----------------------------------------- | -------------------------------- |
| `§§ 32 bis 43` read as a section          | looking at the section list      |
| § 44's text filed under § 31              | searching for a known provision  |
| D4: 1 record from 26 pages                | noticing the record count        |
| D2: § 12 missing entirely                 | listing the sections found       |
| D2: Portfolioprüfung merged with a footer | searching for a known definition |

§ 44 is the cohort rule and § 12 is the amendment's central change — both would
have produced confident citations to the wrong place.

**Learned**

- **Automated checks tell you a stage ran; only known facts tell you it worked.**
  Every stage now asserts something verifiable — record count against page
  count, § 12 and Anhang present, nine modules totalling 90 ECTS.
- A PDF encodes appearance, never meaning. Structure is reverse-engineered from
  font size and position, which is why parsers are per-document.

**Confirmed**

- `Pf` covers exactly 30 of 90 ECTS
- Both WPM modules are semester `1+2`; D4 says 2nd semester
- `55010` really is five digits with no hyphen

**Next:** the chunker — merge the five files into one `chunks.jsonl` with stable
IDs, then Day 5's embedding.

---

## Day 5 — 6 Aug · Chunking, embedding, search DONE

**Done**

- `pipeline/chunk.py` — 418 records grouped by paragraph into **191 chunks**,
  each with a citation string (`D1 § 21 Abs. 5 Saetze 1-7`)
- `pipeline/embed.py` — 191 x 768 index, normalised, **573 KB**, cached by
  content hash
- `pipeline/search.py` — cosine search in three lines, with the programme filter

**Decided**

- **Group by paragraph, not by sentence.** A lone sentence often lacks its
  subject — "Sie ist innerhalb von vier bis sechs Monaten zu bearbeiten" never
  says "thesis". Precision moves into the citation instead.
- **`gemini-embedding-001` at 768 dimensions.** GA over the preview
  `gemini-embedding-2`; the numbers have to be reproducible. Multimodal buys
  nothing for a text corpus.
- **Normalise at index time**, so cosine similarity reduces to a dot product and
  search is one matrix multiplication.
- **No vector database.** 573 KB is not a database problem.

**Measured — two results overturned planned approaches**

- **Cross-lingual retrieval works unaided.** German query scored 0.752 on the
  English chunk; English scored 0.742. The glossary drops in priority.
- **Score thresholds cannot drive abstention.** Answerable 0.742, unanswerable
  0.666, boilerplate 0.617 — no separating line. The BRD budgeted a score floor;
  abstention moves into the Day 6 prompt as a judgement instead.
- **Vector search fails on "what is Pf"** — retrieved neither chunk containing
  the string. Two characters carry nothing to embed. Concrete case for BM25,
  with a before/after test ready for Day 8.

**Noted**

- `D1 § 23` (thesis defence) ranks third on thesis queries, but D3 removes the
  defence entirely for IAI. Similarity cannot know a rule is disapplied
  elsewhere — the prompt must handle it. Candidate for `FAILURES.md`.
- 15 chunks exceed 1,500 characters, all D4 pages. Fixed-size embeddings blur
  long, multi-topic text.

**Next:** Day 6 — generation. Chunks in, cited English answer out, plus the
abstention and conflict paths. First point at which the system answers anything.

---

## Day 6 — 6 Aug · Generation DONE

**Done**

- `pipeline/answer.py` — retrieved chunks plus question to `gemini-3.6-flash`,
  cited English answer out. **The system answers end to end for the first time.**
- Same model, same three response types, same temperature as the baseline, so
  the Day 7 comparison measures architecture rather than prompt quality.

**Decided**

- **Abstention lives in the prompt, not a threshold.** Day 5 proved no
  separating score exists. The instruction says directly: passages merely ABOUT
  a topic are not an answer.
- **Override and conflict separated explicitly.** The baseline scored 0/6
  because it resolved disagreements helpfully. An override is resolved by a rule
  (D3 over D1 on thesis duration). A conflict has no rule that resolves it —
  usually an error in the text.

**First results — 3 of 6**

| Question                                 | Expected                | Got                              |
| ---------------------------------------- | ----------------------- | -------------------------------- |
| how long for my thesis                   | ANSWER 6 months         | OK — D3 cited, D1 noted          |
| what grade did I get                     | DECLINE                 | OK — declined and routed         |
| what do I need before starting my thesis | CONFLICT                | OK — both quoted, neither chosen |
| do I have to defend my thesis            | ANSWER no               | DECLINE                          |
| are exams written or coursework          | ANSWER 11 types         | DECLINE                          |
| what does Pf stand for                   | ANSWER Portfolioprüfung | DECLINE                          |

**The conflict case is the significant one.** On that exact question the
baseline answered smoothly, dropping "WIW" and reporting a 50-ECTS threshold as
if it applied to IAI. This system named the error and chose neither source. That
is the measured gap closing.

**All three failures are retrieval, not generation**

```
Q4  needed D3 Re § 3   retrieved 5x D1 § 23
Q5  needed D2 § 12     retrieved D2 Anhang, D3 § 5, D3 § 12
Q6  needed D2 Anhang   retrieved D1 § 31, D4 boilerplate
```

The model behaved correctly each time — declined on incomplete evidence rather
than inventing. **All three are refusals, not wrong answers**, which is the
recoverable direction for a regulations system. The baseline failed the other
way twice.

**Noted**

- Retrieval concentration: Q4 returned five chunks from a single section,
  crowding out the document that answers.
- Absence-based reasoning may be structurally hard for retrieval. Q4's answer
  follows from a rule that is _not there_; the baseline got it right because it
  held all four documents. If this holds across the eval set: **long context
  wins on absence, retrieval wins on conflict.**

**Not fixed, deliberately.** Six hard questions say nothing about the other 44.
Day 7 measures all 50 and separates recall@5 from accuracy.

**Next:** Day 7 — run the full evaluation, compare against the 84% baseline,
read every failure.

---

## Day 7 — 6 Aug · Measure DONE

**Done**

- `pipeline/evaluate.py` — runs all 50 questions, records the response, the
  retrieved citations and a recall flag
- All 50 scored by hand against the rules in `notes.md`

**Result: 42/50 — 84%. Identical to the baseline, opposite failure profile.**

```
                 Baseline    Retrieval v1
Overall           42/50        42/50
Lookup            33/33        30/34
Declines           9/11         9/10
Conflicts          0/6          3/6
False answers      2/11         1/10
Recall@5           n/a         37/40
```

**Four lookups traded for three conflicts, and the false-answer rate halved.**
That trade is the project's result — at 59 pages the two approaches score the
same, and what differs is what each is blind to.

**Hit — a metric that would have misled the whole of Day 8**

`recall_hit` originally matched on document ID alone, so "D3 retrieved" counted
as a hit when the wrong provision within D3 came back. It reported near-perfect
recall on a smoke test where two of five rows had failed on retrieval. Tightened
to check the section before the full run. Under the loose metric, Day 8 would
have been aimed at the prompt instead of at retrieval.

**Failures, by mechanism**

- **Recall misses (E05, E30, E48)** — right provision absent from the top five.
  E05 got § 21 Abs. 8 (thesis retake) rather than § 16 (module retake).
- **Precision (E04, E28)** — right document, wrong provision. E28 answered from
  D4 alone because the binding D3 rows were not surfaced, so the conflict was
  invisible.
- **Low-semantic token (E25)** — `Pf` retrieved neither chunk containing it.
- **Structural (E01)** — "how many subjects" needs all 9 study-plan chunks;
  top-5 returns 5. Aggregation is not fixable by better ranking.
- **False answer (E47)** — answered from § 19 Abs. 2 on equivalence agreements.
  **The baseline failed this same row the same way.**

**Learned**

- Recall@5 at 37/40 means retrieval mostly works. The failures cluster in named
  mechanisms rather than general weakness, which is what makes Day 8 targetable
  rather than speculative.
- The model declined correctly in every case where it lacked evidence. All
  retrieval failures surfaced as refusals, not as wrong answers — the
  recoverable direction for a regulations system.

**Next:** Day 8 — BM25 (targets E25, E48), retrieval diversity (E04, E28, E30),
one change at a time with the eval re-run after each.

---

## Day 8 — 6 Aug · Depth features DONE

**Done**

- `pipeline/bm25.py` — BM25 written from scratch: IDF weighting, term-frequency
  saturation, length normalisation, and a tokeniser that preserves `2-010`,
  `12,5` and `§` where a standard one would destroy them
- `hybrid()` in `search.py` — Reciprocal Rank Fusion of dense and sparse
- Four configurations measured on all 50 questions

**Result: the original configuration won.**

| Configuration                        | Type match | Recall@5  | Conflicts |
| ------------------------------------ | ---------- | --------- | --------- |
| **dense k=5**                        | **42/50**  | **37/40** | **3/6**   |
| hybrid, equal-weight RRF             | 27/50      | 22/40     | 3/6       |
| hybrid, BM25 x 0.25                  | 40/50      | 34/40     | 3/6       |
| dense + binding/conflict prompt rule | 41/50      | 37/40     | 2/6       |

**Two standard improvements built and rejected on measurement.**

**Learned**

- **BM25 works exactly as designed and still hurts here.** In isolation it found
  all three `Pf` chunks where dense found none, and hit `2-020` exactly. But
  equal-weight fusion cost 15 points — seventeen natural-language lookups became
  declines because BM25 matched on _is_, _the_, _how_ and RRF weighted that noise
  as heavily as dense's signal. Down-weighting recovered most but still trailed.
  With 191 chunks and only two or three identifier queries, the wins do not pay
  for the noise.
- **A prompt rule aimed at one row broke two others.** The binding/non-binding
  conflict rule did not fix E28, broke E29, and made E50 over-flag. Teaching the
  model a rule to catch one case taught it to over-apply it.
- **The system is deterministic at temperature 0.** Reverting reproduced the
  original run exactly, row for row — so configuration differences are signal,
  not noise. Worth confirming before reading a two-point change as progress.
- **Conflict detection is stuck at 3/6** across all four configurations. E25 is
  retrieval (the `Pf` link is split across two chunks, neither of which contains
  both halves); E28 and E30 are the model resolving instead of surfacing. Going
  past 3/6 appears to need something other than better retrieval or better
  wording.

**Decided**

Stop after four measured attempts. Further tuning against 50 questions would fit
hyperparameters to the test set. `bm25.py` and `hybrid()` stay in the codebase
as the ablation — the rejection is the interesting part.

**Next:** Day 9 — deploy, or record a demo. Day 10 — `FAILURES.md` and the
README.

---

## Open risks

| Risk                                                                                                                            | Status                       |
| ------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| Paragraphs cross page boundaries — positional renumbering will silently mis-number D2 if it assumes every paragraph starts at 1 | open, hits Day 4             |
| Table extraction returns wrong values without erroring                                                                          | open, hits Day 4             |
| Long-context baseline may beat retrieval at 59 pages                                                                            | expected; publish either way |
| First project of five in 45 days — no schedule slack                                                                            | ongoing                      |

**Pattern worth noting:** nearly every risk here is _silently wrong output_,
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
