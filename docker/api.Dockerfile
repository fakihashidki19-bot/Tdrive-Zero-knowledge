FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY core/ ./core/
COPY api/ ./api/
COPY cli/ ./cli/
COPY pyproject.toml .

RUN pip install --no-cache-dir \
    cryptography \
    sqlalchemy \
    telethon \
    fastapi[standard] \
    python-multipart \
    pyjwt \
    typer \
    rich \
    pytest \
    pytest-asyncio \
    pytest-mock

EXPOSE 8000

CMD ["python", "-m", "api.main"]
