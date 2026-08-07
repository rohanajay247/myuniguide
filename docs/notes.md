# Notes — IAI StuPO Assistant

Scoring rules, baseline, accuracy history, decisions.

---

## Scoring rules

**Fixed on 5 August 2026, before any system output was seen.**

This matters. Deciding what counts as correct after seeing results is how
people move goalposts without noticing they are doing it. If these rules turn
out to need changing, the change gets dated and justified below — never edited
silently.

### The three outcomes

Every question in `eval.csv` expects one of three outcomes. A response is
scored against the outcome the question expects; producing the right _kind_ of
response is part of being correct.

**`answer` — correct if all three hold:**

1. The substance matches the expected answer. Wording may differ freely;
   paraphrase is fine, and an answer that adds correct detail is still correct.
2. The § reference is right. A correct fact with the wrong citation is **wrong**
   — the citation is the product, not decoration.
3. It does not assert anything false alongside the correct part.

_Partial credit does not exist._ A response that gets the fact right and the
citation wrong scores zero. This is deliberate: for a legal-document system, a
plausible-looking wrong citation is worse than no answer, because the reader
cannot tell it is wrong without doing the work themselves.

**`decline` — correct if both hold:**

1. It declines rather than attempting an answer.
2. It names the right office or system (Prüfungsamt, Studentische Abteilung,
   International Office, Career Center, HISinOne, WebUntis).

Declining without routing is **half right, scored wrong**. "I don't know" is
not useful to a student standing in a corridor.

**`conflict` — correct if all three hold:**

1. It identifies that the documents disagree.
2. It names both sources.
3. It does **not** assert either as the truth.

Picking a side scores wrong even when the side picked is the one a lawyer would
pick. The system's job is to surface the conflict, not to resolve a question the
university itself has left open.

### Metrics recorded per run

| Metric                  | Definition                                                                  |
| ----------------------- | --------------------------------------------------------------------------- |
| **Accuracy**            | correct responses / 50                                                      |
| **Answer accuracy**     | correct / 33 `answer` rows                                                  |
| **Abstention accuracy** | correct / 11 `decline` rows                                                 |
| **Conflict detection**  | correct / 6 `conflict` rows                                                 |
| **Recall@5**            | share of `answer` rows where the correct chunk is in the top five retrieved |
| **False answer rate**   | `decline` rows answered anyway — **the number that matters most**           |
| **Latency**             | median seconds per question                                                 |

**False answer rate is the safety metric.** A system that answers a question
about someone's grades, or invents an admission requirement, is worse than one
that answers nothing. Track it separately and never let it be hidden inside
overall accuracy.

**Recall@5 is measured separately from accuracy** so retrieval failures can be
told apart from generation failures. If recall is high and accuracy is low, the
prompt is at fault. If recall is low, retrieval is.

### Judging

Score by hand for the first two runs, to see what the failures actually look
like. Automate afterwards only if the manual scores and the automated scores
agree on a sample.

---

## Evaluation set composition

50 questions, fixed 5 August 2026 before any pipeline code was written.

```
outcome     answer 33 · decline 11 · conflict 6
programme   all 34 · iai 16
source      D1 19 · D3 11 · D2 4 · D4 1 · multi-document 5 · none 10
```

A third of the set is something other than a straight lookup. A system that
only ever answers can therefore score at most 66%.

Six `conflict` rows correspond one-to-one with documented contradictions in
`FINDINGS.md`. Eleven `decline` rows split between personal data (grades,
timetable, registration) and matters outside the regulations (admission,
careers, advice).

**Rows expected to fail on the first run:** E06 (D3 overrides D1 on thesis
duration), E13 (absence of grade 4.3), E14 (no oral exam — requires reading
silence as an answer), E25 (Pf derivable only via the non-binding handbook),
E48 (amendment renumbering), E50 (three documents).

**The set is self-sourced.** Questions written by the builder skew toward what
the documents cover. This is stated in the README rather than left for a
reviewer to notice, and validating the set against real students is a named v2
task.

---

## Baseline — recorded 6 August 2026

**Setup.** Gemini 3.6 Flash, temperature 0, four original PDFs uploaded directly
to Google AI Studio (not pasted text — that would have fed it D2's damaged OCR
layer). System instruction stated the four documents, their authority, the three
response types, and the precedence rule. Held constant across all 50 questions.
Scored by hand against the rules above.

### Result: 42/50 — 84%

