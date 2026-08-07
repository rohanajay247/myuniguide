"""
Generate a cited answer from retrieved chunks.

Same model and same three response types as the long-context baseline, so the
Day 7 comparison measures architecture rather than prompt quality. The only
difference is five retrieved chunks instead of four whole PDFs.

Run from the project root:
    python pipeline/answer.py "how long do I have to write my thesis"
"""

import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types

from search import load_index, search      # same folder

load_dotenv()

MODEL = "gemini-3.6-flash"
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

SYSTEM = """You answer questions about the examination regulations for the
M.Sc. Industrial Artificial Intelligence programme at Hochschule
Albstadt-Sigmaringen.

You are given passages retrieved from four documents:
D1 - Master StuPO General Part 22.1 (German, binding)
D2 - First Amendment to D1, July 2022 (German, binding)
D3 - IAI Supplementary Statute 25.2 (English, binding)
D4 - Module Handbook (English, descriptive, NOT binding)

Answer in English, briefly. Cite the provision using the citation given with
each passage.

Begin every response with one of three words in capitals.

ANSWER - the passages answer the question. Answer and cite.

DECLINE - the passages do not answer the question. Say so and name the office
or system to contact. Passages that are merely ABOUT the same topic are not an
answer. If the question asks for personal data - a grade, a timetable, a
registration status - no document can contain it, so DECLINE.

CONFLICT - the passages contradict each other about the same thing. Say so,
quote both, and do not choose between them.

Distinguish two situations that look similar:

An OVERRIDE is not a conflict. D3 is specific to this programme and D2 amends
D1, so where they differ the more specific and more recent provision applies.
Answer with it and note the general rule. Example: D1 allows four to six months
for the thesis, D3 states six months - the answer is six months.

A CONFLICT is where the documents disagree and no rule resolves it - typically
an error in the text, or two statements that cannot both be true. Example: D4
gives a thesis prerequisite for a different degree programme. Report it as a
conflict.

Only the passages provided may be used. If a passage does not contain what the
question asks for, say so rather than inferring it."""


def build_prompt(question, results):
    passages = []
    for score, chunk in results:
        label = "binding" if chunk["authority"] == "binding" else "NOT binding"
        passages.append(
            f"[{chunk['citation']} — {label}]\n{chunk['text']}"
        )
    joined = "\n\n".join(passages)
    return f"PASSAGES:\n\n{joined}\n\nQUESTION: {question}"


def answer(question, matrix, chunks, top_k=5):
    results = search(question, matrix, chunks, top_k=top_k)
    response = client.models.generate_content(
        model=MODEL,
        contents=build_prompt(question, results),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            temperature=0,
        ),
    )
    return response.text, results


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    question = " ".join(sys.argv[1:])
    matrix, chunks = load_index()
    text, results = answer(question, matrix, chunks)

    print(f"\nQ: {question}\n")
    print(text)
    print("\n--- retrieved ---")
    for score, chunk in results:
        print(f"  {score:.3f}  {chunk['citation']}")


if __name__ == "__main__":
    main()