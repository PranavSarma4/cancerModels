FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 wget && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY proteosurf/ proteosurf/

RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir rdkit || true

EXPOSE 8000

ENV STRUCTBIO_CACHE=/app/cache
RUN mkdir -p /app/cache

CMD ["uvicorn", "proteosurf.app:app", "--host", "0.0.0.0", "--port", "8000"]
