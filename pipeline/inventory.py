import hashlib
from pathlib import Path

RAW = Path("data/raw")

for pdf in sorted(RAW.glob("*.pdf")):
    data = pdf.read_bytes()
    print(pdf.name)
    print(f"  sha256: {hashlib.sha256(data).hexdigest()}")
    print(f"  bytes:  {len(data):,}")
    print()