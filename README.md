# 🛡️ Personal Fiduciary Financial Harness (Live UK Version)

[![CI & Security Audit](https://github.com/cloudcruncher/fiduciary-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/cloudcruncher/fiduciary-agent/actions/workflows/ci.yml)
[![Python 3.11 | 3.12 | 3.13](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Linter: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Privacy: 100% Air-Gapped Local](https://img.shields.io/badge/Privacy-100%25%20Air--Gapped%20Local-emerald.svg)](#-privacy-fiduciary-contract--air-gap-guarantees)
[![Open Banking: UK Regulated](https://img.shields.io/badge/Open%20Banking-TrueLayer%20%7C%20Wise-blueviolet.svg)](#-connecting-real-uk-banks)
[![Architecture: Interactive Map](https://img.shields.io/badge/Architecture-Interactive%20Live%20Map-teal.svg)](https://cloudcruncher.github.io/fiduciary-agent/)

A 100% `uv`-managed, local-first, privacy-preserving fiduciary intelligence harness engineered for Apple Silicon macOS.

Unlike mainstream fintech apps that sell your financial habits to third-party data brokers, or generic LLM wrappers that hallucinate arithmetic, this harness operates under a strict **Three-Tier Fiduciary Contract**:
1. **Air-Gapped Ingestion**: Automated PII masking (`••-••-XX`, `••••XXXX`). Sensitive databases (`data/*.db`) and credentials (`.env`, `secrets/*`) are strictly excluded from git.
2. **Deterministic Python Core**: 100% of arithmetic calculations (liquid runway, 60% tax traps, spending velocity, budget splits) run through pure Python—never an LLM.
3. **Grounded Local AI (Apple Silicon Metal GPU)**: Local reasoning running via Ollama (`qwen3.5:4b`) or LM Studio (`Meta-Llama-3.1-8B`) with real-time Grounding Guardrails and an independent local LLM Judge.

---

## 🎬 Terminal Demo & UI Preview

### Terminal Interactive Workflow (`./f seed` → `./f spending pubs` → `./f copilot` → `./f judge`)
![Terminal Demo](docs/demo.svg)

### Local Web Dashboard (`http://localhost:8080`)
![Fiduciary Dashboard](docs/dashboard_live.png)

---

## ⚡ 60-Second Quickstart (100% Local, Zero Real Data Needed)

Anyone can clone and run this harness locally in under a minute without needing real bank accounts or API keys:

### 1. Prerequisites
- **macOS** (Optimized for Apple Silicon M1/M2/M3/M4) or Linux/WSL2
- [**uv**](https://docs.astral.sh/uv/) (blazing fast Python package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [**Ollama**](https://ollama.com/) (recommended for local offline inference): `brew install ollama && ollama serve`

### 2. Clone & Install
```bash
git clone https://github.com/cloudcruncher/fiduciary-agent.git
cd fiduciary-agent

# Install dependencies in an isolated virtual environment
uv sync --dev
```

### 3. Pull Lightweight Local Model
```bash
# Pull fast, high-quality 4B model (uses ~2.8 GB RAM, unloads after turn)
ollama pull qwen3.5:4b
```

### 4. Seed Realistic Synthetic UK Financial Profile
```bash
# Generates realistic NatWest, Revolut, and Wise accounts with 60-day history
./f seed
```

### 5. Launch & Explore
```bash
# Run the live interactive terminal walkthrough tour
./f demo

# Launch the interactive local web dashboard
./f ui

# Or chat with your offline AI Fiduciary Copilot directly in the terminal
./f copilot "How much have I spent on pubs?"
./f copilot "Can I afford a £1,500 holiday in July without breaking my emergency buffer?"
```

---

## ⚡ CLI Command Matrix (`./f`)

An executable shortcut `./f` is available in the project root:

| Command | Short Alias | Function |
| :--- | :--- | :--- |
| **`./f demo`** | — | Run interactive cinematic terminal walkthrough demonstrating all capabilities |
| **`./f seed`** | — | Seed realistic synthetic UK bank accounts, transactions & bills for local testing |
| **`./f spending [query]`** | **`./f spend`** | Spending Insight Engine: Category breakdown (e.g. `pubs`, `groceries`), velocity & micro-expenses |
| **`./f profile`** | **`./f p`** | Intelligent Customer Profile: Financial Health Score (0–100), Financial DNA Archetype & Action Cards |
| **`./f copilot [Q]`** | **`./f chat`** | Interactive conversational AI Fiduciary Copilot (grounded in live transactions & tax rules) |
| **`./f watchdog`** | **`./f guard`** | Financial Watchdog: Detect stealth subscription price hikes, duplicate charges, upcoming bills |
| **`./f tax`** | **`./f t`** | UK Tax & Wealth Optimization: 60% allowance trap audit, SIPP relief, Personal Savings Allowance drag |
| **`./f sweep`** | — | Smart Cash Sweeper & Automated Standing Order float architect |
| **`./f networth`** | **`./f nw`** | Whole-of-Wealth Balance Sheet (Cash, Investments, Pensions, Property, Debt) |
| **`./f asset add`** | — | Add custom assets or debts (property equity, pension pots, mortgages) |
| **`./f tx`** | — | Itemised transactions. Filters: `-c dining`, `-a revolut`, `-n 15`, `-s "Tesco"` |
| **`./f connect`** | **`./f c`** | Connect real UK banks (Revolut, Chase, HSBC, Lloyds, Zopa) via TrueLayer |
| **`./f sync`** | — | Sync live balances & transactions from Wise and Open Banking |
| **`./f scout`** | **`./f s`** | Autonomous market scout (Cash ISAs, after-tax yields, bank switch bounties) |
| **`./f audit`** | **`./f a`** | Real fiduciary capital allocation audit + live AI strategy memo |
| **`./f traces`** | **`./f tr`** | AI observability: inspect tool latency, grounding score, and telemetry per turn |
| **`./f judge`** | **`./f j`** | Score the latest Copilot answer with an independent local model (LLM-as-a-Judge) |
| **`./f tools`** | **`./f tl`** | Inspect available deterministic and live web tools catalog |
| **`./f ui`** | **`./f w`** | Launch local web dashboard at `http://localhost:8080` |

---

## 🗄️ Architectural Rationale: Why SQLite? (And When to Use DuckDB or PostgreSQL)

The fiduciary engine was engineered with intentional storage trade-offs tailored to single-user financial autonomy on modern laptop hardware:

| Criteria | **SQLite** *(Current Choice)* | **DuckDB** *(Analytical Vector)* | **PostgreSQL** *(Enterprise SaaS)* |
| :--- | :--- | :--- | :--- |
| **Deployment Model** | Embedded, zero-daemon, single file (`data/financial.db`) | Embedded, in-process columnar engine | Client-server daemon (Docker / Managed service) |
| **RAM Impact (16GB Mac)** | **~0 MB idle** (instant zero-friction start) | Moderate buffer pool allocation | High (shared buffers + connection pool processes) |
| **Data Privacy & Air-Gap** | **100% local APFS file**, zero network open ports | 100% local file / Parquet data lake | Network TCP ports, exposed credentials surface |
| **Query Latency** | **< 0.1 ms** for transactional lookups & joins | **< 0.5 ms** vectorized scans over millions | 1.0 – 5.0 ms (network roundtrip latency) |
| **Dependency Footprint** | **Zero external dependencies** (Python standard library) | Third-party dependency (`duckdb`) | External database server + drivers (`psycopg2`/`asyncpg`) |
| **Special Superpower** | Unmatched reliability, zero maintenance, ACID | Direct Parquet/CSV queries + native VSS vector search | Multi-tenant Row-Level Security (RLS), `pgvector`, TimescaleDB |
| **When to Switch?** | **Default for personal fiduciary harness** | Switch if analyzing 500K+ txs or running local vector search | Switch if hosting a multi-user advisory SaaS platform |

### Why SQLite was chosen for this project:
1. **Unified Memory Preservation on 16GB Macs**: On an Apple Silicon machine running an Ollama or LM Studio LLM (`qwen3.5:4b` requires ~2.8 GB RAM), every megabyte counts. Running a PostgreSQL daemon or memory-hungry OLAP cluster competes directly with Metal GPU unified memory. SQLite consumes virtually 0 MB when idle and requires zero background processes.
2. **Absolute Air-Gap**: The SQLite file sits exclusively on your local APFS SSD. It cannot be sniffed over a network socket or misconfigured with open ports.
3. **Pluggable Storage Abstraction**: All database interactions are encapsulated in [`fiduciary/storage/db.py`](fiduciary/storage/db.py). If you wish to migrate to DuckDB (for analytical column scans) or PostgreSQL (for a multi-tenant web platform), you only need to swap the adapter without altering any agent or analysis logic.

---

## 🔒 Privacy, Fiduciary Contract & Air-Gap Guarantees

### Automated Secret & PII Shielding
- **Strict `.gitignore`**: Live databases (`data/*.db`), credentials (`.env`), private keys (`*.pem`, `*.key`), and bank statements (`*.pdf`, `*.csv`) are strictly ignored.
- **PII Masking**: Bank account numbers and sort codes are automatically masked (`••-••-XX`, `••••XXXX`) during statement ingestion.
- **Zero Cloud Egress**: In default local mode, client financial balances and transactions are **never transmitted to external cloud APIs**. The Gemini API client remains completely dormant unless explicitly configured.
- **Automated CI Secret Scanning**: Every pull request and push is audited with [Gitleaks](https://github.com/gitleaks/gitleaks) to guarantee zero credentials or tokens enter git history.

### Offline Air-Gap Verification (Airplane Mode Test)
You can physically verify that zero financial data leaves your Mac:
1. Turn off Wi-Fi on your Mac completely.
2. Run:
   ```bash
   ./f copilot "What is my liquid balance and how much did I spend on pubs?"
   ```
3. The Copilot executes 100% offline using your local Ollama engine on Apple Silicon Metal GPU.

---

## 🏦 Connecting Real UK Banks (Optional)

When you are ready to transition from synthetic demo data to your real finances:

### 1. Wise Multi-Currency API
1. Generate a read-only API token in Wise (*Settings → API tokens → Read only*).
2. Add to `.env`:
   ```bash
   WISE_API_TOKEN="your_read_only_token"
   ```
3. Sync: `./f sync`

### 2. Revolut, Chase, HSBC, NatWest, Lloyds, Zopa (via TrueLayer)
1. Register a free developer console at [console.truelayer.com](https://console.truelayer.com).
2. Add credentials to `.env`:
   ```bash
   TRUELAYER_CLIENT_ID="your_client_id"
   TRUELAYER_CLIENT_SECRET="your_client_secret"
   TRUELAYER_USE_SANDBOX=false
   ```
3. Run `./f connect` or click **`🏦 Connect Bank`** in the web dashboard. Complete the standard UK Open Banking mobile app authentication.

### 3. PDF & CSV Bank Statement Importer
Drop any NatWest, Revolut, Chase, or HSBC PDF/CSV statement into the drag-and-drop importer at `http://localhost:8080`. Statements are parsed in memory, sanitized through the PII Privacy Shield, and stored directly in your local SQLite database.

---

## 🧠 Optimizing Local LLMs on Apple Silicon (M3, 16GB RAM)

Running local LLMs fast on an M3 MacBook Pro requires specific latency engineering:
1. **Disabled Reasoning Loops (`"think": false`)**: Models like `qwen3.5:4b` default to generating 800+ internal "thinking" tokens. By passing `"think": false` via Ollama's native `/api/chat`, inference time drops from **22 seconds down to 0.4–1.2 seconds (50x faster)**.
2. **Intent-Driven Dynamic Prompt Pruning**: Rather than dumping full transaction histories into every turn, the Copilot dynamically prunes context based on classified intent, cutting token consumption by 80%.
3. **RAM Guardrails (`keep_alive: 0`)**: Ollama unloads the model from RAM after generating a response, preventing memory pressure accumulation.

---

## 🧪 CI, Testing & Code Quality

The repository includes a comprehensive test suite (48 tests) and automated CI pipeline:

```bash
# Run full unit and integration test suite
uv run pytest --verbose

# Run ultra-fast Ruff linter
uv run ruff check .

# Verify wheel and source distribution build
uv build
```

GitHub Actions executes across **Python 3.11, 3.12, and 3.13** on every commit, alongside automated Gitleaks secret detection and Ruff validation.

---

## 🏛️ Interactive Architecture & System Tour

Interactive architectural diagrams, sequence flows, grounding guardrails, and data schemas are accessible live:
- 🌐 **[Live Interactive Architecture Map (GitHub Pages)](https://cloudcruncher.github.io/fiduciary-agent/)**
- 🧭 **[Complete System Walkthrough & User Guide (GitHub Pages)](https://cloudcruncher.github.io/fiduciary-agent/guide.html)**
- Open [`docs/architecture.html`](docs/architecture.html) locally in your browser.
- Or visit `http://localhost:8080/architecture` while the local server is running.
- Local System Tour and Module Guide: `http://localhost:8080/guide`.

---

## 📄 License

MIT License. Designed for personal financial sovereignty.
