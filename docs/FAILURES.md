# FAILURES

What does not work, and why.

Eight of fifty evaluation questions fail. This file explains each one, groups
them by cause, and separates the ones that better engineering would fix from the
ones that are structural limits of retrieval.

Seven of the eight are **refusals** — the system declines when it should have
answered. One is a **wrong answer**. For a system about examination regulations
that is the recoverable direction: "ask the Prüfungsamt" costs a student a
query; a confident wrong thesis deadline costs them more. The long-context
baseline failed the other way twice.

Full evaluation data in `data/eval_1_dense_scored.csv`. Scoring rules in
`docs/notes.md`.

---

## Summary

```
Overall           42/50   84%
Lookup            30/34
Declines           9/10
Conflicts          3/6
False answers      1/10
Recall@5          37/40
```

| #   | Row | Question                                            | Cause               |
| --- | --- | --------------------------------------------------- | ------------------- |
| 1   | E01 | How many subjects are there in the IAI course?      | aggregation         |
| 2   | E25 | What does Pf stand for?                             | cross-chunk join    |
| 3   | E05 | Can I get a failed exam re-evaluated?               | semantic near-miss  |
| 4   | E30 | Does the general StuPO apply to IAI?                | recall miss         |
| 5   | E48 | Are exams written or coursework?                    | chunk boundary      |
| 6   | E04 | I was sick and missed an exam                       | retrieval precision |
| 7   | E28 | Which semester are the electives in?                | retrieval precision |
| 8   | E47 | Are there special rules for international students? | **false answer**    |

---

## Structural — not fixable by better retrieval

### E01 — aggregation

**Question:** "How many subjects are there in the IAI course?"
**Expected:** 9 modules including the thesis.
**Got:** DECLINE.

**No single chunk contains the answer.** There are nine module chunks, one per
module, and none of them says "nine". The answer exists only in the aggregate.

Top-5 retrieval returns five chunks. Even perfect ranking cannot supply nine.

**Why raising `k` is not the fix.** Setting `k=20` would solve this question and
degrade the other forty-nine, which would each receive fifteen additional
irrelevant chunks to sift. That is a trade, not an improvement.

**What would actually work:** routing counting questions to a structured query
over `d3_studyplan.jsonl` rather than to retrieval. The data is already
structured — `module_code`, `ects`, `semester` are fields, not prose. A
`COUNT(*)` answers this exactly and a vector search never will.

### E25 — the join exists in neither chunk

**Question:** "What does Pf stand for?"
**Expected:** Portfolioprüfung — inferable, but stated in no binding document.
**Got:** DECLINE.

Two chunks hold the two halves:

```
D2 Anhang            "11. Portfolioprüfung | Prüfung, die aus mehreren..."
                     — says Portfolioprüfung, never says "Pf"

D3 study plan 2-020  "Module 2-020 Data Science: 5 ECTS ... examination Pf (5)"
                     — says Pf, never says Portfolioprüfung
```

**The link is written down nowhere.** It exists only as an inference across two
documents, one of which is not binding.

Retrieval returns chunks. A fact absent from every chunk cannot be retrieved,
regardless of ranking. Producing the answer requires a reasoning step over
retrieved material, which is a different operation.

BM25 found the three chunks containing the literal string `Pf` — but the ones it
found were where `Pf` is _used_, not where Portfolioprüfung is _defined_. Better
retrieval on both sides still leaves the model to make the connection.

---

## Retrieval — fixable, at a cost

### E05 — semantic near-miss

**Question:** "I failed Artificial Intelligence — can I get it re-evaluated or
must I retake?"
**Needed:** D1 § 16 (retaking a module examination) and § 30 (inspecting papers).
**Got:** D1 § 21 Abs. 8 — retaking the _thesis_.

Almost the same concept, wrong provision. Embeddings place "repeating a failed
examination" close together regardless of which examination is meant, and § 21
Abs. 8 is the more emphatic passage about repetition.

**Likely fix:** retrieve 20 candidates and re-rank them with a model. Standard
practice in production RAG; adds latency and cost. Not attempted here.

### E30 — recall miss on a list

**Question:** "Does the general StuPO apply to Industrial Artificial
Intelligence?"
**Needed:** D1 § 1, which lists twelve programmes and omits IAI.
**Got:** other D1 chunks; § 1 never surfaced.

A bare list of twelve programme names does not resemble the question in
embedding space. It contains no words about applicability or scope — just names.

This is a general weakness: **lists and tables embed poorly**, because an
embedding averages the whole chunk and a list has no thematic centre.

### E48 — chunk boundary

**Question:** "Are exams written or coursework?"
**Needed:** D2 § 12's eleven-item list of examination types.
**Got:** D2's annex (which _defines_ the types) but not the list itself.

