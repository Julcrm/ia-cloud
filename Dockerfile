# syntax=docker/dockerfile:1

# ── Dépendances et package, installés dans /app/.venv ──
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.7.7 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dépendances seules d'abord : cette couche reste en cache tant que uv.lock ne change pas.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

COPY pyproject.toml uv.lock main.py ./
COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable


# ── Modèle : entraîné au build tant qu'il n'est pas lu sur S3 (ADR-0002, séance 3) ──
FROM builder AS model

RUN /app/.venv/bin/python main.py train


# ── Image finale : API seule, sans uv, sans sources ni traces MLflow ──
FROM python:3.12-slim

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/data \
    && chown app:app /app/data

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=model /app/artifacts /app/artifacts

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Sans droits root (ADR-0006).
USER app

# Extensions DuckDB installées au build : l'API n'a pas à les télécharger au démarrage.
RUN python -c "import duckdb; duckdb.sql('INSTALL ducklake; INSTALL postgres; INSTALL httpfs')"

EXPOSE 8000

# Healthcheck utilisé par Coolify pour le rolling update (ADR-0005) : échoue tant que
# /health/ready ne répond pas 200.
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)"]

CMD ["uvicorn", "express_delivery.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
