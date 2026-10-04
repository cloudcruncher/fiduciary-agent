#!/usr/bin/env bash
# ==============================================================================
# Local Pre-Push Quality & CI Parity Gate
# Prevents failing commits from ever reaching GitHub Actions CI runners.
# ==============================================================================
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

echo -e "\n${BOLD}${BLUE}=== 🛡️ Fiduciary Agent: Pre-Push Local CI Quality Gate ===${NC}\n"

# 1. Secret Scanning (Gitleaks)
echo -e "${BOLD}[1/4] Scanning for committed secrets (Gitleaks)...${NC}"
if command -v gitleaks &> /dev/null; then
    CONFIG_FLAG=""
    if [ -f "${ROOT_DIR}/.gitleaks.toml" ]; then
        CONFIG_FLAG="--config ${ROOT_DIR}/.gitleaks.toml"
    fi
    if gitleaks git --log-opts="-1" --no-banner --log-level warn ${CONFIG_FLAG}; then
        echo -e "${GREEN}✓ Secret scan passed (no leaks detected).${NC}\n"
    else
        echo -e "${RED}✗ Gitleaks detected potential secret leaks in the latest commit!${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️ Gitleaks not installed on PATH; skipping secret scan.${NC}\n"
fi

# 2. Ruff Linter & Formatting Check
echo -e "${BOLD}[2/4] Running Ruff linter across repository...${NC}"
if uv run ruff check .; then
    echo -e "${GREEN}✓ Ruff lint checks passed cleanly.${NC}\n"
else
    echo -e "${RED}✗ Ruff lint errors detected! Fix them before pushing.${NC}"
    exit 1
fi

# 3. Pytest Under Simulated Headless / Offline CI Conditions
echo -e "${BOLD}[3/4] Running full Pytest suite under headless CI conditions...${NC}"
if env TESTING=1 \
       AI_GATEWAY_URL="http://localhost:59999/v1" \
       OLLAMA_HOST="http://localhost:59998" \
       LM_STUDIO_URL="http://localhost:59997" \
       uv run pytest -q; then
    echo -e "${GREEN}✓ All test suites passed under headless/offline simulation.${NC}\n"
else
    echo -e "${RED}✗ Pytest failed! Local tests must pass before pushing to CI.${NC}"
    exit 1
fi

# 4. Package Build Verification
echo -e "${BOLD}[4/4] Verifying wheel and source distribution build (uv build)...${NC}"
if uv build --quiet; then
    echo -e "${GREEN}✓ Package build successful.${NC}\n"
else
    echo -e "${RED}✗ Package build failed!${NC}"
    exit 1
fi

echo -e "${BOLD}${GREEN}🎉 ALL LOCAL CI QUALITY GATES PASSED! Safe to push to GitHub.${NC}\n"
exit 0
