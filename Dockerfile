FROM python:3.12-slim

WORKDIR /app

# Requirements first so this layer caches — code edits won't reinstall
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The index ships inside the image. 573 KB, so no database, no external state.
COPY pipeline/ ./pipeline/
COPY app/ ./app/
COPY config/ ./config/
COPY data/index.npy data/index.json ./data/

# Cloud Run injects PORT at runtime; 8080 is the local default
ENV PORT=8080
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}