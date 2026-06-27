# Fishing Copilot backend (+ ML) — built from the repo root so that the shared
# `core` and `ml` packages are included alongside `backend`.
#
#   docker build -f backend/Dockerfile -t fishing-copilot .
#   docker run -p 8000:8000 fishing-copilot
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for better layer caching.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the three Python packages.
COPY core ./core
COPY ml ./ml
COPY backend ./backend

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
