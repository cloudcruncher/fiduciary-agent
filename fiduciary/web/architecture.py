ARCHITECTURE_HTML = r"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solution Architecture & System Design • Personal Fiduciary Agent</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        brand: { 50: '#f0fdf4', 500: '#22c55e', 600: '#16a34a', 700: '#15803d' },
                        slate: { 850: '#151f32', 900: '#0f172a', 950: '#020617' }
                    }
                }
            }
        };
        mermaid.initialize({
            startOnLoad: false,
            theme: 'dark',
            securityLevel: 'loose',
            themeVariables: {
                darkMode: true,
                background: '#0f172a',
                primaryColor: '#1e293b',
                primaryTextColor: '#f8fafc',
                primaryBorderColor: '#334155',
                lineColor: '#38bdf8',
                secondaryColor: '#064e3b',
                tertiaryColor: '#581c87'
            }
        });
        window.addEventListener('DOMContentLoaded', () => {
            const activeNodes = document.querySelectorAll('#section-topology .mermaid');
            if (activeNodes.length) {
                mermaid.run({ nodes: Array.from(activeNodes) });
            }
            const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            if (isLocal) {
                document.getElementById('nav-local-dashboard')?.classList.remove('hidden');
            }
        });
    </script>
    <style>
        .card { @apply bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg; }
        .tab-btn.active { @apply bg-slate-800 text-emerald-400 border-emerald-500 font-bold; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0f172a; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans antialiased pb-20">

    <!-- Header -->
    <header class="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40">
        <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <span class="text-2xl">🏛️</span>
                <div>
                    <h1 class="font-bold text-base bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
                        Solution Architecture & System Design
                    </h1>
                    <p class="text-[11px] text-slate-400">Institutional Fiduciary Autonomous Engine • 100% On-Device Privacy</p>
                </div>
            </div>
            <div class="flex items-center space-x-3 text-xs">
                <a id="nav-local-dashboard" href="/" class="hidden px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 font-semibold transition">
                    ← Back to Dashboard
                </a>
                <a href="https://github.com/cloudcruncher/fiduciary-agent" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 font-semibold transition flex items-center space-x-1.5">
                    <span>💻</span>
                    <span>GitHub Repo</span>
                </a>
                <a href="guide.html" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 font-semibold transition">
                    🧭 System Guide
                </a>
                <button onclick="window.print()" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-semibold shadow transition">
                    🖨️ Export PDF / Print
                </button>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 mt-6 space-y-6">

        <!-- Executive Summary Banner -->
        <div class="card border-l-4 border-l-emerald-500 space-y-2">
            <div class="flex items-center justify-between">
                <h2 class="text-lg font-bold text-white flex items-center space-x-2">
                    <span>🛡️</span>
                    <span>System Architecture Overview</span>
                </h2>
                <div class="flex items-center space-x-2">
                    <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 border border-emerald-800 text-emerald-300">Air-Gapped Privacy</span>
                    <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-950 border border-blue-800 text-blue-300">Deterministic Math Core</span>
                    <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-950 border border-purple-800 text-purple-300">Local LLM (Metal GPU)</span>
                </div>
            </div>
            <p class="text-xs text-slate-300 leading-relaxed max-w-5xl">
                The Personal Fiduciary Agent is an institutional-grade financial intelligence engine engineered for Apple Silicon macOS.
                Unlike traditional fintech apps that stream confidential banking data to cloud servers or hallucinate arithmetic using generic LLMs,
                this harness enforces a strict <strong>Three-Tier Separation Architecture</strong>: 
                <strong>1. Air-Gapped Data Ingestion</strong> with automatic PII masking, 
                <strong>2. Zero-Hallucination Deterministic Python Core</strong> for all calculations (runway, tax traps, bills), and 
                <strong>3. Grounded Local AI Reasoning</strong> running on Apple Silicon Metal GPU with real-time Grounding Guardrails.
            </p>
        </div>

        <!-- Interactive Architecture Navigation Tabs -->
        <div class="flex border-b border-slate-800 space-x-2 overflow-x-auto text-xs pb-1">
            <button onclick="switchArchTab('topology')" id="tab-topology" class="tab-btn active px-4 py-2 rounded-t-lg border-b-2 border-transparent transition">
                1. System Topology Diagram
            </button>
            <button onclick="switchArchTab('airgap')" id="tab-airgap" class="tab-btn px-4 py-2 rounded-t-lg border-b-2 border-transparent transition text-slate-400 hover:text-white">
                2. Ingestion & Air-Gap Sequence Flow
            </button>
            <button onclick="switchArchTab('deterministic')" id="tab-deterministic" class="tab-btn px-4 py-2 rounded-t-lg border-b-2 border-transparent transition text-slate-400 hover:text-white">
                3. Deterministic Financial Core
            </button>
            <button onclick="switchArchTab('guardrails')" id="tab-guardrails" class="tab-btn px-4 py-2 rounded-t-lg border-b-2 border-transparent transition text-slate-400 hover:text-white">
                4. Observability & Grounding Guardrails
            </button>
            <button onclick="switchArchTab('schema')" id="tab-schema" class="tab-btn px-4 py-2 rounded-t-lg border-b-2 border-transparent transition text-slate-400 hover:text-white">
                5. Database Schema & Entity Model
            </button>
            <button onclick="switchArchTab('dataeng')" id="tab-dataeng" class="tab-btn px-4 py-2 rounded-t-lg border-b-2 border-transparent transition text-slate-400 hover:text-white">
                6. Lead Data Engineering &amp; Closed-Loop Reconciliation
            </button>
            <button onclick="switchArchTab('mobile')" id="tab-mobile" class="tab-btn px-4 py-2 rounded-t-lg border-b-2 border-transparent transition text-slate-400 hover:text-white">
                7. Mobile Phone Linking &amp; Biometric OAuth Handoff
            </button>
        </div>

        <!-- TAB 1: SYSTEM TOPOLOGY DIAGRAM -->
        <div id="section-topology" class="space-y-6">
            <div class="card space-y-4">
                <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                        <h3 class="font-bold text-sm text-white">Full Solution Architecture Topology</h3>
                        <p class="text-xs text-slate-400">Complete end-to-end data pipelines from bank statements to local AI inference</p>
                    </div>
                    <span class="text-xs text-slate-500 font-mono">Interactive Vector Diagram</span>
                </div>

                <!-- Mermaid Diagram -->
                <div class="bg-slate-950 p-6 rounded-xl border border-slate-800 overflow-x-auto">
                    <pre class="mermaid text-xs">
flowchart TB
    subgraph INGESTION["1. INGESTION &amp; PRIVACY LAYER"]
        PDF["UK Bank PDF Statements<br/>(NatWest, Barclays, HSBC)"] --> PDFP["On-Device PDF Parser<br/>(pypdf in-memory extraction)"]
        CSV["Bank CSV Exports<br/>(Revolut, Chase, Lloyds)"] --> CSVP["CSV Banking Importer"]
        TL["TrueLayer Open Banking API<br/>(Read-Only Account Token)"] --> TLP["TrueLayer Sync Client"]
        WISE["Wise Multi-Currency API<br/>(Direct Read-Only Token)"] --> WCL["Wise Sync Client"]
        
        PDFP --> PII["PII Privacy Shield<br/>• Sort Code: ••-••-XX<br/>• Account: ••••XXXX"]
        CSVP --> PII
        TLP --> PII
        WCL --> PII
    end

    subgraph STORAGE["2. LOCAL AIR-GAPPED STORAGE"]
        PII --> DB[("SQLite Engine (data/financial.db)<br/>• accounts<br/>• transactions<br/>• recurring_bills<br/>• net_worth_snapshots<br/>• llm_traces<br/>• oauth_tokens (90d Refresh Tokens)<br/>• credit_profile (CRA Scores &amp; Electoral Roll)")]
    end

    subgraph CORE["3. DETERMINISTIC PYTHON CORE (ZERO MATH HALLUCINATION)"]
        DB --> TP["Transaction Profiler<br/>• 30-Day Living Burn Rate<br/>• Exact Liquid Runway Days<br/>• Inbound Funding Patterns"]
        DB --> WD["Financial Watchdog<br/>• Subscription Detection<br/>• Stealth Price Hikes<br/>• Duplicate Charge Audits"]
        DB --> TAX["UK Tax Optimizer<br/>• 60% Marginal Tax Trap<br/>• PSA Interest Drag<br/>• SIPP Pension Sacrifice"]
        DB --> SWEEP["Smart Sweeper Engine<br/>• 1st-of-Month Float Plan<br/>• Consumer Rights 2015 Notices"]
        DB --> NW["Whole Balance Sheet<br/>• Multi-Asset Net Worth<br/>• Class Allocation (Cash/ISA/Pots)"]
        DB --> CREDIT["Credit &amp; Affordability Engine<br/>• FCA MCOB 11 Cash Flow (UMI/DTI)<br/>• BNPL &amp; Returned DD Radar<br/>• 4.5x Mortgage Capacity &amp; Stress<br/>• 0–100 Readiness Score"]
    end

    subgraph AI["4. LOCAL OLLAMA REASONING &amp; GUARDRAIL PIPELINE (100% PRIVATE)"]
        TP --> CTX["Financial Context Aggregator"]
        WD --> CTX
        TAX --> CTX
        SWEEP --> CTX
        NW --> CTX
        CREDIT --> CTX

        WEB["Zero-Overhead Web Tools (&lt;250ms)<br/>• Live BoE Base Rate (3.75%)<br/>• Top Cash ISA (4.87%) &amp; Regular Saver (7.00%)<br/>• DuckDuckGo Knowledge API"] --> CTX
        WEB --> TOOL_OBS["Tool Execution Tracker<br/>• Latency (ms), URL/Source, Payload<br/>• tools_used_json stored in trace"]
        TOOL_OBS --> TRACE

        CTX --> PROMPT["Grounded Dynamic Prompt<br/>(Pruned context: ~300 tokens)"]
        DB --> TXR["Itemised Transaction Retriever<br/>• Bank filter (revolut / wise / natwest)<br/>• 'last N' count detection<br/>• Numbered newest-first rows"]
        TXR --> PROMPT
        
        PROMPT --> LLM_CLIENT["Unified LLM Client"]
        
        LLM_CLIENT -->|"Primary Default (100% Offline)"| OLLAMA["Ollama Local Engine (:11434)<br/>(qwen3.5:4b / llama3.2 on Metal GPU)<br/>• think: false (Sub-second)<br/>• keep_alive: 0 (Zero RAM leak)"]
        LLM_CLIENT -.->|"Alternative Local"| LMSTUDIO["LM Studio Local Endpoint (:1234)<br/>(Meta-Llama-3.1-8B)"]
        LLM_CLIENT -.->|"Enterprise AI Gateway (Opt-in)"| GATEWAY["AI Gateway / LiteLLM Proxy (:4000)<br/>(OpenAI-compatible router &amp; cache)"]
        LLM_CLIENT -.->|"Dormant Adapter (Opt-in only)"| GEMINI["Google Gemini Cloud API<br/>(Zero egress by default)"]

        OLLAMA --> AUDIT["Layer 1: Grounding Auditor<br/>• Extracts all £, %, days<br/>• Validates against Prompt Context<br/>• Flags Unverified Claims"]
        LMSTUDIO -.-> AUDIT
        GATEWAY -.-> AUDIT
        GEMINI -.-> AUDIT

        AUDIT --> TRACE["Observability Logger<br/>• Latency (ms)<br/>• Grounding Score<br/>• llm_traces Table"]
        TRACE -.->|"On demand: ./f judge"| JUDGE["Layer 2: LLM-as-a-Judge<br/>(Ollama :11434 with think: false)<br/>• Faithfulness / Relevance / Fiduciary<br/>• Auto-unloaded after evaluation"]
        JUDGE -.->|"judge_result_json"| TRACE
    end

    subgraph INTERFACES["5. CLIENT PRESENTATION INTERFACES"]
        AUDIT --> FASTAPI["FastAPI Local Server (127.0.0.1:8080)"]
        TRACE --> FASTAPI

        FASTAPI --> MACAPP["Native macOS App<br/>(/Applications/Fiduciary.app)"]
        FASTAPI --> BROWSER["Local Web Dashboard<br/>(http://localhost:8080)<br/>• Live Transactions tab<br/>• Credit &amp; Borrowing tab<br/>• Traces modal"]
        FASTAPI --> CLI["Interactive Terminal CLI<br/>(./f tx -a revolut -n 5, ./f credit, ./f copilot, ./f judge)"]
    end

    style INGESTION fill:#064e3b,stroke:#059669,stroke-width:2px,color:#ecfdf5
    style STORAGE fill:#1e293b,stroke:#475569,stroke-width:2px,color:#f8fafc
    style CORE fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#e0e7ff
    style AI fill:#581c87,stroke:#a855f7,stroke-width:2px,color:#faf5ff
    style INTERFACES fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#f0f9ff
                    </pre>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 text-xs">
                    <div class="p-3.5 bg-slate-850 rounded-xl border border-slate-800 space-y-1">
                        <div class="font-bold text-emerald-400">1. Complete Privacy Air-Gap</div>
                        <p class="text-slate-400 text-[11px]">Confidential PDF statements and transaction records are parsed and stored locally. Zero raw financial data ever traverses the internet.</p>
                    </div>
                    <div class="p-3.5 bg-slate-850 rounded-xl border border-slate-800 space-y-1">
                        <div class="font-bold text-indigo-400">2. Deterministic Accuracy</div>
                        <p class="text-slate-400 text-[11px]">The AI never calculates balances or taxes. Pure Python mathematical algorithms calculate verified figures and inject them as hard facts.</p>
                    </div>
                    <div class="p-3.5 bg-slate-850 rounded-xl border border-slate-800 space-y-1">
                        <div class="font-bold text-purple-400">3. Continuous Guardrails</div>
                        <p class="text-slate-400 text-[11px]">The Grounding Auditor scans every generated response, verifying that every financial citation matches ground truth.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 2: INGESTION & AIR-GAP SEQUENCE FLOW -->
        <div id="section-airgap" class="hidden space-y-6">
            <div class="card space-y-4">
                <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                        <h3 class="font-bold text-sm text-white">Ingestion Pipeline & Query Execution Sequences</h3>
                        <p class="text-xs text-slate-400">Sequence diagrams detailing the zero-leakage statement parsing and copilot query lifecycles</p>
                    </div>
                    <span class="text-xs text-slate-500 font-mono">Sequence Flow</span>
                </div>

                <!-- Sequence Diagram 1: PDF Ingestion -->
                <div class="space-y-2">
                    <h4 class="font-bold text-xs text-emerald-400 uppercase tracking-wider">A. PDF Statement Parsing & PII Redaction Flow</h4>
                    <div class="bg-slate-950 p-6 rounded-xl border border-slate-800 overflow-x-auto">
                        <pre class="mermaid text-xs">
sequenceDiagram
    autonumber
    actor User as User (Drag &amp; Drop)
    participant UI as Web / Fiduciary.app
    participant API as FastAPI (/api/upload)
    participant Parser as PDFStatementParser (pypdf)
    participant Reconciler as Balance Delta Reconciler
    participant Shield as PII Redactor
    participant DB as SQLite (financial.db)

    User->>UI: Drops NatWest Statement PDF
    UI->>API: POST /api/upload (Multipart Bytes)
    API->>Parser: parse_pdf(filename, raw_bytes)
    Note over Parser: 100% In-Memory Extraction.<br/>No temp files on disk.
    Parser->>Shield: Extract Sort Code &amp; Account Number
    Shield->>Shield: Auto-Mask: ••-••-30 &amp; ••••7715
    Parser->>Reconciler: Extract Multi-Column Table &amp; Balances
    Reconciler->>Reconciler: Delta Math: Bal[k] - Bal[k-1] = True Amount
    Note over Reconciler: Discards 'Brought Forward' rows.<br/>Eliminates Debit/Credit guesswork.
    Reconciler->>DB: Upsert Institution ('natwest', 'NatWest')
    Reconciler->>DB: Upsert Account (acc_natwest_imported, masked PII)
    Reconciler->>DB: Insert Categorized Transactions
    DB-->>API: Commit Success (8 txs, £7,428.47 balance)
    API-->>UI: Return JSON Summary
    UI-->>User: Instant Dashboard Refresh
                        </pre>
                    </div>
                </div>

                <!-- Sequence Diagram 2: Copilot Query -->
                <div class="space-y-2 pt-4">
                    <h4 class="font-bold text-xs text-purple-400 uppercase tracking-wider">B. Air-Gapped Copilot Query &amp; Grounding Verification Flow</h4>
                    <div class="bg-slate-950 p-6 rounded-xl border border-slate-800 overflow-x-auto">
                        <pre class="mermaid text-xs">
sequenceDiagram
    autonumber
    actor User as User (Query)
    participant Copilot as AICopilotEngine
    participant WebTools as Zero-Overhead Web Tools (&lt;250ms)
    participant DB as SQLite (financial.db)
    participant PythonCore as Deterministic Profiler &amp; Watchdog
    participant Ollama as Local Ollama (:11434 / Metal GPU)
    participant Guardrail as GroundingAuditor
    participant Tracer as Observability Tracer

    User->>Copilot: "What is the best Cash ISA right now and what is the BoE rate?"
    Copilot->>WebTools: get_live_web_context_with_tools(query)
    WebTools-->>Copilot: Injected Data + Tool Telemetry (fetch_boe_base_rate, fetch_top_savings_and_isas)
    Copilot->>DB: Fetch Accounts, 30d Transactions, Bills
    DB-->>PythonCore: Raw Financial Records
    PythonCore->>PythonCore: Compute exact metrics:<br/>• Liquid Cash: £7,455.73<br/>• Daily Burn: £24.85/day<br/>• Runway: 300 Days
    PythonCore-->>Copilot: Deterministic Context
    Copilot->>Copilot: Track Executed Tools (web + db + watchdog)
    Copilot->>Ollama: POST /api/chat (model: qwen3.5:4b, think: false, keep_alive: 0)
    Note over Ollama: 100% On-Device Offline Inference on Metal GPU.<br/>think: false eliminates 800+ reasoning tokens.<br/>Total latency ~1.2s.
    Ollama-->>Copilot: Grounded Natural Language Response
    Copilot->>Guardrail: audit(response, system_prompt)
    Guardrail->>Guardrail: Validate 4.87%, 3.75%, £7,455.73 against ground truth
    Guardrail-->>Tracer: Status: VERIFIED_GROUNDED (Score: 1.0)
    Tracer->>DB: INSERT INTO llm_traces (includes tools_used_json)
    Copilot-->>User: Grounded Fiduciary Advice &amp; Safety Rating
                        </pre>
                    </div>
                </div>

                <!-- Sequence Diagram 3: LLM-as-a-Judge -->
                <div class="space-y-2 pt-4">
                    <h4 class="font-bold text-xs text-amber-400 uppercase tracking-wider">C. On-Demand LLM-as-a-Judge Evaluation (16GB-Safe)</h4>
                    <div class="bg-slate-950 p-6 rounded-xl border border-slate-800 overflow-x-auto">
                        <pre class="mermaid text-xs">
sequenceDiagram
    autonumber
    actor User as User (./f judge)
    participant Judge as LLMJudge (judge.py)
    participant Ollama as Local Ollama (:11434 / Metal GPU)
    participant DB as SQLite (llm_traces)

    User->>Judge: Evaluate latest trace (./f judge)
    Judge->>DB: Load query, ground-truth context, copilot response
    Judge->>Ollama: POST /api/generate (format: json, think: false, keep_alive: 0, num_ctx: 4096)
    Note over Ollama: Evaluates independently with think: false.<br/>Unloaded from RAM immediately after answering (keep_alive: 0).
    Ollama-->>Judge: JSON: Faithfulness (1.0), Relevance (1.0), Fiduciary Soundness (1.0), Verdict: PASSED
    Judge->>Judge: Overall Score = 0.45 F + 0.35 S + 0.20 R = 1.00
    Judge->>DB: UPDATE llm_traces SET judge_result_json
    Judge-->>User: ⚖️ LLM-AS-A-JUDGE VERDICT: PASSED (Overall: 1.00)
                        </pre>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 3: DETERMINISTIC FINANCIAL CORE -->
        <div id="section-deterministic" class="hidden space-y-6">
            <div class="card space-y-4">
                <div class="border-b border-slate-800 pb-3">
                    <h3 class="font-bold text-sm text-white">Deterministic Financial Core Modules</h3>
                    <p class="text-xs text-slate-400">Pure Python algorithmic engines executing mathematical formulas to the exact penny</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <!-- Module 1 -->
                    <div class="p-4 bg-slate-850 rounded-xl border border-slate-800 space-y-2">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-slate-100 flex items-center space-x-1.5">
                                <span>⏱️</span>
                                <span>Transaction Profiler (profiler.py)</span>
                            </span>
                            <span class="px-2 py-0.5 rounded text-[10px] bg-emerald-950 border border-emerald-800 text-emerald-300 font-semibold">Runway Engine</span>
                        </div>
                        <p class="text-slate-400 text-[11px] leading-relaxed">
                            Aggregates 30-day and 90-day transactions to compute granular outflow burn rates. Divides total liquid cash by daily living expenses to calculate <strong>exact liquid runway days</strong>. Flags recurring inbound top-ups to identify cognitive cash-flow friction.
                        </p>
                        <div class="font-mono text-[10px] p-2 bg-slate-900 rounded text-slate-300 border border-slate-800/80">
                            runway_days = round(liquid_gbp / daily_burn, 1)<br/>
                            monthly_float = round(monthly_burn * 1.0, 2)
                        </div>
                    </div>

                    <!-- Module 2 -->
                    <div class="p-4 bg-slate-850 rounded-xl border border-slate-800 space-y-2">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-slate-100 flex items-center space-x-1.5">
                                <span>🚨</span>
                                <span>Financial Watchdog (watchdog.py)</span>
                            </span>
                            <span class="px-2 py-0.5 rounded text-[10px] bg-rose-950 border border-rose-800 text-rose-300 font-semibold">Anomaly Detector</span>
                        </div>
                        <p class="text-slate-400 text-[11px] leading-relaxed">
                            Maintains strict keyword boundaries (<code class="text-rose-300">\b</code>) and category exclusion lists to identify genuine recurring subscriptions (British Gas, TV Licence, Anthropic). Detects stealth price hikes (>5% jump) and duplicate card charges within 24 hours.
                        </p>
                        <div class="font-mono text-[10px] p-2 bg-slate-900 rounded text-slate-300 border border-slate-800/80">
                            is_hike = latest &gt; prev * 1.05 and (latest - prev) &gt;= 0.50<br/>
                            is_dup = c1.merchant == c2.merchant and c1.amt == c2.amt and abs(c1.dt - c2.dt) &lt;= 1d
                        </div>
                    </div>

                    <!-- Module 3 -->
                    <div class="p-4 bg-slate-850 rounded-xl border border-slate-800 space-y-2">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-slate-100 flex items-center space-x-1.5">
                                <span>🇬🇧</span>
                                <span>UK Tax Optimizer (tax_optimizer.py)</span>
                            </span>
                            <span class="px-2 py-0.5 rounded text-[10px] bg-amber-950 border border-amber-800 text-amber-300 font-semibold">HMRC Statutory Logic</span>
                        </div>
                        <p class="text-slate-400 text-[11px] leading-relaxed">
                            Models UK income tax bands (Basic 20%, Higher 40%, Additional 45%). Calculates the punitive <strong>60% marginal tax trap</strong> between £100,000 and £125,140 caused by Personal Allowance tapering, and computes the exact pension sacrifice required to restore it.
                        </p>
                        <div class="font-mono text-[10px] p-2 bg-slate-900 rounded text-slate-300 border border-slate-800/80">
                            taper_loss = min(12570, max(0, (gross_income - 100000) / 2))<br/>
                            effective_rate = 60.0% if 100000 &lt; income &lt;= 125140
                        </div>
                    </div>

                    <!-- Module 4 -->
                    <div class="p-4 bg-slate-850 rounded-xl border border-slate-800 space-y-2">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-slate-100 flex items-center space-x-1.5">
                                <span>⚡</span>
                                <span>Smart Automation &amp; Sweeper (automation.py)</span>
                            </span>
                            <span class="px-2 py-0.5 rounded text-[10px] bg-teal-950 border border-teal-800 text-teal-300 font-semibold">Cashflow Automation</span>
                        </div>
                        <p class="text-slate-400 text-[11px] leading-relaxed">
                            Detects idle cash drag in 0% current accounts and calculates the optimal sweep into 4.87% Flexible Cash ISAs. Generates statutory cancellation notices under the <strong>UK Consumer Rights Act 2015</strong> with 1-click clipboard export.
                        </p>
                        <div class="font-mono text-[10px] p-2 bg-slate-900 rounded text-slate-300 border border-slate-800/80">
                            sweepable_cash = max(0.0, liquid_gbp - 30d_burn_buffer)<br/>
                            projected_annual_yield = sweepable_cash * 0.0487
                        </div>
                    </div>

                    <!-- Module 5 -->
                    <div class="p-4 bg-slate-850 rounded-xl border border-slate-800 space-y-2">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-slate-100 flex items-center space-x-1.5">
                                <span>🏦</span>
                                <span>Credit &amp; Affordability Engine (credit_affordability.py)</span>
                            </span>
                            <span class="px-2 py-0.5 rounded text-[10px] bg-cyan-950 border border-cyan-800 text-cyan-300 font-semibold">FCA MCOB 11 Underwriter</span>
                        </div>
                        <p class="text-slate-400 text-[11px] leading-relaxed">
                            Underwrites household creditworthiness according to UK Open Banking standards. Detects monthly payroll, living necessities, and contractual debt to compute <strong>Uncommitted Monthly Income (UMI)</strong> and <strong>Debt-to-Income (DTI)</strong>. Scans 90-day history for BNPL instalments (Klarna/Clearpay) and returned direct debits, calculates 4.5x gross mortgage capacity with 7.5% stress testing, and maintains an air-gapped local CRA profile.
                        </p>
                        <div class="font-mono text-[10px] p-2 bg-slate-900 rounded text-slate-300 border border-slate-800/80">
                            UMI = net_monthly_income - (fixed_needs + committed_debt)<br/>
                            mortgage_capacity = (gross_annual * 4.5) - (annual_debt * 3.5)<br/>
                            readiness_score = cashflow(40) + dti(20) + hygiene(25) + identity(15)
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 4: OBSERVABILITY & GUARDRAILS -->
        <div id="section-guardrails" class="hidden space-y-6">
            <div class="card space-y-4">
                <div class="border-b border-slate-800 pb-3">
                    <h3 class="font-bold text-sm text-white">Observability &amp; Grounding Guardrails Pipeline</h3>
                    <p class="text-xs text-slate-400">Real-time verification ensuring no hallucinated figures reach the user</p>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 text-xs">
                    <div class="lg:col-span-7 space-y-3">
                        <h4 class="font-bold text-slate-200">How the Grounding Auditor &amp; Local Evaluation Work</h4>
                        <p class="text-slate-400 leading-relaxed">
                            Every time the AI produces a response (via local Ollama on Apple Silicon Metal GPU), the raw completion is intercepted by the <code>GroundingAuditor</code> before being returned to the UI or terminal.
                        </p>
                        <ul class="space-y-2 text-slate-300">
                            <li class="flex items-start space-x-2">
                                <span class="text-emerald-400 font-bold">1.</span>
                                <span><strong>Entity Extraction:</strong> Scans the response using regular expressions for all currency figures (e.g. <code>£7,455.73</code>, <code>£50.00</code>), percentages (<code>4.87%</code>, <code>3.75%</code>), and runway days.</span>
                            </li>
                            <li class="flex items-start space-x-2">
                                <span class="text-emerald-400 font-bold">2.</span>
                                <span><strong>Ground-Truth Matching:</strong> Checks whether each cited figure was present in the deterministic context passed into the system prompt. Allows mathematical equivalents (e.g. rounded integers).</span>
                            </li>
                            <li class="flex items-start space-x-2">
                                <span class="text-emerald-400 font-bold">3.</span>
                                <span><strong>Scoring &amp; Flagging:</strong> Assigns a Grounding Score from 0.0 to 1.0. If an ungrounded figure is detected, the trace is flagged as <code>UNVERIFIED_FIGURES_DETECTED</code>.</span>
                            </li>
                            <li class="flex items-start space-x-2">
                                <span class="text-emerald-400 font-bold">4.</span>
                                <span><strong>Immutable Trace Logging:</strong> Records the full trace with latency (ms), model identifier, provider (<code>local</code>, <code>gateway</code>, <code>gemini</code>), prompt, response, and audit result to the <code>llm_traces</code> table.</span>
                            </li>
                            <li class="flex items-start space-x-2">
                                <span class="text-amber-400 font-bold">5.</span>
                                <span><strong>Layer 2 - Independent LLM-as-a-Judge (on demand):</strong> <code>./f judge</code> audits the completed interaction using an independent local model on Ollama. It scores Faithfulness, Relevance and Fiduciary Soundness (0–1), returns PASSED / WARNING / FAILED, and stores it in <code>judge_result_json</code>. The regex auditor catches invented numbers; the judge evaluates correct ordering, omissions, and fiduciary advice soundness.</span>
                            </li>
                            <li class="flex items-start space-x-2">
                                <span class="text-amber-400 font-bold">6.</span>
                                <span><strong>16GB RAM Safeguard &amp; Sub-Second Latency:</strong> Both the Copilot and the Judge utilize <code>think: false</code> (bypassing 800+ hidden reasoning tokens to generate text in &lt;1.5s) and <code>keep_alive: 0</code> (unloading models from unified memory immediately after responding). Single-model footprint maintains 70%+ free RAM on a 16GB M3 Mac.</span>
                            </li>
                            <li class="flex items-start space-x-2">
                                <span class="text-cyan-400 font-bold">7.</span>
                                <span><strong>Tool Execution &amp; Provenance Tracking:</strong> Every web scraping call (BoE 3.75%), retail market feed (Trading 212 4.87%, First Direct 7.00%), and database transaction query generates structured telemetry (<code>tool_name</code>, <code>source</code>, <code>latency_ms</code>, <code>summary</code>). Stored in <code>tools_used_json</code> and inspectable via <code>./f tools</code>, <code>./f traces --detail &lt;ID&gt;</code>, or the Web Dashboard tools panel.</span>
                            </li>
                            <li class="flex items-start space-x-2">
                                <span class="text-blue-400 font-bold">8.</span>
                                <span><strong>Enterprise AI Gateway &amp; Router Adapter:</strong> For institutional deployments requiring centralized observability, rate limiting, and model fallback routing (e.g., LiteLLM Proxy, Cloudflare AI Gateway, Portkey), the harness provides an OpenAI-compatible adapter (<code>AI_GATEWAY_URL</code>). The domain-specific <code>GroundingAuditor</code> remains positioned after the gateway, ensuring mathematical truth is audited regardless of proxy routing.</span>
                            </li>
                        </ul>
                    </div>

                    <div class="lg:col-span-5 bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3 font-mono text-[11px]">
                        <div class="text-slate-400 font-sans font-bold text-xs">Live Trace Inspection Schema</div>
                        <div class="space-y-1 text-slate-300">
                            <div><span class="text-emerald-400">id:</span> "tr_2d5a49d95318"</div>
                            <div><span class="text-emerald-400">caller:</span> "copilot"</div>
                            <div><span class="text-emerald-400">provider:</span> "local"</div>
                            <div><span class="text-emerald-400">model:</span> "qwen3.5:4b"</div>
                            <div><span class="text-emerald-400">latency_ms:</span> 1194.5</div>
                            <div><span class="text-emerald-400">tools_used:</span> [{"tool": "fetch_top_savings_and_isas", "lat_ms": 0.0}]</div>
                            <div><span class="text-emerald-400">grounding_status:</span> "VERIFIED_GROUNDED"</div>
                            <div><span class="text-emerald-400">grounding_score:</span> 1.0 (100%)</div>
                            <div><span class="text-emerald-400">judge_verdict:</span> "PASSED (Score: 1.00)"</div>
                            <div><span class="text-emerald-400">verified_figures:</span> ["7.00%", "4.87%", "£2,236.50", "300"]</div>
                            <div><span class="text-emerald-400">unverified_figures:</span> []</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 5: DATABASE SCHEMA & ENTITY MODEL -->
        <div id="section-schema" class="hidden space-y-6">
            <div class="card space-y-4">
                <div class="border-b border-slate-800 pb-3">
                    <h3 class="font-bold text-sm text-white">SQLite Entity Relationship &amp; Data Model</h3>
                    <p class="text-xs text-slate-400">Embedded database structure stored locally at data/financial.db</p>
                </div>

                <div class="bg-slate-950 p-6 rounded-xl border border-slate-800 overflow-x-auto">
                    <pre class="mermaid text-xs">
erDiagram
    institutions ||--o{ accounts : "has"
    accounts ||--o{ transactions : "contains"
    
    institutions {
        string id PK
        string name
        string country
        string status
        timestamp authorized_at
    }

    accounts {
        string id PK
        string institution_id FK
        string name
        string account_type
        string asset_class
        string currency
        string sort_code "Masked Sort Code"
        string account_number "Masked Account Number"
        real current_balance
        real available_balance
        timestamp updated_at
    }

    transactions {
        string id PK
        string account_id FK
        string booking_date
        real amount
        string currency
        string counterparty_name
        string description
        string category
        integer is_recurring
    }

    recurring_bills {
        string id PK
        string merchant
        string category
        real expected_amount
        string frequency
        string last_date
        string next_due_date
        integer is_active
    }

    net_worth_snapshots {
        integer id PK
        string snapshot_date
        real total_assets
        real total_liabilities
        real net_worth
        real liquid_assets
        string breakdown_json
    }

    llm_traces {
        string id PK
        string timestamp
        string caller
        string provider
        string model
        real latency_ms
        string user_prompt
        string system_prompt
        string response
        string grounding_status
        real grounding_score
        string unverified_tokens_json
        string judge_result_json "LLM Judge verdict"
        string tools_used_json "Tool execution metadata"
    }

    copilot_chat {
        integer id PK
        string role
        string content
        string metadata_json
        timestamp created_at
    }

    oauth_tokens {
        string provider PK
        string access_token
        string refresh_token
        timestamp expires_at
        timestamp updated_at
    }

    credit_profile {
        integer id PK
        integer experian "Experian score (0-999)"
        integer equifax "Equifax score (0-1000)"
        integer transunion "TransUnion score (0-710)"
        integer electoral_roll "Electoral roll registered"
        string notes
        timestamp updated_at
    }
                    </pre>
                </div>
            </div>

            <!-- STORAGE ENGINE SELECTION & COMPARATIVE TRADE-OFFS -->
            <div class="card space-y-4 border border-slate-800 bg-slate-900/60 p-5 rounded-xl">
                <div class="border-b border-slate-800 pb-3">
                    <div class="flex items-center space-x-2">
                        <span class="text-amber-400 font-bold">🗄️ Storage Engine Analysis:</span>
                        <span class="text-sm font-semibold text-white">Why SQLite? (SQLite vs DuckDB vs PostgreSQL)</span>
                    </div>
                    <p class="text-xs text-slate-400 mt-1">Architectural decision rationale and pluggable storage adapter trade-offs</p>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs border-collapse">
                        <thead>
                            <tr class="border-b border-slate-800 text-slate-400">
                                <th class="py-2 px-3 font-semibold">Evaluation Criteria</th>
                                <th class="py-2 px-3 font-semibold text-emerald-400">SQLite (Current Choice)</th>
                                <th class="py-2 px-3 font-semibold text-cyan-400">DuckDB (Analytical Vector)</th>
                                <th class="py-2 px-3 font-semibold text-indigo-400">PostgreSQL (Enterprise SaaS)</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y border-slate-800/60 text-slate-300">
                            <tr>
                                <td class="py-2 px-3 font-medium text-white">Deployment Model</td>
                                <td class="py-2 px-3 text-emerald-300">Embedded, zero-daemon, single file</td>
                                <td class="py-2 px-3 text-cyan-300">Embedded, in-process columnar</td>
                                <td class="py-2 px-3 text-indigo-300">Client-server daemon (Docker/service)</td>
                            </tr>
                            <tr>
                                <td class="py-2 px-3 font-medium text-white">Memory Footprint</td>
                                <td class="py-2 px-3 text-emerald-300">~0 MB idle (critical for 16GB Mac)</td>
                                <td class="py-2 px-3 text-cyan-300">Moderate buffer pool memory</td>
                                <td class="py-2 px-3 text-indigo-300">High (shared buffers + connection pool)</td>
                            </tr>
                            <tr>
                                <td class="py-2 px-3 font-medium text-white">Air-Gap &amp; Privacy</td>
                                <td class="py-2 px-3 text-emerald-300">100% local APFS file, zero network ports</td>
                                <td class="py-2 px-3 text-cyan-300">100% local file / Parquet lake</td>
                                <td class="py-2 px-3 text-indigo-300">Network TCP ports, credential surface</td>
                            </tr>
                            <tr>
                                <td class="py-2 px-3 font-medium text-white">Query Latency</td>
                                <td class="py-2 px-3 text-emerald-300">&lt; 0.1 ms (instant transactional lookups)</td>
                                <td class="py-2 px-3 text-cyan-300">&lt; 0.5 ms (vectorized scan over millions)</td>
                                <td class="py-2 px-3 text-indigo-300">1.0 – 5.0 ms (network roundtrip)</td>
                            </tr>
                            <tr>
                                <td class="py-2 px-3 font-medium text-white">Special Superpower</td>
                                <td class="py-2 px-3 text-emerald-300">Zero dependency (Python standard lib)</td>
                                <td class="py-2 px-3 text-cyan-300">Direct Parquet query + native VSS vector search</td>
                                <td class="py-2 px-3 text-indigo-300">Multi-tenant RLS, pgvector, TimescaleDB</td>
                            </tr>
                            <tr>
                                <td class="py-2 px-3 font-medium text-white">When to Switch?</td>
                                <td class="py-2 px-3 text-slate-400">Default for single-user local fiduciary</td>
                                <td class="py-2 px-3 text-cyan-200">Switch if storing 500K+ txs or vector embeddings</td>
                                <td class="py-2 px-3 text-indigo-200">Switch if deploying as a hosted SaaS / multi-user portal</td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px] text-slate-400 pt-2">
                    <div class="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                        <span class="font-bold text-emerald-400 block mb-1">Why SQLite for Fiduciary Agent?</span>
                        On a 16GB Apple Silicon Mac running local LLMs (Ollama qwen3.5:4b), unified RAM is precious. SQLite requires zero background processes, zero ports, and stores encrypted banking records directly in <code class="text-slate-200">data/financial.db</code>.
                    </div>
                    <div class="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                        <span class="font-bold text-cyan-400 block mb-1">When should you use DuckDB?</span>
                        DuckDB is exceptional if you export decades of tick data from brokers (Interactive Brokers, TradingView) or want to execute local vector semantic search across transaction descriptions using DuckDB's <code class="text-slate-200">vss</code> extension.
                    </div>
                    <div class="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                        <span class="font-bold text-indigo-400 block mb-1">When should you use Postgres?</span>
                        Postgres is the standard if migrating this harness into a multi-tenant family-office SaaS platform with concurrent web worker writes, row-level security (RLS), and <code class="text-slate-200">pgvector</code> search in cloud infrastructure.
                    </div>
                </div>
            </div>
        </div>

        <!-- Verification & Air-Gap Testing -->
        <div class="card border border-slate-800 bg-slate-900/60 space-y-3">
            <h3 class="font-bold text-xs uppercase tracking-wider text-slate-300">Technical Privacy &amp; Air-Gap Verification</h3>
            <p class="text-xs text-slate-400 leading-relaxed">
                You can physically verify that zero financial data leaves your laptop using two standard macOS technical procedures:
            </p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div class="p-3.5 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5 font-mono text-[11px]">
                    <div class="font-bold text-white font-sans text-xs">1. Offline Air-Gap Test (Airplane Mode)</div>
                    <p class="text-slate-400 font-sans text-[11px]">Turn off Wi-Fi on your Mac completely. Run:</p>
                    <div class="p-2 bg-slate-900 rounded text-emerald-300 border border-slate-800">
                        ./f copilot "What is my liquid balance?"
                    </div>
                    <p class="text-slate-400 font-sans text-[11px]">The agent answers immediately via local Ollama on Metal GPU with zero network connectivity.</p>
                </div>
                <div class="p-3.5 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5 font-mono text-[11px]">
                    <div class="font-bold text-white font-sans text-xs">2. Network Socket Inspection</div>
                    <p class="text-slate-400 font-sans text-[11px]">Check active TCP connections from Python and local runners:</p>
                    <div class="p-2 bg-slate-900 rounded text-emerald-300 border border-slate-800">
                        lsof -iTCP -sTCP:ESTABLISHED -n -P | grep -E "python|8080|11434|1234"
                    </div>
                    <p class="text-slate-400 font-sans text-[11px]">All connections are local loopbacks (127.0.0.1). Zero outbound external packets.</p>
                </div>
            </div>
        <!-- TAB 6: LEAD DATA ENGINEERING & CLOSED-LOOP RECONCILIATION -->
        <div id="section-dataeng" class="space-y-6 hidden">
            <div class="card space-y-4">
                <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                        <h3 class="font-bold text-sm text-white">Lead Data Engineering &amp; Closed-Loop Reconciliation Architecture</h3>
                        <p class="text-xs text-slate-400">Formal engineering invariants, cryptographic provenance, stateful narrative buffering, and two-stage SLM critic verification</p>
                    </div>
                    <span class="text-xs text-emerald-400 font-mono font-semibold px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800">Discrepancy ≡ £0.00</span>
                </div>

                <!-- Mermaid Diagram: Data Pipeline Invariants -->
                <div class="bg-slate-950 p-6 rounded-xl border border-slate-800 overflow-x-auto">
                    <pre class="mermaid text-xs">
flowchart TD
    subgraph STAGE1["1. RAW STATEMENT INGESTION &amp; CRYPTOGRAPHY"]
        RAW["Raw PDF / CSV Bank Statement"] --> HASH["Compute SHA-256 Batch Fingerprint<br/>file_hash_sha256 = sha256(raw_bytes)"]
        HASH --> BATCH["Register statement_batches Record<br/>Status: PENDING"]
    end

    subgraph STAGE2["2. STATEFUL NORMALIZATION &amp; NARRATIVE BUFFER"]
        BATCH --> TOKEN["Token Lookahead Buffer<br/>• Multi-line narrative stitching<br/>• Overdraft limit bounds filtering"]
        TOKEN --> DATEP["Stateful Same-Day Date Forward-Propagation<br/>current_date binds to trailing sub-rows"]
        DATEP --> DELTA["Running Balance Delta Direction Solver<br/>&Delta;B = B(t) - B(t-1)<br/>+Inflow if &Delta;B &gt; 0, -Outflow if &Delta;B &lt; 0"]
    end

    subgraph STAGE3["3. CLOSED-LOOP DOUBLE-ENTRY SOLVER"]
        DELTA --> SOLVER["Double-Entry Invariant Proof<br/>Opening + &Sigma;Inflows - &Sigma;Outflows == Closing<br/>&Delta; = Calculated - Actual Closing"]
        SOLVER -->|Discrepancy == 0.00| REC["Status: RECONCILED / CLOSING_VERIFIED"]
        SOLVER -->|Discrepancy != 0.00| GAP["Status: UNRECONCILED_GAP (Alert)"]
    end

    subgraph STAGE4["4. IDEMPOTENT PERSISTENCE"]
        REC --> UPSERT["Deterministic Transaction Fingerprinting<br/>id = tx_sha256(account:date:amount:norm_desc)<br/>ON CONFLICT(id) DO UPDATE (Zero Duplicates)"]
        UPSERT --> SQLITE[("Air-Gapped SQLite DB<br/>data/financial.db")]
    end

    subgraph STAGE5["5. TWO-STAGE CRITIC EVALUATION (SLM ISOLATION)"]
        SQLITE --> COPILOT["Stage 1: Generative Copilot<br/>Qwen 3.5 4B (Local Metal GPU)"]
        COPILOT --> CRITIC["Stage 2: Independent Grounded SLM Judge<br/>Llama 3.2 3B (Faithfulness &amp; Math Audit)<br/>keep_alive=0 Metal VRAM Purge"]
        CRITIC --> TRACE["Audit Provenance &amp; Observability Log"]
    end
                    </pre>
                </div>
            </div>

            <!-- In-Depth Engineering Guarantees Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-300">
                <div class="card space-y-3 border-l-4 border-l-emerald-500">
                    <h4 class="font-bold text-white flex items-center space-x-2">
                        <span>📐</span>
                        <span>Double-Entry Mathematical Invariant</span>
                    </h4>
                    <p class="text-slate-400 text-[11px] leading-relaxed">
                        Retail financial applications commonly sum rows independently, causing rounding errors and phantom money when bank statements omit explicit negative signs or roll pending card authorizations.
                    </p>
                    <div class="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-emerald-300">
                        Opening + &Sigma; Inflows - &Sigma; Outflows &equiv; Closing Balance (&Delta; &equiv; &pound;0.00)
                    </div>
                    <p class="text-slate-400 text-[11px] leading-relaxed">
                        If a single transaction is missed, duplicated, or mis-signed, the batch status is immediately flagged as <code class="text-amber-300">UNRECONCILED_GAP</code> with the exact penny variance recorded in SQLite for auditing.
                    </p>
                </div>

                <div class="card space-y-3 border-l-4 border-l-indigo-500">
                    <h4 class="font-bold text-white flex items-center space-x-2">
                        <span>🔐</span>
                        <span>Cryptographic Provenance &amp; Idempotency</span>
                    </h4>
                    <p class="text-slate-400 text-[11px] leading-relaxed">
                        Financial data pipelines must be resilient to repeated ingestion of overlapping statements (e.g. downloading May-June and then June-July statements).
                    </p>
                    <div class="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-cyan-300">
                        tx_id = &quot;tx_&quot; + sha256(account | date | amount | norm_description)[:16]
                    </div>
                    <p class="text-slate-400 text-[11px] leading-relaxed">
                        Every statement batch logs its raw SHA-256 fingerprint in <code class="text-slate-200">statement_batches</code>. Transactions are upserted via deterministic content keys, guaranteeing 100% idempotent deduplication.
                    </p>
                </div>

                <div class="card space-y-3 border-l-4 border-l-purple-500">
                    <h4 class="font-bold text-white flex items-center space-x-2">
                        <span>🧠</span>
                        <span>Stateful Token Normalization Buffer</span>
                    </h4>
                    <p class="text-slate-400 text-[11px] leading-relaxed">
                        UK statements (NatWest, Barclays, HSBC) frequently wrap lengthy payment narratives (e.g. <em>"BILL PAYMENT FROM J BLOGGS REFERENCE EXPENSES JULY"</em>) across 2 to 4 physical PDF lines with no date or balance on trailing rows.
                    </p>
                    <p class="text-slate-400 text-[11px] leading-relaxed">
                        The parser maintains a stateful narrative accumulator that binds orphan description lines to the current active transaction until the next transaction header or balance delta is encountered, while strictly pruning legal footers (<em>"Overdraft Limit £1,000"</em>).
                    </p>
                </div>

                <div class="card space-y-3 border-l-4 border-l-amber-500">
                    <h4 class="font-bold text-white flex items-center space-x-2">
                        <span>⚖️</span>
                        <span>Two-Stage Critic: Grounded SLM Judge Separation</span>
                    </h4>
                    <p class="text-slate-400 text-[11px] leading-relaxed">
                        Standard LLM architectures suffer from confirmation bias when an agent judges its own responses. We enforce an institutional separation of concerns:
                    </p>
                    <ul class="text-[11px] text-slate-400 list-disc list-inside space-y-1">
                        <li><strong>Generative Copilot:</strong> Qwen 3.5 4B generates user summaries and tactical recommendations.</li>
                        <li><strong>Grounded Critic:</strong> Llama 3.2 3B independently evaluates claims against deterministic SQLite ground truth.</li>
                        <li><strong>Zero-Leak Metal VRAM Purge:</strong> Evaluator uses <code class="text-amber-300">keep_alive=0</code>, releasing Unified Memory immediately after evaluation.</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- TAB 7: MOBILE PHONE LINKING & BIOMETRIC OAUTH HANDOFF -->
        <div id="section-mobile" class="hidden space-y-6">
            <div class="card space-y-4">
                <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                        <h3 class="font-bold text-sm text-white">Mobile Phone Linking &amp; Biometric FaceID Architecture</h3>
                        <p class="text-xs text-slate-400">Zero-compromise security flow connecting mobile banking apps to the Mac host</p>
                    </div>
                    <span class="text-xs font-mono px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-300">
                        Universal Link + Biometrics
                    </span>
                </div>
                <p class="text-xs text-slate-300 leading-relaxed">
                    Most UK banking apps (Lloyds, Revolut, Chase, HSBC, NatWest) mandate biometric hardware authentication (FaceID / TouchID) on a smartphone. The fiduciary agent bridges your phone and Mac host via a zero-egress local network architecture:
                </p>
                <div class="bg-slate-950 p-6 rounded-xl border border-slate-800 overflow-x-auto">
                    <pre class="mermaid text-xs">
sequenceDiagram
    autonumber
    actor User as User (Mobile Phone)
    participant Phone as Mobile Browser (Safari/Chrome)
    participant Mac as Fiduciary Host (Mac LAN :8080)
    participant TL as TrueLayer Auth Gateway
    participant BankApp as Bank Native App (Lloyds/Revolut)

    User->>Phone: Open http://[mac-ip]:8080
    Phone->>Mac: GET / (Loads Responsive PWA Dashboard)
    User->>Phone: Tap "Connect Bank"
    Phone->>Mac: GET /truelayer/auth
    Mac-->>Phone: 302 Redirect to auth.truelayer.com
    Phone->>TL: Load Bank Selection
    User->>TL: Selects Bank (e.g. Lloyds)
    TL-->>Phone: Universal Link / App Scheme
    Phone->>BankApp: Deep link launches native banking app
    User->>BankApp: Biometric FaceID / Passcode Auth
    BankApp-->>TL: Grants 90-day read-only consent
    TL-->>Phone: 302 Redirect http://localhost:8080/truelayer/callback?code=AUTH_CODE
    Note over Phone: Mobile browser cannot reach localhost:8080
    User->>Phone: 1. Tap "Paste from Clipboard & Connect"<br/>OR 2. Edit URL localhost -> [mac-ip]
    Phone->>Mac: POST /api/truelayer/exchange {code: "AUTH_CODE"}
    Mac->>TL: POST /connect/token (Candidate URI Matching)
    TL-->>Mac: 200 OK {access_token, refresh_token}
    Mac->>Mac: Store in oauth_tokens & trigger initial sync
    Mac-->>Phone: 200 OK {status: "success", accounts_synced: 2}
    Note over User,Phone: Live balances & transactions appear instantly
                    </pre>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="card space-y-3 border-l-4 border-l-emerald-500">
                    <h4 class="font-bold text-white flex items-center space-x-2">
                        <span>📱</span>
                        <span>The "Localhost Redirect" Invariant</span>
                    </h4>
                    <p class="text-slate-400 text-[11px] leading-relaxed">
                        Strict OAuth 2.0 specifications enforced by the UK Open Banking Implementation Entity (OBIE) and the FCA mandate that callback redirect URIs cannot contain wildcards or arbitrary dynamic LAN IPs.
                    </p>
                    <p class="text-slate-400 text-[11px] leading-relaxed">
                        Redirects must strictly match console-registered endpoints (e.g. <code class="text-slate-200">http://localhost:8080/truelayer/callback</code>). When a mobile banking app completes FaceID authentication, TrueLayer sends the browser back to localhost, which fails on mobile.
                    </p>
                </div>

                <div class="card space-y-3 border-l-4 border-l-cyan-500">
                    <h4 class="font-bold text-white flex items-center space-x-2">
                        <span>📋</span>
                        <span>1-Tap Clipboard Handoff Engine</span>
                    </h4>
                    <p class="text-slate-400 text-[11px] leading-relaxed">
                        We engineered a seamless 1-tap clipboard bridge: when redirected to the unroutable localhost URL, the user simply copies the URL in Mobile Safari and taps <strong class="text-emerald-300">"📋 Paste from Clipboard &amp; Connect"</strong> in the dashboard.
                    </p>
                    <p class="text-slate-400 text-[11px] leading-relaxed">
                        The frontend uses <code class="text-slate-200">navigator.clipboard.readText()</code> to extract the authorization code via regex and asynchronously posts it to <code class="text-cyan-300">/api/truelayer/exchange</code>, eliminating all friction.
                    </p>
                </div>

                <div class="card space-y-3 border-l-4 border-l-purple-500">
                    <h4 class="font-bold text-white flex items-center space-x-2">
                        <span>🔄</span>
                        <span>Multi-Candidate Token Exchange</span>
                    </h4>
                    <p class="text-slate-400 text-[11px] leading-relaxed">
                        OAuth token exchange strictly validates that the <code class="text-slate-200">redirect_uri</code> sent during token exchange matches the URI from authorization.
                    </p>
                    <p class="text-slate-400 text-[11px] leading-relaxed">
                        The backend tests multiple candidate redirect URIs in order (<code class="text-slate-200">localhost:8080</code>, <code class="text-slate-200">127.0.0.1:8080</code>, and active LAN IPs) until TrueLayer accepts the token grant, guaranteeing 100% exchange reliability.
                    </p>
                </div>
            </div>
        </div>

    </main>

    <script>
        function switchArchTab(tabId) {
            const tabs = ['topology', 'airgap', 'deterministic', 'guardrails', 'schema', 'dataeng', 'mobile'];
            tabs.forEach(t => {
                const sec = document.getElementById(`section-${t}`);
                const btn = document.getElementById(`tab-${t}`);
                if (sec && btn) {
                    if (t === tabId) {
                        sec.classList.remove('hidden');
                        btn.classList.add('active');
                        btn.classList.remove('text-slate-400');
                    } else {
                        sec.classList.add('hidden');
                        btn.classList.remove('active');
                        btn.classList.add('text-slate-400');
                    }
                }
            });

            // Render mermaid diagrams only when the section is visible to avoid SVG zero-dimension layout errors
            const currentSec = document.getElementById(`section-${tabId}`);
            if (currentSec) {
                const unrendered = currentSec.querySelectorAll('.mermaid:not([data-processed="true"])');
                if (unrendered.length > 0) {
                    mermaid.run({ nodes: Array.from(unrendered) });
                }
            }
        }
    </script>
</body>
</html>
"""
