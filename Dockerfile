# syntax=docker/dockerfile:1

# Trois images depuis ce fichier (ADR-0005 : une appli Coolify « Dockerfile » chacune) :
#   docker build --target api   -t ia-cloud-api .     API, cible par défaut
#   docker build --target train -t ia-cloud-train .   entraînement, lancé à la demande
#   docker build --target orchestrator -t ia-cloud-orchestrator .   code server Dagster (réentraînement)

# Image de base figée par version et par empreinte : un build donne toujours le même
# système. À mettre à jour volontairement pour récupérer les correctifs de sécurité.
ARG PYTHON_IMAGE=python:3.12.15-slim-trixie@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704


# ── Dépendances de l'API et package, installés dans /app/.venv (sans mlflow) ──
# Les suites de tests livrées avec scipy, pandas, sklearn... sont retirées : ~100 Mo.
FROM ${PYTHON_IMAGE} AS builder

COPY --from=ghcr.io/astral-sh/uv:0.7.7 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dépendances seules d'abord : cette couche reste en cache tant que uv.lock ne change pas.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-default-groups --no-install-project

COPY pyproject.toml uv.lock main.py ./
COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-default-groups --no-editable \
    && find /app/.venv -type d -name tests -prune -exec rm -rf {} +


# ── Entraînement : dépendances de l'API + mlflow ──
# L'utilisateur app peut créer ses sorties dans /app (artifacts/, mlruns/, mlflow.db),
# mais pas modifier le .venv ni les sources, qui restent à root.
FROM builder AS train

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-default-groups --group train --no-editable \
    && find /app/.venv -type d -name tests -prune -exec rm -rf {} + \
    && useradd --create-home --uid 1000 app \
    && mkdir /app/artifacts \
    && chown app:app /app /app/artifacts

# Pas de Git dans l'image : mlflow ne cherche pas le commit du code.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    GIT_PYTHON_REFRESH=quiet

USER 1000:1000

CMD ["python", "main.py", "train"]


# ── Modèle : entraîné au build tant qu'il n'est pas lu sur S3 (ADR-0002) ──
FROM train AS model

RUN python main.py train


# ── Réentraînement planifié : code server Dagster (gRPC :4000) pour le dagster-workspace du VPS ──
# Les runs s'exécutent ici (DefaultRunLauncher) : mêmes dépendances que l'entraînement + dagster.
FROM train AS orchestrator

USER root

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-default-groups --group train --group orchestration --no-editable \
    && find /app/.venv -type d -name tests -prune -exec rm -rf {} + \
    && install -d -o app -g app /app/dagster_home

COPY dagster.yaml /app/dagster_home/dagster.yaml

ENV DAGSTER_HOME=/app/dagster_home

USER 1000:1000

EXPOSE 4000

CMD ["dagster", "api", "grpc", "-h", "0.0.0.0", "-p", "4000", "-m", "express_delivery.orchestration.definitions"]


# ── API : sans uv, sans mlflow, sans pip, sans sources ni traces MLflow ──
FROM ${PYTHON_IMAGE} AS api

# pip ne sert pas à l'exécution et porte la plupart des vulnérabilités de l'image de base.
RUN python -m pip uninstall --yes pip \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /app/data \
    && chown app:app /app/data

WORKDIR /app

# Code, dépendances et modèle appartiennent à root : l'API ne peut pas les modifier.
COPY --from=builder /app/.venv /app/.venv
COPY --from=model /app/artifacts /app/artifacts

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Sans droits root (ADR-0006). UID numérique : vérifiable sans lire /etc/passwd.
USER 1000:1000

# Extensions DuckDB installées au build : l'API n'a pas à les télécharger au démarrage.
RUN python -c "import duckdb; duckdb.sql('INSTALL ducklake; INSTALL postgres; INSTALL httpfs')"

EXPOSE 8000

# Healthcheck utilisé par Coolify pour le rolling update (ADR-0005) : échoue tant que
# /health/ready ne répond pas 200.
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)"]

CMD ["uvicorn", "express_delivery.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
