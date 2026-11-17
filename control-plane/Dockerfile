# 控制面镜像。构建上下文是仓库根：
#   docker build -f control-plane/Dockerfile -t cloud-agents/control-plane:0.1.0 .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

COPY control-plane/pyproject.toml control-plane/uv.lock ./
RUN pip install --no-cache-dir uv==0.13.8 \
    && uv sync --frozen --no-dev --no-install-project \
    && rm -rf /root/.cache/uv

COPY control-plane/alembic.ini ./
COPY control-plane/migrations ./migrations
COPY control-plane/app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