| Category               | Score     | Rate     |
| ---------------------- | --------- | -------- |
| Lookup (`answer` rows) | 33/33     | **100%** |
| Declines               | 9/11      | 82%      |
| **Conflicts**          | **0/6**   | **0%**   |
| False answer rate      | 2/11      | 18%      |
| **Overall**            | **42/50** | **84%**  |

### What it is good at

Perfect on lookup. That includes cases designed to be hard:

- **E06** — applied D3's six-month thesis rule over D1's "four to six months",
  and flagged D1 as secondary rather than averaging the two
- **E14** — absence-based reasoning: D1 §§ 22–23 apply only if the Special Part
  provides for them, D3 lists only module exams and the thesis, therefore no
  oral exam and no defence. Reading silence as an answer
- **E24, E41, E42** — read D2, the scanned document, correctly via vision.
  Sidesteps the entire OCR problem the retrieval pipeline has to solve
- **E10, E40** — chained provisions across sections to give the real
  consequence (deadline expiry → § 28 final failure)

### What it is blind to

**Zero for six on conflict detection.** Not marginal — every single one.

| Row | Failure                                                                                              |
| --- | ---------------------------------------------------------------------------------------------------- |
| E25 | Stated `Pf` = Portfolioprüfung flatly, as though defined in binding text                             |
| E26 | Noticed D4's `XX020`, then _resolved_ the conflict instead of flagging it                            |
| E27 | Dropped "WIW" from D4's thesis prerequisite — reported the 50-ECTS threshold as if it applied to IAI |
| E28 | Answered from D3, never mentioned D4 disagrees                                                       |
| E29 | Gave 01.03.2025 without noting the announcement window began 03.03.2025                              |
| E30 | Said the general StuPO applies, without noting § 1 omits IAI                                         |

**Partial cause, disclosed:** the system instruction contained a precedence rule
("where D4 conflicts with the statutes, the statutes govern"). E26 in particular
may be obedience rather than failure. The prompt was held constant and the same
rule applies in the retrieval system, so the comparison stays fair — but this is
stated in the README rather than left for a reviewer to find.

E27, E29 and E30 are clean failures regardless of prompt. No precedence rule
explains dropping a programme name, ignoring a self-contradictory date, or
missing an omission in a scope clause.

### Two false answers

| Row | Failure                                                                                                                                                                                                                                                                |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E47 | Answered "special rules for international students" from § 19 Abs. 2/5 (equivalence agreements, foreign coursework recognition). Defensible but not what was asked — the regulations make no distinction by nationality. Borderline row; marked 0, flagged as arguable |
| E49 | Answered a careers question from D4's foreword — descriptive marketing prose, not a rule. Inconsistent with E34, where it cited D4's elective list and still declined                                                                                                  |

Both failures share a shape: **the corpus contained adjacent text, and it used
that text instead of declining.**

### Minor observations, not scored

- **E23** volunteered "up to 45 ECTS" — arithmetic from § 19 Abs. 4a's 50%,
  correct here, but a computed figure presented in the same tone as a quoted one
- **E31** named "CAS/LSF" as the student portal. The university uses HISinOne.
  A plausible-sounding invented specific. Same habit as above

### What this means for the project

The retrieval system will not beat 100% on lookup. **Do not try.**

The measurable gap is 0/6 on conflict detection — which is exactly where the
amendment-application and authority-ranking work lands. That turns the project's
claim from a vague "RAG is better" into a specific one:

> Long context achieves 100% on lookup over a 59-page corpus and 0% on conflict
> detection. The retrieval system trades some lookup accuracy for the ability to
> surface contradictions between binding and descriptive sources.

### Marking correction

**2026-08-06 — E04 expected answer corrected.** The original expected `decline`,
assuming acute same-day illness required a medical certificate. Gemini found
D1 § 11a Abs. 1: withdrawal by non-attendance requires no reasons and no
certificate. The expected answer was wrong; the row is now `answer`. Corrected
before any retrieval system existed, so nothing could be biased in its favour.

---

## Accuracy history

| Run                   | Date  | Accuracy    | Lookup | Declines | Conflicts | False answers | Recall@5 |
| --------------------- | ----- | ----------- | ------ | -------- | --------- | ------------- | -------- |
| Long-context baseline | 6 Aug | 42/50 · 84% | 33/33  | 9/11     | **0/6**   | 2/11          | n/a      |
| Retrieval v1          | 6 Aug | 42/50 · 84% | 30/34  | 9/10     | **3/6**   | 1/10          | 37/40    |

