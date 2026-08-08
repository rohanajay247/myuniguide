# MyUniGuide

**Question answering over German university examination regulations, in English,
with legal citations.**

🔗 **[Live demo](https://myuniguide-703440239913.europe-west1.run.app)** ·
[Failure analysis](docs/FAILURES.md) ·
[Measurements](docs/notes.md) ·
[Corpus findings](docs/FINDINGS.md) ·
[Implementation guide](docs/IMPLEMENTATION_GUIDE.md)

---

## The finding first

I built a retrieval system over my Master's programme's examination regulations.
Before building anything, I measured a baseline: upload all four PDFs to Gemini
and ask directly.

**Both score 84%. The failure profiles are opposite.**

|                             | Long context | Retrieval   |
| --------------------------- | ------------ | ----------- |
| **Overall**                 | 42/50 · 84%  | 42/50 · 84% |
| Lookup                      | **33/33**    | 30/34       |
| Declines                    | 9/11         | 9/10        |
| **Contradictions detected** | **0/6**      | **3/6**     |
| False answers               | 2/11         | 1/10        |

Long context is perfect at finding facts and **structurally blind to its sources
contradicting each other**. In one case it reported a thesis prerequisite from a
different degree programme as though it applied to mine, silently dropping the
programme name from the quoted text.

So at 59 pages, retrieval does not buy accuracy. It buys the ability to say
_"these documents disagree."_

That is the claim this project makes, and it is only available because the
baseline was measured before anything was built.

---

## The problem

The M.Sc. Industrial Artificial Intelligence at Hochschule Albstadt-Sigmaringen
is taught in English to an international cohort. The regulations that govern it
are not straightforward to read:

- **Four documents that modify each other.** A general statute, an amendment to
  it, a programme-specific supplement, and a module handbook.
- **Two of the four are German**, including the base rulebook containing most of
  what a student actually needs — registration, retakes, grading, deadlines.
- **One is a scan** with a broken embedded OCR layer: zero `§` symbols across six
  pages.
- **Citations are three levels deep.** `§ 12 Abs. 2 Satz 3` means section 12,
  paragraph 2, sentence 3. Sentence-level precision is the unit of legal
  reference, so the pipeline has to preserve it.

And the documents contain around twenty genuine defects — contradictions,
placeholder module IDs never filled in, a date that precedes its own
publication. Catalogued in [`docs/FINDINGS.md`](docs/FINDINGS.md).

---

## Method

**Evaluation before implementation.** 50 questions with verified answers, written
before any pipeline code, with the scoring rules fixed before any output was
seen. Three outcome types, not two — `answer`, `decline`, and `conflict`, because
a corpus with twenty contradictions makes "the documents disagree" a routine
result rather than an edge case.

**Baseline before building.** The long-context comparison ran first. Without it
there is no way to know whether retrieval earned its place.

**Every change measured.** Four configurations were built and evaluated on all 50
questions. Three were rejected.

---

## What got rejected

| Configuration                        | Type match | Recall@5  | Conflicts |
| ------------------------------------ | ---------- | --------- | --------- |
| **dense k=5** — _shipped_            | **42/50**  | **37/40** | **3/6**   |
| hybrid, equal-weight RRF             | 27/50      | 22/40     | 3/6       |
| hybrid, BM25 weighted 0.25           | 40/50      | 34/40     | 3/6       |
| dense + binding/conflict prompt rule | 41/50      | 37/40     | 2/6       |

**BM25 was written from scratch and then removed from the pipeline.** In
isolation it does exactly what it should — it found all three chunks containing
the literal token `Pf` where vector search found none, and hit `2-020` exactly.
But fusing it at equal weight cost 15 percentage points: seventeen
natural-language lookups became refusals because BM25 matched on _is_, _the_,
_how_, and rank fusion weighted that noise as heavily as the vector signal.

With 191 chunks and only two or three identifier queries, the wins do not pay for
the noise. `pipeline/bm25.py` and `hybrid()` remain in the repo as the ablation.

**A prompt rule aimed at one failing question broke two passing ones.** Adding
_"if a binding and a non-binding passage disagree, that is a CONFLICT"_ did not
fix the row it targeted, and dropped conflict detection from 3/6 to 2/6.

Reverting reproduced the original run exactly, row for row — so at temperature 0
the system is deterministic and these differences are signal rather than noise.

---

## What doesn't work

Eight of fifty fail. **Seven are refusals; one is a wrong answer.** For a system
about examination rules that is the recoverable direction — the baseline failed
the other way twice.

Retrieval assumes the answer lives in a passage. That holds for most questions
and fails for four kinds:

| Kind                         | Example                    | Why it fails                                                                     |
| ---------------------------- | -------------------------- | -------------------------------------------------------------------------------- |
| **Aggregation**              | "how many modules?"        | nine chunks hold the answer; top-5 returns five                                  |
| **Cross-chunk joins**        | "what does `Pf` mean?"     | one chunk says _Portfolioprüfung_, another says `Pf` — neither contains the link |
| **Precision within a topic** | § 16 vs § 21 Abs. 8        | embeddings capture subject, not which provision                                  |
| **Absence**                  | "must I defend my thesis?" | the answer follows from a rule that _is not there_                               |

Long context sidesteps all four by never chunking. Full diagnosis per row in
[`docs/FAILURES.md`](docs/FAILURES.md).

---

## Everything failed silently

Eight times across OCR, parsing, measurement and deployment, a stage produced
plausible output that was wrong. **None raised an error at the point of failure.**

| Stage                 | Failure                                              | Caught by                                |
| --------------------- | ---------------------------------------------------- | ---------------------------------------- |
| Flat table extraction | ECTS read from the wrong column                      | comparing distances across rows          |
| Tesseract OCR         | dropped a sentence marker entirely                   | counting markers against the source      |
| D1 parser             | `§§ 32 bis 43` parsed as a section                   | reading the section list                 |
| D1 parser             | § 44's text filed under § 31                         | searching for a known provision          |
| D4 parser             | 1 record from 26 pages                               | noticing the record count                |
| D2 parser             | § 12 missing entirely                                | listing the sections found               |
| Evaluation            | a recall metric that matched document, not provision | comparing against manually-read failures |
| Cloud Build           | the index never uploaded                             | reading the build's file list            |

Every one was caught by checking a **specific expected fact** — not by an error
message, and not by aggregate metrics. That is what `docs/FINDINGS.md` is for:
it is the checklist. Each pipeline stage now asserts something it can verify
itself — record count against page count, nine modules totalling 90 ECTS, § 12
and the annex present.

The last two are the same lesson in different clothing. A recall metric that
matched only the document reported near-perfect retrieval on a run where two of
five rows had failed _because of_ retrieval. And a rule written in `.gitignore`
silently governed a cloud build, because `.gcloudignore` did not exist and gcloud
falls back to it — three edits to `.dockerignore` changed nothing.

---

## How it works

Four documents go in. A question comes out the other end with a legal citation
attached.

```
                    ┌─── done once, offline ───┐
   4 PDFs  →  text  →  191 chunks  →  573 KB index
                                           │
   question  →  ────────────────────────►  find 5 closest  →  Gemini  →  answer
                    ┌─── per question ───┐
```

### 1. Read the PDFs

A PDF stores _appearance_, not meaning. There is no "this is a heading" flag —
only "this text is 6pt at position x=70". So structure has to be worked out from
how things look.

That turns out to be the key to a real problem. In German legal text, sentences
are numbered with tiny raised digits, and once extracted they are
indistinguishable from ordinary numbers:

```
1,0 ; 1,3 ; 1,7          grades
§ 16 Abs. 1 Satz 1       a cross-reference
15 Minuten               a duration
1Die Studierenden        a sentence marker  ← only this one is special
```

But on the page the marker is **smaller** — 6pt where the body text is 9pt. Read
the font size and they separate cleanly. The threshold is worked out per document
rather than hardcoded, since one document sets its body text at 10.1pt.

**The scanned document was a separate problem.** It arrived with an OCR layer
already embedded — and that layer was worse than nothing, because it produced
readable German that was silently wrong, with not a single `§` symbol in six
pages. Tesseract read the pages again and got the words right but dropped a
sentence number entirely. Gemini Vision kept all of them. That decision mattered
because sentence numbers are the citation unit — losing one shifts every citation
after it, invisibly.

**The study plan needed different handling.** It is a table, and flattening a
table to text destroys the columns. Measured across five consecutive rows, the
ECTS value sat 8, 8, 9, 10 and 8 positions after the module code — so counting
positions returns the wrong number without any error. Extracting it as a table
keeps the columns intact.

### 2. Cut it into pieces

The system does not read whole documents. It cuts them into 191 pieces and looks
at five per question.

**Why not one sentence per piece:** a lone sentence often loses its subject.

> _"Sie ist innerhalb von vier bis sechs Monaten zu bearbeiten."_

_It_ is the Master's thesis — but the word "thesis" is not in that sentence, so a
search for "how long for my thesis" would never match it.

So pieces are grouped by paragraph, and precision moves into the citation:
`D1 § 21 Abs. 5 Sätze 1–7` says exactly which sentences the piece contains.

### 3. Turn meaning into numbers

Each piece goes through an embedding model, which returns 768 numbers
representing what the text means. Pieces with similar meaning get similar
numbers.

This is what makes the language barrier disappear. _"How long do I have?"_ in
English and _"Bearbeitungszeit"_ in German land close together, because the model
encodes meaning rather than words. Measured: a German question scored **0.752**
against the English chunk that answers it; the English version of the same
question scored **0.742**.

All 191 sets of numbers form a 573 KB array. That is the entire search index —
small enough to load into memory, which is why there is no database.

### 4. Find the closest five

The question goes through the same model. Then finding relevant pieces is one
multiplication — the question's numbers against all 191 at once.

```python
scores = index @ question      # (191, 768) @ (768,) → 191 scores
```

No loop, no database, no search engine. Every vector was scaled to length 1 when
the index was built, which is what reduces the comparison to a plain
multiplication.

### 5. Write the answer

The five pieces and the question go to Gemini with instructions to do one of
three things:

|              |                                                         |
| ------------ | ------------------------------------------------------- |
| **ANSWER**   | the passages answer it — answer and cite the provision  |
| **DECLINE**  | they don't — say so and name the office to contact      |
| **CONFLICT** | they contradict each other — quote both, choose neither |

**Deciding between these is the model's judgement, not a score.** The obvious
approach — refuse when the best match scores below some threshold — was tried and
measured, and there is no threshold that works:

```
answerable question       0.742
unanswerable question     0.666
pure page boilerplate     0.617
```

Set the line at 0.68 and good answers get refused. Set it at 0.60 and boilerplate
counts as an answer. The reason is that similarity cannot tell _"there is text
about this topic"_ from _"this question is answerable"_ — asking for a grade
retrieves chunks about that module, which are genuinely the most similar text in
the corpus and contain no grade.

Two rules sit alongside: a **more specific rule wins** (the programme statute
gives six months for the thesis, the general one says four to six — the answer is
six), and the **module handbook is not a source of rules**, so where it disagrees
with a statute that is a conflict to report rather than resolve.

### The stack

Python 3.12, PyMuPDF, numpy, Gemini (`3.6-flash` for answers,
`embedding-001` at 768 dimensions), FastAPI, Docker, Cloud Run.

**No LangChain, no LlamaIndex, no vector database.**

## Why no framework

A framework would have saved roughly 60 lines of loading, splitting and
retrieval boilerplate out of ~250.

It would not have helped with any of the eight failures, and it would not have
supplied the parts that took the time: distinguishing superscript sentence
numbers by font size, applying an amendment that _renumbers_ a list so `Nr. 4`
means different things before and after July 2022, ranking a binding statute
above a descriptive handbook, or extracting a table that silently returns values
from the wrong column.

Those get written by hand either way. Building the retrieval core manually is
also what made the ablation possible — swapping fusion weights and measuring the
result is trivial when you wrote the fusion.

---

## Reproducing

```bash
python -m venv .venv && .venv/Scripts/activate      # or source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                                 # add your GEMINI_API_KEY

# The four source PDFs are not in this repo — they belong to the university.
# config/sources.yaml has the URLs and SHA-256 hashes. Download into data/raw/.

python pipeline/ocr_d2.py          # re-OCR the scanned amendment
python pipeline/parse.py           # D1, D3, D4
python pipeline/parse_d2.py        # D2, from the OCR text
python pipeline/parse_table.py     # the study plan, structurally
python pipeline/chunk.py           # 418 records -> 191 chunks
python pipeline/embed.py           # build the index
python pipeline/evaluate.py        # run all 50 questions

python pipeline/answer.py "how long do I have to write my thesis"
uvicorn app.main:app --reload
```

---

## Honest limitations

**59 pages fits in a context window**, so retrieval had a weak case here by
construction. That is the finding, not a flaw in the experiment — but it means
this result should not be generalised to corpora too large to fit.

**The evaluation set is self-written**, which biases it toward what the documents
cover and toward failures its author could imagine. Validating it against real
student questions is the single most valuable improvement available and has not
been done.

**One wrong answer in fifty.** The deployed demo carries a visible notice: it is
a student project, not an official university service, and every answer links to
the provision it came from.

**Rate-limit counters are in memory** and reset when the container restarts.
Mitigated by pinning to a single instance, not solved.

**Scope is one programme.** Half the corpus (the general statute and its
amendment) already applies to all twelve Master's programmes, and every chunk
carries a `programme` field, so adding another means adding two documents. It has
not been tested.

---

## Repository

```
app/            FastAPI service and the web page
pipeline/       OCR, parsing, chunking, embedding, search, generation, evaluation
config/         sources manifest, German↔English glossary, routing table
data/           chunks, index, and five evaluation runs
docs/           findings, failures, measurements, implementation guide
eval.csv        50 questions with verified answers
```

The source PDFs are excluded — they are the university's. `config/sources.yaml`
records the URL, issue date, authority and SHA-256 of each, so the corpus can be
reconstructed exactly.
