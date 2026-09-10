# ============================================================
# Stage 1: Build Wheels & Compile C-Extensions
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgeos-dev \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# ============================================================
# Stage 2: Minimal Production Runtime
# ============================================================
FROM python:3.11-slim AS runner

WORKDIR /app

# Install minimal shared runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgeos-c1v5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pre-compiled wheels from builder stage
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application source code
COPY . .

# Expose backend internal port
EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
