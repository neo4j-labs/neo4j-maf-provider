# syntax=docker/dockerfile:1

FROM python:3.11-slim

WORKDIR /app

# Install uv for faster dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies using uv (prerelease required for Agent Framework)
RUN uv pip install --system --no-cache --prerelease=allow .

EXPOSE 50505

# Run from src directory where the modules are located
WORKDIR /app/src
CMD ["gunicorn", "api.main:create_app"]
