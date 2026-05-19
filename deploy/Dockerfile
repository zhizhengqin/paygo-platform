# ---- 构建阶段 ----
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir --user \
    fastapi>=0.100.0 \
    "uvicorn[standard]>=0.23.0" \
    jinja2>=3.1.0 \
    python-multipart>=0.0.6 \
    "sqlalchemy[asyncio]>=2.0.0" \
    asyncpg>=0.29.0 \
    redis>=5.0.0 \
    openpaygo>=0.6.3

# ---- 运行阶段 ----
FROM python:3.12-slim

RUN groupadd -r paygo && useradd -r -g paygo paygo

COPY --from=builder /root/.local /home/paygo/.local

WORKDIR /app
COPY app/ ./app/
COPY static/ ./static/
COPY templates/ ./templates/

RUN chown -R paygo:paygo /app

ENV PATH="/home/paygo/.local/bin:$PATH"
ENV PYTHONUNBUFFERED=1

USER paygo
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/login')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