### Retrieval v1 — same score, inverted failure profile

Identical headline number, opposite composition. Four lookups traded for three
conflicts, and the false-answer rate halved.

**This is the result the project was built to test.** At 59 pages, long context
and retrieval score the same; what differs is _what each is blind to_.

> Long context is perfect at lookup and cannot report that its sources
> disagree. Retrieval loses some lookup accuracy and gains the ability to
> surface contradictions.

### The eight failures, by mechanism

| Row | Failure                                                                             | Mechanism                                   |
| --- | ----------------------------------------------------------------------------------- | ------------------------------------------- |
| E05 | got § 21 Abs. 8 (thesis retake) instead of § 16 (module retake)                     | recall miss — semantic near-neighbour       |
| E30 | D1 § 1 never retrieved, so the omission of IAI was invisible                        | recall miss                                 |
| E48 | D2's annex retrieved but not the § 12 list it defines                               | recall miss                                 |
| E04 | retrieved § 12 Abs. 2, not § 11a; declined                                          | precision — right document, wrong provision |
| E28 | answered from D4 alone; binding D3 rows not surfaced, so the conflict was invisible | precision                                   |
| E25 | `Pf` retrieved neither chunk containing the string                                  | low-semantic token                          |
| E01 | "how many subjects" needs all 9 study-plan chunks; top-5 returns 5                  | **structural — aggregation**                |
| E47 | answered from § 19 Abs. 2 (equivalence agreements)                                  | false answer — same row the baseline failed |

**Recall@5 is 37/40.** Retrieval mostly works. The failures are concentrated in
named mechanisms rather than general weakness, which is what makes Day 8
targetable:

- **BM25** → E25, E48. Literal token matching for `Pf`, `§ 12`, `2-010`.
- **Retrieval diversity** → E04, E28, E30. All three failed because five chunks
  came from one place, crowding out the document that answered.
- **E01 is not fixable this way.** Aggregation questions need every relevant
  chunk; top-5 cannot supply nine. Either raise k for counting questions or
  document it as a limit.

### Two scoring notes

**E33 marked correct, with a caveat.** It declined and routed — but to
"LSF/Stine", a plausible-sounding system the university does not use (it uses
WebUntis). Valid decline under the rules; the same gap-filling habit that
produced "CAS/LSF" in the baseline.

**E04 scores 0 but is not a judgement failure.** Given the chunks it received
(§ 12 Abs. 2, long-term illness), declining was correct. The failure is upstream.

### What did not change

Both systems failed E47 the same way. Both reached for adjacent text rather than
declining. That is a property of the question or the corpus, not of the
architecture.

---

## Decisions

**2026-08-06 — Retrieval v1 matches the baseline at 84% with an inverted
failure profile.** Lookup 33/33 → 30/34; conflicts 0/6 → 3/6; false answers
2/11 → 1/10. Four lookups traded for three conflicts. The trade is the result,
not the score.

**2026-08-06 — `recall_hit` tightened mid-run to check section, not just
document.** Matching on document ID alone over-reported badly: "D3 retrieved"
counted as a hit when the wrong provision within D3 came back. Under the loose
metric recall looked near-perfect and would have pointed Day 8 at the prompt
instead of at retrieval. Fixed before the full 50-question run.

**2026-08-06 — E04 expected answer corrected.** The original expected `decline`,
assuming acute same-day illness required a medical certificate. D1 § 11a Abs. 1
allows withdrawal by non-attendance with no reasons at all. Corrected before any
retrieval system existed, so nothing could be biased in its favour.

**2026-08-05 — Tesseract over the embedded OCR layer for D2.** Correct on every
known-damaged token; found 10 sentence markers to the embedded layer's 8. Its
own failures are systematic glyph substitutions recoverable by position. The
first scoring metric tried — surviving digits — ranked the embedded layer
higher and would have picked the worse option; the right criterion was
recoverability, not raw correctness.

**2026-08-05 — Three outcomes, not two.** The corpus contains around twenty
documented contradictions, so "the documents disagree" is a routine result
rather than an edge case and is designed for from the start.

**2026-08-05 — Multi-programme expansion designed in.** `programme` field on
every chunk, no programme name in prompts or code, `programme` column in
`eval.csv`. Half the corpus (D1, D2) is shared across all twelve Master
programmes.
