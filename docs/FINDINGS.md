# Corpus findings — IAI StuPO Assistant

Running log of what the documents actually look like, established by
extraction rather than assumption. Everything here was verified against
PyMuPDF output, not guessed.

Last updated: end of Day 1. All four documents extracted and inventoried.
No pipeline code written yet.

---

## Status by document

| ID | Document | Pages | Language | Text layer | Extracted |
|----|----------|-------|----------|------------|-----------|
| D1 | Master StuPO 22.1 (11.01.2022) | 20 | DE | native | yes — clean |
| D2 | First Amendment (14.07.2022) | 6 | DE | scan + **bad embedded OCR** | yes — unusable as-is |
| D3 | IAI Supplementary Statute 25.2 (28.02.2025) | 7 | **EN** | native | yes — clean |
| D4 | Module Handbook (07.04.2025) | 26 | EN (+ some DE) | native | yes — clean |

---

## Corrections to BRD v0.6

**D3 is in English, not German.** The BRD's framing — that binding
regulations exist only in German — is wrong for the programme-specific
document. Only D1 and D2 are German.

- Open question: does a German original of D3 exist, and if so which
  version is legally binding? The filename says *Ausfertigung* (official
  execution), which would imply the English text is binding. Unusual.
  → Prüfungsamt.

**No `\x02` hyphen corruption.** An earlier warning about hyphens being
replaced by a control character was wrong — it came from a different
extractor. PyMuPDF preserves every hyphen in D1 (74 clean `Modul-`
occurrences, zero `Modulbzw`). Nothing to fix.

**Real module codes** are `2-010`, `2-020`, `2-030`, `2-040`, `1-010`,
`1-020`, `1-030`, `1-040`, `55010` — not the `XX010` placeholders printed
in D4's overview page.

---

## Extraction limitations (real, need handling)

### Superscript sentence numbers lose their formatting

German legal text numbers sentences (`Satz`) with superscripts. These
extract as ordinary digits, indistinguishable from other numbers:

```
1,0 ; 1,3 ; 1,7          grades
§ 16 Abs. 1 Satz 1       cross-reference
15 Minuten               duration
3. Fachsemester          ordinal
4§ 12 Abs. 2 ...         superscript 4, then a reference
```

No regex can separate these from a flat string. The information survives
in the PDF as font size — superscripts render smaller.

**Fix:** use `page.get_text("dict")` instead of `page.get_text()`. Gives
font size, position and flags per span. Needed before the chunker.

### Indentation is discarded

`(1)` paragraphs, `-` bullets and `1.` `2.` numbered lists all flatten.
Nesting is lost. Same fix — the `x0` coordinate in the dict output records
how far each line was indented.

### Tables flatten into unusable line sequences

D3 page 6 (the study and examination plan) is the highest-value page in
the corpus — it answers most real student questions (ECTS per module,
which semester, exam type, teaching language) and nothing else does.

Flat extraction destroys column alignment. Distance from module code to
its ECTS value, per row:

```
2-010 → 8      2-020 → 8      2-030 → 9
1-010 → 10     1-020 → 8
```

Three causes, none of them "a cell is legitimately empty":
- row 1 merged code and name onto one line; row 2 split them
- long module names wrap, adding a line to that row only
- blank-line count doesn't track empty-cell count

Position-counting will return wrong values **silently** — `4` instead of
`5` — with no error raised.

**Fix:** `page.find_tables()`. Verified working: returns 20 rows × 15
columns with module code, semester, ECTS, exam type and language correct
on every row.

Known limitation: vertically merged cells collapse. The `CM/CEM` and
`L+E` columns pile into the first row of each block (`'CM CM CM CEM'`).
The columns that matter came through clean. Fix by hand or document it.

### Line-break hyphenation — do not strip the hyphen

D4 hyphenates across line breaks where D1 and D3 mostly don't:

```
in-\nprocess          CRISP-\nDM
self-\norganization   research-\noriented
```

Both hyphen and newline survive, which is correct. Cleanup rule: **join
the lines, leave the hyphen alone.** Stripping it yields `inprocess`,
which matches nothing. The same rule keeps D1's German compounds intact
(`Modul-\nbzw.`).

