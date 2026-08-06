import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

img = Image.open("data/d2_page2.png")
text = pytesseract.image_to_string(img, lang="deu")

with open("data/d2_page2_tesseract.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("characters:", len(text))
print("-" * 40)
print(text)