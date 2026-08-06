# to read font sizes
import fitz

doc = fitz.open("data/raw/StuPO_Master_221_20220111.pdf")
page = doc[5]

d = page.get_text("dict")

for block in d["blocks"]:
 if "lines" not in block:
   continue
 for line in block["lines"]:
   for span in line["spans"]:
    print(f'{span["size"]:5.1f}  x={span["bbox"][0]:6.1f}  {span["text"][:60]!r}')