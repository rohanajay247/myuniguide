import fitz

PDF = "data/raw/2022-07-14_StuPO_Master_Erste_AEnderungssatzung_beurkundet.pdf" 
OUT = "data/d2_raw.txt"

doc = fitz.open(PDF)

pages = []
for i in range(doc.page_count):
  text = doc[i].get_text()
  pages.append(f"\n\n========== Page {i+1} ==========\n\n{text}")

with open(OUT, "w", encoding="utf-8") as f:
  f.write("".join(pages))

print("Wrote to", OUT)
print("Total Characters:", sum(len(p) for p in pages))


# for one page
# import fitz

# PDF = "data/raw/StuPO_Master_221_20220111.pdf"

# doc = fitz.open(PDF)

# print("pages: ", doc.page_count)

# page = doc[4]
# text = page.get_text()

# print("characters on this page: ", len(text))
# print("-"*40)
# print(text)