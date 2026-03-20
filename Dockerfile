# ── stage 1: build dependencies ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Copy installed packages from build stage
COPY --from=builder /install /usr/local

# Copy application source
COPY app/      app/
COPY etl/      etl/
COPY data/raw/ data/raw/

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
