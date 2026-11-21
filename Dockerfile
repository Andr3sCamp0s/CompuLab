FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/Costa_Rica

WORKDIR /app

# Dependencias primero para aprovechar caché de capas
COPY pyproject.toml ./
COPY compulab ./compulab
COPY tests ./tests

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ".[dev]"

# Usuario no-root por buenas prácticas de seguridad en contenedores Linux
RUN useradd --create-home --shell /bin/bash compulab \
    && chown -R compulab:compulab /app
USER compulab

CMD ["pytest", "-q"]
