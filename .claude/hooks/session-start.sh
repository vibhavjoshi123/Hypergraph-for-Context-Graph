#!/bin/bash
set -euo pipefail

# Only run in remote (Claude Code on the web) environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Set PYTHONPATH so src imports work without pip install -e
echo 'export PYTHONPATH="$CLAUDE_PROJECT_DIR"' >> "$CLAUDE_ENV_FILE"

# Install Python dependencies for testing and linting.
# External service SDKs (typedb-driver, anthropic, openai) are optional
# and not required for unit tests.
# Use uv if available (faster), fall back to pip.
if command -v uv &> /dev/null; then
  uv pip install --system \
    pydantic \
    pydantic-settings \
    fastapi \
    uvicorn \
    httpx \
    python-dotenv \
    structlog \
    tenacity \
    aiolimiter \
    numpy \
    aiohttp \
    pytest \
    pytest-asyncio \
    pytest-cov \
    ruff \
    mypy
else
  pip install \
    pydantic \
    pydantic-settings \
    fastapi \
    uvicorn \
    httpx \
    python-dotenv \
    structlog \
    tenacity \
    aiolimiter \
    numpy \
    aiohttp \
    pytest \
    pytest-asyncio \
    pytest-cov \
    ruff \
    mypy
fi
