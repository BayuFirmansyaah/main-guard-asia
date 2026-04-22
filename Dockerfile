# ── Build stage: Mind-Guard Asia ──────────────────────────────────────────────
FROM python:3.11-slim

# Prevent pyc files & enable unbuffered logs (penting untuk Docker)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies dulu (layer ini di-cache jika requirements.txt tidak berubah)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn>=21.0.0

# Copy source code
COPY app.py .
COPY index.html .

# Port yang akan di-expose (CapRover akan proxy ke sini)
EXPOSE 5000

# Jalankan dengan Gunicorn (production-grade, bukan Flask dev server)
# - 2 worker processes
# - timeout 120s (untuk streaming SSE)
# - bind ke semua interface
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--timeout", "120", \
     "--worker-class", "sync", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