D4 also writes `CRISP-DM` in one place and `CRISP DM` four pages later.
Source inconsistency, not extraction.

### Verify against the file, never against a rendering

Three separate times, text pasted into a chat showed corruption
(`Modulbzw`, `ofthe`, `forthe`, `Contacttime`, `CRISPDM`) that did not
exist in the PyMuPDF output. Different extractors fail differently. When
something looks broken, grep the actual `.txt` before believing it.

### Justified text can break one word per line

D3 page 4, § 11 section:

```
examinations
within
a
module
to
which
```

The paragraph is fully justified with very wide word spacing, so each word
read as a separate line. Harmless after whitespace collapsing — but fatal
if the chunker ever splits on line breaks.

---

## Document structure notes for the chunker

**Running headers repeat on every page.** D1: `Master-StuPO vom
11.01.2022 <n>` × 20. D3: `Faculty of Engineering | ... | 25.2 page n of
7` × 6, but absent from the table page. Strip before embedding — noise
pollutes both vectors and BM25.

**Printed page numbers restart.** D1's *Besonderer Teil* returns to page 1.
"Page 2" is ambiguous. Cite by PDF page index, not printed number.

**The table of contents produces phantom sections.** A naive `^§ \d+`
regex matches §§ 32–43 in D1's TOC, but their text isn't in this PDF
(§31 says "siehe §§ 32 bis 43" — published separately). Twelve empty
chunks that match queries and return nothing.

**Section regex needs to handle:**
- letter suffixes: `§ 11a`, `§ 33a`, `§ 38a`
- double symbol: `§§ 32 bis 43`, `§§ 11 ff`
- en-dash vs hyphen: § 16's title uses `–` in the body, `-` in the TOC
- D3 uses `Re § 2` for references and spells out `Para. 3` where D1 writes
  `(3)` — two conventions, same meaning

**Empty sections exist and are real.** D1 § 17 is "nicht belegt". § 19(3)
is "Entfällt".

---

## Defects in the source documents

These are the university's errors, not extraction problems. Each is a
candidate evaluation question.

**D1 § 30 sentence numbering is broken.** Runs `1`, `3`, `3` — no 2, and
3 twice. Satz numbering is therefore not guaranteed sequential; code that
assumes it is will break.

**D1 § 1 does not list IAI.** Twelve Master's programmes named.
Industrial Artificial Intelligence is not among them. So the base
regulation's own scope clause doesn't cover the programme it governs.

**D1 § 31 defines no `Pf`, `CM` or `CEM`.** Exam abbreviations listed:
`Kx, Mx, R, Ha, La, Pb, Pr, Ma, X`. D3 § 31 adds only `XxB`. But D3's
study plan uses `CM` and `CEM` in every row, and `Pf` in three. Three
abbreviations the programme depends on are defined nowhere in binding text.

**`Pf` covers 30 of 90 ECTS.** [Revised — see D2 section. The exam
*type* Portfolioprüfung is defined in binding text. Only the
abbreviation `Pf` is undefined.] 2-020 (5), 2-030 (12.5), 1-030 (12.5) —
exactly one third of the degree, under an abbreviation with no definition.
The *exam type* Portfolioprüfung is defined, in D2, in German, inside the
scanned document. The abbreviation-to-name link is what's missing.

**D3's dates contradict each other, on the same page.** Article II: enters
into force the day after publication. Publication ran 03.03.2025 →
17.03.2025. Then: "Date of entry into force: 01.03.2025" — two days before
publication began.

**`55010`.** Every other module code is `n-0n0`. The thesis is five digits,
no hyphen. Typo or different scheme — verify visually against the PDF.

**D4's module overview prints `XX010`, `XX020`, `XX030`** — unfilled
placeholders. Real codes are in D3. Clean test of the binding-source-wins
rule.

**D1 § 12 lists seven exam types. D2 replaces the list with eleven,**
adding Lerntagebuch and Portfolioprüfung. This is the concrete
amendment-application case for Phase 4.

**D1 § 44 is the cohort rule.** The version in force when you started
governs you.

### D4 specifically

