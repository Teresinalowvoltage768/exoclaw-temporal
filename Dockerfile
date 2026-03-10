FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
RUN uv sync --no-dev

COPY exoclaw_temporal/ exoclaw_temporal/

CMD ["uv", "run", "python", "-m", "exoclaw_temporal.turn_based", "--worker"]
