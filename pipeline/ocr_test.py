import fitz

PDF = "data/raw/2022-07-14_StuPO_Master_Erste_AEnderungssatzung_beurkundet.pdf"
doc = fitz.open(PDF)
doc[2].get_pixmap(dpi=300).save("data/d2_page3.png")
print("saved")


# import fitz

# PDF = "data\raw\2022-07-14_StuPO_Master_Erste_AEnderungssatzung_beurkundet.pdf"

# doc = fitz.open(PDF)
# pix = doc[1].get_pixmap(dpi=300)
# pix.save("data/d2_page2.png")

# print("saved d2_page2.png")
# print("size:", pix.width, "x", pix.height)