**Module IDs are ambiguous, not merely unfilled.** `XX010` appears 8
times and denotes *two different modules* — Digital Technology and
Management, and Artificial Intelligence. Same for XX020, XX030, XX040.
"What is XX010" has no answer. Real codes exist only in D3.

**D4 contradicts itself on its own codes.** The overview (section 2)
lists `XX030` twice in the AI group where the module description says
`XX040`.

**Field labels are inconsistent, across two languages.** The Thesis
module switches to German mid-table (`1 Lehrveranstaltung(en) / keine /
Sprache`) where every other module uses `1 Course(s) / Language`. The
literature heading appears four ways: `Recommended literature` ×4,
`Recommended reading` ×3, `Recommended Literature` ×1, `Empfohlene
Literatur` ×1. Label-based field parsing will silently skip modules.

**Thesis prerequisite names the wrong programme.** Verbatim: "At least
50 ECTS credits completed in the Master's program in Industrial
Engineering (WIW); further details are specified in the study and
examination regulations." WIW is a different programme, and D3 states no
50-ECTS threshold at all.

**Semester conflicts with D3.** D4 puts the compulsory elective modules
in the 2nd semester; D3's study plan says `1+2` for both `1-040` and
`2-040`. D3 is binding and wins.

**Decimal separators differ.** D3 writes `12,5`, D4 writes `12.5`. BM25
will treat them as distinct tokens.

**Sections 3 and 4 (qualification / competence matrices) are unusable.**
German-labelled tables of bare numbers with a varying count of values
per row — 9 on one, 11 on the next. No way to bind a number to a
competence. Exclude from the corpus and document the exclusion.

**The `Pf` chain closes, but only through the non-binding document.**
D3 marks Data Science as `Pf (5)`; D4 gives its examination form as
`Portfolio examination – Graded (5)`. Same module, same weight, so the
mapping is derivable — by cross-referencing binding text against a
handbook that explicitly isn't binding. Good eval question with a subtle
correct answer: inferable, but not stated in any binding source.

**The `Frequency` field answers the intake-order question and exists
nowhere else.** AI and Data Science are `Annual / winter semester`;
Digital Technology and Operational Excellence are `Annual / summer
semester`. An SS intake therefore meets the "semester 2" modules first.
Only D4 records this, and D4 is not binding.

**One thing the documents agree on:** workload is exactly 30 h per ECTS
throughout D4 (150/5, 375/12.5, 900/30), which is what D1 § 4 Abs. 1
requires.

### D2 specifically — the embedded OCR layer is unusable

D2 is a scan, but it is **not** a blank text layer. PyMuPDF returns
13,625 characters: someone OCR'd the scan before publishing and embedded
the result. That is worse than an empty layer, because it fails silently
— the output looks like plausible German until checked.

Measured damage:

```
§ symbol         0 occurrences  — every one became $, S, 5 or 9
"Änderung"       0 correct, "Anderung" ×4 — umlaut lost on capitals
superscript ¹    4 correct, 18 misread as lowercase l
```

Zero section symbols in a document whose entire function is amending
numbered sections. The same pattern is mangled three different ways:
`§ 12b → 9 Izb`, `§ 12c → 9 tZc`, `§ 12d → 9 tzd`.

Sentence numbering — the citation unit — is systematically destroyed:

```
superscript 1 → l    lMacht, lStudien, lOnline, lDer, lEs, lZur
superscript 2 → z    zDie
superscript 5 → s    sDas, slm, sHierauf
```

Plus scattered word damage (`Prüfungszeitraurns`, `Adoptionsurkundc`,
`Vedust`, `uird`, `Beendigqng`, `erneüten`) and spurious spaces
(`Landeshochsch ul gesetz`, `Erfol gskontrol len`).

**The scan itself is clean** — high-contrast printed text, effortless for
a human to read. The damage came from a weak OCR engine, not a bad
scan. The `$`-for-`§` and `l`-for-`1` signature is characteristic of
older engines. A fresh pass should beat it substantially.

### OCR comparison — RESOLVED, Tesseract wins

Tested on page 2 rendered at 300 dpi via `get_pixmap(dpi=300)`.
Tesseract 5.5.3, `lang="deu"`.

**Word accuracy — Tesseract correct on every known-damaged token:**

