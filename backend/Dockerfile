FROM python:3.13-slim

WORKDIR /app

# postgresql-client: pg_dump/pg_restore da tela de Administracao. A imagem e
# Debian trixie, que traz o cliente 17 — o servidor daqui e o 16, e o pg_dump
# so recusa quando o SERVIDOR e mais novo que ele.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --without dev --no-interaction --no-ansi

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && fastapi run backend/app.py --host 0.0.0.0 --port 8000"]
