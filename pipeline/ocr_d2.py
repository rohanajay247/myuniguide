import os
import time
import fitz
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-3.6-flash"

PDF = "data/raw/2022-07-14_StuPO_Master_Erste_AEnderungssatzung_beurkundet.pdf"
OUT = "data/d2_ocr.txt"

PROMPT = """Transcribe this page of German legal text exactly.

This document numbers individual sentences with superscript digits.
Preserve every one as a normal digit attached to the start of its
sentence, e.g. the superscript 1 in "Macht" becomes "1Macht".

Transcribe the section symbol § correctly wherever it appears.

If a character or number is unclear, write [?] rather than guessing.

Do not summarise, correct, translate or reformat. Transcribe only.
Output the page text and nothing else."""

doc = fitz.open(PDF)
pages = []

for i in range(doc.page_count):
    png = doc[i].get_pixmap(dpi=300).tobytes("png")

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=png, mime_type="image/png"),
            PROMPT,
        ],
        config=types.GenerateContentConfig(temperature=0),
    )

    text = response.text
    pages.append(f"\n\n===== PAGE {i + 1} =====\n\n{text}")
    print(f"page {i + 1}: {len(text)} chars")
    time.sleep(2)

with open(OUT, "w", encoding="utf-8") as f:
    f.write("".join(pages))

print("wrote", OUT)