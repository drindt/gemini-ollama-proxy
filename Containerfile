FROM python:3.11-alpine

ARG CREATED=${CREATED:-1970-00-00T00:00:00Z}
ARG VERSION=${VERSION:-latest}
ARG REVISION=${REVISION:-0f0f0f0}
ARG USER=${USER:-drindt}

LABEL org.opencontainers.image.created=$CREATED
LABEL org.opencontainers.image.url="https://hub.docker.com/r/drindt/gemini-ollama-proxy"
LABEL org.opencontainers.image.title="Gemini-Ollama-Proxy"
LABEL org.opencontainers.image.description="A lightweight proxy that lets you use Google's Gemini API through an Ollama-compatible interface."
LABEL org.opencontainers.image.version=$VERSION
LABEL org.opencontainers.image.revision=$REVISION
LABEL org.opencontainers.image.source="https://github.com/drindt/gemini-ollama-proxy.git"
LABEL org.opencontainers.image.documentation="https://github.com/drindt/gemini-ollama-proxy/README.md"
LABEL org.opencontainers.image.authors="Daniel Rindt"
LABEL org.opencontainers.image.vendor="Viselabs Inc."
LABEL org.opencontainers.image.licenses="MIT"

ENV PATH="/app/.venv/bin:$PATH"
ENV HOST=${HOST:-"0.0.0.0"}
ENV PORT=${PORT:-11434}
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV GENAI_API_KEY=${GENAI_API_KEY}

RUN --mount=type=cache,target=/var/cache/apk \
    apk update \
    apk add \
    curl

WORKDIR /app

COPY pyproject.toml .
RUN --mount=type=cache,target=/root/.cache \
    pip install --root-user-action=ignore --upgrade pip setuptools wheel && \
    pip install --root-user-action=ignore .

COPY src/ src

EXPOSE $PORT

CMD ["sh", "-c", "uvicorn src.main:app --host ${HOST} --port ${PORT}"]