```
                        Tesseract   Embedded
Prüfungszeitraums          OK        Prüfungszeitraurns
Adoptionsurkunde           OK        Adoptionsurkundc
den nachfolgenden          OK        derr nachfolgenden
Landeshochschulgesetz      OK        Landeshochsch ul gesetz
durchgeführt               OK        du rchgeführt
§ 12b                      OK        Izb
```

Tesseract also produced real German quotation marks (`„` `“`) where the
embedded layer gave `,,`.

**Sentence markers — Tesseract found 10, embedded found 8.** The
embedded layer silently dropped two. Tesseract renders them as
punctuation rather than digits, but systematically:

```
Tesseract:  ? ? * ! 2 ! ? ! ! !
Actual:     2 3 4 1 2 1 2 1 1 1

!  ->  superscript 1   (all five occurrences)
*  ->  superscript 4
?  ->  superscript 2 OR 3 — ambiguous
```

**Why the ambiguity doesn't matter.** Sentence numbers run sequentially
within a paragraph, and Tesseract preserved every marker's *position*.
The Nth marker in a paragraph is sentence N — the glyph doesn't need to
be read at all. `?Dies` is 2nd -> ²Dies; `?Der` is 3rd -> ³Der;
`*Alternativ` is 4th -> ⁴Alternativ.

Caveat for Day 4: paragraphs cross page boundaries (page 2's first
paragraph continues from page 1, so its sequence starts at 2). And D1
§ 30 proves numbering is not *always* sequential — spot-check against
the page images.

**`§` still fails in both**, but Tesseract's failure is mechanical:
`& 12a` and `„8 12a`, i.e. `[&8]` followed by space and a digit. That
pattern is otherwise vanishingly rare in this text. One regex.

**Decision: Tesseract. Gemini Vision not tested — it was the tiebreaker
and there is no tie.**

**The metric was wrong and is worth recording.** Scoring on "surviving
digits" ranked the embedded layer higher (6/10 vs 1/10). But the
embedded layer corrupts real words irrecoverably, while Tesseract's
failures are consistent glyph substitutions a post-processing pass can
undo. The right criterion is **recoverability, not raw correctness** —
wrong-but-consistent beats wrong-but-random.

### D2 content findings

**The amendment renumbers § 12's exam list, and positions change
meaning.** This is not an append:

```
D1 (2022-01)              D2 (2022-07)
1 Klausurarbeiten         1 Klausurarbeit
2 mündliche Prüfungen     2 Mündliche Prüfung
3 Referate                3 Elektronische Prüfung
4 Hausarbeiten            4 Referat
5 Laborarbeiten           5 Praktische Arbeit
6 Praktische Arbeit       6 Laborarbeit
7 Master-Thesis           7 Hausarbeit
                          8 Praxisbericht
                          9 Master-Thesis
                          10 Lerntagebuch
                          11 Portfolioprüfung
```

A cross-reference to "§ 12 Abs. 1 Satz 2 Nr. 4" means *Hausarbeiten*
before July 2022 and *Referat* after. The sharpest amendment-application
case in the corpus, and a strong eval question.

**Portfolioprüfung IS defined in binding text.** D2's new annex: a
Prüfung combining several different examination elements into one
overall result. Revises the earlier finding — the exam *type* is defined;
only the abbreviation `Pf` is not. Narrower, but more defensible.

**The annex defines only 5 of its 11 types.** Mündliche Prüfung, Referat,
Praktische Arbeit, Laborarbeit and Hausarbeit are all `(nicht belegt)`.

**D2 adds §§ 12a–12e** — five new sections on online examinations,
covering video supervision, oral, open-book and written online formats.
Note D1 § 12 Abs. 3 said online exams would be governed by the
*Besonderer Teil*; D2 moves them into the general part instead.

**D2 also amends § 12 Abs. 2** (Nachteilsausgleich extended to
Mutterschutz, students with children, and caring responsibilities) and
inserts § 12 Abs. 2a (Tierschutz in der Lehre).

**D2's dates are internally consistent** — announcement 15.07–29.07.2022,
entry into force 30.07.2022, matching "the day after publication."
The contrast case to D3, whose dates don't line up.