The list and the annex defining it are pages apart in the source, so
`group_key = (doc, section, paragraph, page)` put them in separate chunks.

**A boundary that helps here hurts elsewhere.** Merging them would produce one
very large chunk — the same problem D4's 2,800-character pages already have,
where an embedding averages five topics into a point that represents none of
them sharply.

This is why chunking is genuinely hard rather than a parameter to tune.

_Note: the down-weighted hybrid configuration fixed E48 and broke three other
rows. Net worse. See `docs/notes.md`._

### E04, E28 — precision within the right document

**E04** — "I was sick and missed an exam." Needed § 11a Abs. 1 (withdrawal by
non-attendance requires no reasons). Got § 12 Abs. 2 (long-term illness,
four weeks' notice). Right document, wrong provision — and given what it
received, declining was the correct behaviour. **The failure is upstream of the
model.**

**E28** — "Which semester are the compulsory-elective modules in?" D3's study
plan says `1+2`; D4 says 2nd semester. The system answered from D4 alone,
because the binding D3 rows were not retrieved — **so it never saw that a
conflict existed.** Conflict detection cannot fire on a conflict it cannot see.

---

## The one wrong answer

### E47 — answered from adjacent text

**Question:** "Are there special rules for international students?"
**Expected:** DECLINE — the four documents make no distinction by nationality.
**Got:** an answer citing § 19 Abs. 2 (equivalence agreements) and § 19 Abs. 5
(recognition of coursework completed abroad).

Those provisions exist and do concern foreign qualifications. But recognising a
foreign degree is not the same as having different rules as an international
student, and the honest answer is that the regulations make no such distinction.

**The long-context baseline failed this same row the same way**, which suggests
the cause is the question or the corpus rather than the architecture. The row is
arguably ambiguous; it is scored wrong and flagged as arguable rather than
quietly rewritten.

**The general shape:** both systems reached for topically adjacent text instead
of declining. This is the failure mode that matters most for a regulations
system, and it is the one the abstention prompt is aimed at. One in fifty, down
from the baseline's two in eleven declines.

---

## What retrieval cannot do, stated plainly

Retrieval assumes **the answer lives in a passage**. True for most questions,
false for four kinds:

| Kind                         | Example                    | Why                                             |
| ---------------------------- | -------------------------- | ----------------------------------------------- |
| **Aggregation**              | "how many modules"         | the answer is in the count, not in any chunk    |
| **Cross-chunk joins**        | "what does Pf mean"        | the link is between chunks, not inside one      |
| **Precision within a topic** | § 16 vs § 21 Abs. 8        | embeddings capture subject, not which provision |
| **Absence**                  | "must I defend my thesis?" | a rule that is _not there_ cannot be retrieved  |

Long context sidesteps all four by never chunking — which is why the baseline
scored 33/33 on lookup and got the absence question (E14) right.

**That is the trade this project measures.** Not accuracy: _what kind of question
each architecture can answer at all._

---

## Beyond the eval set

**D4's chunks are too large.** Fifteen chunks exceed 1,500 characters, all
module-handbook pages, because D4 has no § structure to split on. An embedding is
a fixed-size vector regardless of input length, so a 2,800-character page
covering workload, learning outcomes, contents, literature and examination form
averages into a point that represents none of them sharply.

**Conflict detection is stuck at 3/6** across four measured configurations —
dense, two hybrid weightings, and a prompt change. E25 is retrieval; E28 and E30
are the model resolving rather than surfacing. Neither retrieval nor prompt
wording moved it. Improving 0/6 → 3/6 was the architectural gain; getting past
3/6 appears to need something else.

**Rate-limit counters reset on container restart.** They live in memory.
Mitigated with `--min-instances=1 --max-instances=1` so one long-lived container
holds one counter — mitigated, not solved. A shared store would fix it properly.

**The evaluation set is self-written**, so it skews toward what the documents
cover and toward failures its author could imagine. Validating it against real
student questions is the most valuable single improvement available and has not
been done.

---

## What would be tried next

In order of expected value:

1. **Route aggregation questions to structured data.** The study plan is already
   a table with typed fields. Counting and summing questions should query it
   rather than search prose. Fixes E01.
2. **Re-rank a larger candidate set.** Retrieve 20, re-rank with a model, keep 5.
   Standard practice; targets E05, E30, E04, E28.
3. **Validate the eval set with real students.** Removes the largest known bias.
4. **Add a second programme.** Makes the `programme` filter genuinely testable
   rather than theoretical.

**Not planned:** further tuning of retrieval weights or prompt wording. Four
measured attempts produced no improvement over the simplest configuration, and
tuning further against fifty questions would fit the hyperparameters to the test
set rather than the task.
