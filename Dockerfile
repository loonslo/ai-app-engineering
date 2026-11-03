FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    APP_ENV=production \
    CAPSTONE_DATA_DIR=/var/lib/capstone

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home /app app
COPY requirements-capstone.txt /app/requirements-capstone.txt
RUN python -m pip install --no-cache-dir --requirement /app/requirements-capstone.txt

COPY common.py /app/common.py
COPY capstone /app/capstone
COPY capstone/data/docs /var/lib/capstone/docs
RUN mkdir -p /var/lib/capstone && chown -R app:app /app /var/lib/capstone

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/live', timeout=3)"

CMD ["uvicorn", "capstone.api_enterprise:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