---

## Assessment: how well made are these documents?

Not uniformly badly. Worth being precise, because "the documents are a
mess" is not a defensible claim in a README and "here is what is wrong
with each and why" is.

**D1 (Master StuPO)** — competently drafted. One real slip: § 30's
sentence numbering runs 1, 3, 3. The genuine problem is § 1's programme
list omitting IAI, which reads more like a maintenance failure than a
drafting error: new programmes were added by supplementary statute
without the scope clause being updated.

**D2 (Amendment)** — drafted correctly; published badly. The legal
content is sound and its dates are the only ones in the corpus that
actually line up. But it was scanned rather than published digitally,
and shipped with a poor embedded OCR layer. A publishing failure, not a
drafting one — and the one that costs this project the most work.

**D3 (IAI Supplementary Statute)** — mostly sound and appropriately
terse. Two real defects: an entry-into-force date preceding its own
publication window, and a study plan using `CM`, `CEM` and `Pf` without
defining them anywhere in binding text.

**D4 (Module Handbook)** — the weak one. Placeholder IDs that were never
filled and are ambiguous across module groups, self-contradiction on
those IDs, bilingual and inconsistent field labels, a prerequisite naming
the wrong programme, semester values conflicting with the binding plan.
It reads like a template populated under time pressure and never
proofread end to end. Notably, it is also the only document that isn't
legally binding — the care taken tracks the legal weight.

**A separate category: structural, not sloppy.** Some of what makes this
corpus hard is inherent to how German university regulation works and
would exist even if every document were flawless — a general part
amended by a separate instrument, a programme-specific part written as
deltas ("Re § 12"), cohort-dependent versioning under § 44. That layering
is the design, not a defect.

**This is good for the project.** A clean, self-consistent corpus would
make retrieval trivial and the write-up boring. Real contradictions are
what justify a third answer type — *"the documents disagree, here is
where, ask the Prüfungsamt"* — alongside "answer" and "decline", and
that is a more interesting system than one that only ever looks things
up.

---

## Questions for the Prüfungsamt / Studiendekan

1. Is there a German original of D3? Which language version is binding?
2. What does `Pf` stand for, and where is it defined for IAI?
3. D4's thesis prerequisite names the wrong programme (WIW, not IAI) —
   error or intentional?
4. D3 entry-into-force date contradiction — which date applies?
5. § 1 of the base StuPO omits IAI — oversight or handled elsewhere?
6. Are there amendments beyond D2?
7. How does exam registration work for a summer-semester intake?

---

## Environment

Windows, PowerShell, `D:\MyUniGuide`. Python 3.12.8, venv at `.venv`,
activate with `.\.venv\Scripts\Activate.ps1`. PyMuPDF installed
(`import fitz`).

Gotcha hit and solved: naming a script `inspect.py` shadows Python's
built-in `inspect` module and breaks PyMuPDF's import with a confusing
circular-import error. Avoid filenames matching stdlib modules.

---

## What the defects cost — measured

The contradictions catalogued above are not academic. Measured against a
long-context baseline (Gemini 3.6 Flash, all four PDFs uploaded, 6 Aug 2026):

```
Lookup questions   33/33   100%
Conflict questions  0/6      0%
```

A strong model reading the entire corpus found every fact and reported none of
the disagreements. Three failures were independent of prompt wording:

- **D4's thesis prerequisite** — the model dropped "WIW" and reported the
  50-ECTS threshold as if it applied to IAI. The documented error was repeated
  with the error removed.
- **D3's entry-into-force date** — it picked 01.03.2025 and never mentioned that
  the announcement window on the same page began 03.03.2025.
- **D1 § 1's omission of IAI** — it confirmed the general StuPO applies without
  noting the scope clause does not list the programme.

This is the project's central finding: **synthesis and contradiction-reporting
pull in opposite directions.** A system good at combining sources is structurally
inclined to resolve their disagreements rather than surface them.

Full detail in `notes.md`.

---

## Progress

Daily task log lives in `PROGRESS.md`, in this same `docs/` folder.

This file records what the *documents* contain and how they behave.
`PROGRESS.md` records what was *done* and when. Keeping them apart stops
this file turning into a diary.
