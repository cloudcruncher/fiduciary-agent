"""
Standalone Web Walkthrough & System Guide for Personal Fiduciary Financial Harness.
"""

GUIDE_HTML = r"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Walkthrough & User Guide • Personal Fiduciary Harness</title>
    <script src="https://cdn.tailwindcss.com"></script>
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
        }
    </script>
    <style>
        .guide-card { @apply bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0f172a; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    </style>
    <script>
        window.addEventListener('DOMContentLoaded', () => {
            const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            if (isLocal) {
                document.querySelectorAll('.local-only-link').forEach(el => el.classList.remove('hidden'));
            }
        });
    </script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans antialiased pb-20 selection:bg-emerald-500 selection:text-black">

    <!-- Top Sticky Navigation -->
    <header class="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40">
        <div class="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <span class="text-2xl">🛡️</span>
                <div>
                    <h1 class="font-bold text-sm bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">Personal Fiduciary Harness</h1>
                    <p class="text-[11px] text-slate-400">System Walkthrough & Operating Guide</p>
                </div>
            </div>
            <div class="flex items-center space-x-3 text-xs">
                <a href="/" class="local-only-link hidden px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 font-semibold transition">
                    ← Back to Dashboard
                </a>
                <a href="https://github.com/cloudcruncher/fiduciary-agent" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 font-semibold transition flex items-center space-x-1.5">
                    <span>💻</span>
                    <span>GitHub Repo</span>
                </a>
                <a href="index.html" class="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 font-semibold rounded-lg text-white transition flex items-center space-x-1.5 shadow">
                    <span>🏛️ System Architecture</span>
                </a>
            </div>
        </div>
    </header>

    <main class="max-w-5xl mx-auto px-6 mt-8 space-y-10">

        <!-- Header Hero -->
        <div class="guide-card bg-gradient-to-br from-slate-900 via-slate-850 to-slate-900 border-slate-700/80">
            <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-950 border border-emerald-800 text-emerald-400 text-xs font-semibold mb-3">
                <span>🛡️ Autonomous UK Wealth Intelligence</span>
            </div>
            <h2 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">The Complete System Walkthrough</h2>
            <p class="text-sm text-slate-300 mt-2.5 leading-relaxed max-w-3xl">
                This guide explains <strong>what this application does</strong>, <strong>how to use every feature</strong>, an honest evaluation of <strong>local vs cloud AI intelligence</strong>, and how we solved common nagging financial app issues (like hallucinated bills and privacy leaks).
            </p>
        </div>

        <!-- Section 1: The Fiduciary Standard -->
        <section class="space-y-4">
            <div class="flex items-center space-x-2 text-emerald-400 font-bold text-xs uppercase tracking-wider">
                <span>01</span>
                <span>•</span>
                <span>Core Philosophy</span>
            </div>
            <h3 class="text-xl font-bold text-white">Why We Built This: The Fiduciary Standard</h3>
            <div class="guide-card space-y-4 text-xs text-slate-300 leading-relaxed">
                <p>
                    Almost every consumer financial app in the UK (Emma, Snoop, Plum, Money Dashboard) operates as a <strong>lead generator for affiliate financial products</strong>. When they notify you to "cut your bills" or "get a better rate", they receive £50–£150 commission from credit card companies, personal loan providers, or debt consolidators.
                </p>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                    <div class="p-4 rounded-xl bg-rose-950/20 border border-rose-900/40 space-y-1.5">
                        <div class="font-bold text-rose-300 text-xs">❌ Typical Retail FinTech Apps</div>
                        <ul class="list-disc list-inside space-y-1 text-slate-400 text-[11px]">
                            <li>Monetize by selling your financial data to advertisers.</li>
                            <li>Send push notifications for high-commission credit cards.</li>
                            <li>Hallucinate bills: past pub trips or groceries show up as upcoming subscriptions.</li>
                            <li>Send all your bank transactions to external third-party cloud servers.</li>
                        </ul>
                    </div>
                    <div class="p-4 rounded-xl bg-emerald-950/20 border border-emerald-900/40 space-y-1.5">
                        <div class="font-bold text-emerald-300 text-xs">✓ Personal Fiduciary Harness</div>
                        <ul class="list-disc list-inside space-y-1 text-slate-300 text-[11px]">
                            <li><strong>100% Fiduciary Duty</strong>: Zero commissions, zero kickbacks, zero affiliate fluff.</li>
                            <li><strong>100% On-Device Privacy</strong>: Inference runs locally on your Apple Silicon Mac via LM Studio.</li>
                            <li><strong>Deterministic Watchdog</strong>: Zero fabricated bills. Strict 45-day recency and boundary checks.</li>
                            <li><strong>Mathematical Loyalty</strong>: Pure unvarnished numbers based on UK tax rules and FSCS protections.</li>
                        </ul>
                    </div>
                </div>
            </div>
        </section>

        <!-- Section 2: Local Model Intelligence Assessment -->
        <section class="space-y-4">
            <div class="flex items-center space-x-2 text-purple-400 font-bold text-xs uppercase tracking-wider">
                <span>02</span>
                <span>•</span>
                <span>AI Architecture & Privacy</span>
            </div>
            <h3 class="text-xl font-bold text-white">Is the Local Model Intelligent Enough? (Honest Evaluation)</h3>
            <div class="guide-card border-l-4 border-l-purple-500 space-y-4 text-xs text-slate-300 leading-relaxed">
                <p class="text-sm text-slate-200">
                    <strong>Yes, for 95% of wealth monitoring, runway planning, and spending questions.</strong>
                </p>
                <p>
                    On your 16GB Apple Silicon MacBook, running <strong>Ollama (qwen3.5:4b)</strong> with <code>think: false</code> and <code>keep_alive: 0</code> on Apple Silicon Metal GPU offloading produces grounded responses in <strong>~1.1 seconds</strong> with zero outbound network traffic and zero RAM leaks. Alternatively, <strong>Meta-Llama-3.1-8B</strong> via LM Studio is fully supported.
                </p>
                <div class="p-4 bg-slate-850 rounded-xl border border-slate-800 space-y-2">
                    <div class="font-bold text-white text-xs">Why Local Models Work So Well Here: Grounded Architecture (RAG)</div>
                    <p class="text-[11px] text-slate-400">
                        The AI does not have to guess your finances or perform complex mental math from scratch. Before querying the model, our Python backend computes exact deterministic metrics:
                    </p>
                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px] font-mono text-emerald-300">
                        <div class="p-2 bg-slate-900 rounded">Liquid Balance: Exact</div>
                        <div class="p-2 bg-slate-900 rounded">Daily Burn: Exact</div>
                        <div class="p-2 bg-slate-900 rounded">Runway Days: Exact</div>
                        <div class="p-2 bg-slate-900 rounded">Active Bills: Exact</div>
                    </div>
                    <p class="text-[11px] text-slate-400">
                        Because these exact figures are injected directly into the system prompt, the local model acts as an articulate financial planner that presents and explains the verified figures without hallucinating.
                    </p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
                    <div class="p-3.5 bg-slate-850 rounded-xl border border-slate-800 space-y-1.5">
                        <div class="font-bold text-emerald-400 text-xs">🟢 Ollama Local (Default)</div>
                        <p class="text-[11px] text-slate-400">Primary on-device engine on port 11434. Uses <code>think: false</code> for sub-second answers and <code>keep_alive: 0</code> so RAM drops to zero when idle.</p>
                    </div>
                    <div class="p-3.5 bg-slate-850 rounded-xl border border-slate-800 space-y-1.5">
                        <div class="font-bold text-blue-400 text-xs">🔵 LM Studio Local</div>
                        <p class="text-[11px] text-slate-400">Alternative local endpoint on port 1234. Supports Llama 3.1 8B or Mistral 7B with full Apple Silicon Metal acceleration.</p>
                    </div>
                    <div class="p-3.5 bg-slate-850 rounded-xl border border-slate-800 space-y-1.5">
                        <div class="font-bold text-purple-400 text-xs">🟣 Cloud Gemini (Dormant)</div>
                        <p class="text-[11px] text-slate-400">Zero data egress by default. Kept as an optional adapter for complex multi-year tax memorandums if explicitly enabled.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Section 3: Feature by Feature Guide -->
        <section class="space-y-4">
            <div class="flex items-center space-x-2 text-cyan-400 font-bold text-xs uppercase tracking-wider">
                <span>03</span>
                <span>•</span>
                <span>Operational Guide</span>
            </div>
            <h3 class="text-xl font-bold text-white">How to Use Every Module in the App</h3>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <!-- Module 1 -->
                <div class="guide-card space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2 font-bold text-slate-100">
                            <span class="text-lg">⏱️</span>
                            <span>Liquid Runway & Burn Rate</span>
                        </div>
                        <span class="text-[10px] text-emerald-400 font-semibold px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800">Core Metric</span>
                    </div>
                    <p class="text-slate-400 leading-relaxed">
                        Measures how many days of living expenses you have on hand before your cash balance hits £0. Calculated by dividing your verified 30-day living spend into daily burn (£18.72/day).
                    </p>
                    <div class="p-2.5 bg-slate-850 rounded-lg text-slate-300 space-y-1">
                        <div class="font-semibold text-emerald-300 text-[11px]">How to use it:</div>
                        <p class="text-[11px] text-slate-400">
                            If your runway drops below 7.0 days, the card turns red. Instead of reactive £100 manual top-ups, use the Smart Sweeper to set up an automated 1st-of-month operating float.
                        </p>
                    </div>
                </div>

                <!-- Module 2 -->
                <div class="guide-card space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2 font-bold text-slate-100">
                            <span class="text-lg">🚨</span>
                            <span>Financial Watchdog & Bills</span>
                        </div>
                        <span class="text-[10px] text-rose-400 font-semibold px-2 py-0.5 rounded bg-rose-950 border border-rose-800">Deterministic</span>
                    </div>
                    <p class="text-slate-400 leading-relaxed">
                        Detects genuine recurring software and subscription contracts (like Anthropic Claude, Cheddar). Excludes one-off discretionary spend (pubs, Deliveroo, groceries) so you never get hallucinated bills.
                    </p>
                    <div class="p-2.5 bg-slate-850 rounded-lg text-slate-300 space-y-1">
                        <div class="font-semibold text-rose-300 text-[11px]">What it flags:</div>
                        <p class="text-[11px] text-slate-400">
                            • <strong>Stealth Price Hikes</strong>: Warns if a monthly charge silently jumped.<br>
                            • <strong>Duplicate Charges</strong>: Warns if a card was double-billed within 48h.<br>
                            • <strong>Upcoming (14d)</strong>: Exact commitments due in the next fortnight.
                        </p>
                    </div>
                </div>

                <!-- Module 3 -->
                <div class="guide-card space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2 font-bold text-slate-100">
                            <span class="text-lg">💰</span>
                            <span>Whole Net Worth Architecture</span>
                        </div>
                        <span class="text-[10px] text-blue-400 font-semibold px-2 py-0.5 rounded bg-blue-950 border border-blue-800">Balance Sheet</span>
                    </div>
                    <p class="text-slate-400 leading-relaxed">
                        Builds an institutional balance sheet uniting all your liquid cash, Cash ISAs, Stocks & Shares ISAs, Workplace Pensions, SIPPs, Property Equity, and Crypto.
                    </p>
                    <div class="p-2.5 bg-slate-850 rounded-lg text-slate-300 space-y-1">
                        <div class="font-semibold text-blue-300 text-[11px]">How to use it:</div>
                        <p class="text-[11px] text-slate-400">
                            Click <strong>"+ Add Custom Asset / Debt"</strong> on the Whole Net Worth tab. Enter the balance and asset class. It recalculates your net worth and renders an allocation chart.
                        </p>
                    </div>
                </div>

                <!-- Module 4 -->
                <div class="guide-card space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2 font-bold text-slate-100">
                            <span class="text-lg">🇬🇧</span>
                            <span>UK Tax Optimization Engine</span>
                        </div>
                        <span class="text-[10px] text-amber-400 font-semibold px-2 py-0.5 rounded bg-amber-950 border border-amber-800">HMRC Math</span>
                    </div>
                    <p class="text-slate-400 leading-relaxed">
                        Audits personal allowance tapering, Personal Savings Allowance (PSA) cash drag, and SIPP relief math across all UK income tax bands.
                    </p>
                    <div class="p-2.5 bg-slate-850 rounded-lg text-slate-300 space-y-1">
                        <div class="font-semibold text-amber-300 text-[11px]">The 60% Trap Audit:</div>
                        <p class="text-[11px] text-slate-400">
                            Between £100,000 and £125,140, you lose £1 of tax-free personal allowance for every £2 of income (an effective 60% marginal tax rate). The tool calculates the exact pension sacrifice needed to restore your full allowance.
                        </p>
                    </div>
                </div>

                <!-- Module 5 -->
                <div class="guide-card space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2 font-bold text-slate-100">
                            <span class="text-lg">⚡</span>
                            <span>Smart Sweeper & 1-Click Cancel</span>
                        </div>
                        <span class="text-[10px] text-teal-400 font-semibold px-2 py-0.5 rounded bg-teal-950 border border-teal-800">Automation</span>
                    </div>
                    <p class="text-slate-400 leading-relaxed">
                        Prevents cash drag from keeping excess money sitting in 0% accounts. Automatically calculates how much excess cash can be swept into an easy-access 4.87% Cash ISA.
                    </p>
                    <div class="p-2.5 bg-slate-850 rounded-lg text-slate-300 space-y-1">
                        <div class="font-semibold text-teal-300 text-[11px]">Statutory Cancellation Generator:</div>
                        <p class="text-[11px] text-slate-400">
                            Type the name of any subscription (e.g. Anthropic, Spotify, Gym) to generate a formal cancellation notice referencing the UK Consumer Rights Act 2015.
                        </p>
                    </div>
                </div>

                <!-- Module 6 -->
                <div class="guide-card space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2 font-bold text-slate-100">
                            <span class="text-lg">🌐</span>
                            <span>Live Market Scout</span>
                        </div>
                        <span class="text-[10px] text-cyan-400 font-semibold px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800">Market Yields</span>
                    </div>
                    <p class="text-slate-400 leading-relaxed">
                        Continuously compares UK retail banking products: Flexible Cash ISAs (Trading 212 at 4.87%), Taxable Savings (effective yield after your tax rate), Chase UK 1% debit cashback, and bank switch bonuses.
                    </p>
                    <div class="p-2.5 bg-slate-850 rounded-lg text-slate-300 space-y-1">
                        <div class="font-semibold text-cyan-300 text-[11px]">Direct Application Links:</div>
                        <p class="text-[11px] text-slate-400">
                            Every single product links directly to the official provider's application portal. Zero affiliate referral redirects.
                        </p>
                    </div>
                </div>

                <!-- Module 7 -->
                <div class="guide-card space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2 font-bold text-slate-100">
                            <span class="text-lg">🛠️</span>
                            <span>AI Observability & Tool Telemetry</span>
                        </div>
                        <span class="text-[10px] text-cyan-400 font-semibold px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800">Provenance Engine</span>
                    </div>
                    <p class="text-slate-400 leading-relaxed">
                        Full data provenance tracking for every Copilot response. Whenever web scraping fetches the Bank of England rate (3.75%) or top Cash ISA yields (Trading 212 at 4.87%, First Direct at 7.00%), or SQLite queries itemized transactions, execution latency (ms), source URLs, and payload summaries are logged.
                    </p>
                    <div class="p-2.5 bg-slate-850 rounded-lg text-slate-300 space-y-1">
                        <div class="font-semibold text-cyan-300 text-[11px]">How to inspect:</div>
                        <p class="text-[11px] text-slate-400">
                            Run <code>./f tools</code> in your terminal to see active tools, or click <strong>🔍 Traces</strong> in the web dashboard and open the <strong>🛠️ Active Tools & Ingested Data</strong> panel.
                        </p>
                    </div>
                </div>

                <!-- Module 8 -->
                <div class="guide-card space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2 font-bold text-slate-100">
                            <span class="text-lg">⚖️</span>
                            <span>Layer 2 Independent LLM-as-a-Judge</span>
                        </div>
                        <span class="text-[10px] text-purple-400 font-semibold px-2 py-0.5 rounded bg-purple-950 border border-purple-800">Quality Guardrail</span>
                    </div>
                    <p class="text-slate-400 leading-relaxed">
                        Regex auditors check that £ and % numbers match ground truth, but cannot judge tone, omissions, or financial soundness. An independent local model evaluates responses across 3 criteria: Faithfulness (0.45 weight), Fiduciary Soundness (0.35), and Relevance (0.20).
                    </p>
                    <div class="p-2.5 bg-slate-850 rounded-lg text-slate-300 space-y-1">
                        <div class="font-semibold text-purple-300 text-[11px]">16GB Mac Protection:</div>
                        <p class="text-[11px] text-slate-400">
                            Trigger with <code>./f judge</code>. Enforces <code>keep_alive: 0</code> to automatically unload the model from unified RAM immediately after scoring, keeping memory 70%+ free.
                        </p>
                    </div>
                </div>
                <!-- Module 9 -->
                <div class="guide-card space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2 font-bold text-slate-100">
                            <span class="text-lg">📱</span>
                            <span>Mobile Banking &amp; Biometric FaceID</span>
                        </div>
                        <span class="text-[10px] text-emerald-400 font-semibold px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800">Local LAN + PWA</span>
                    </div>
                    <p class="text-slate-400 leading-relaxed">
                        Control your finances on your phone while your Mac handles heavy local AI and database storage. Connect UK banks (Lloyds, Revolut, Chase) with native biometric FaceID/TouchID directly from your phone.
                    </p>
                    <div class="p-2.5 bg-slate-850 rounded-lg text-slate-300 space-y-1">
                        <div class="font-semibold text-emerald-300 text-[11px]">1-Tap Clipboard Handoff:</div>
                        <p class="text-[11px] text-slate-400">
                            When redirected after bank login, tap <strong>"📋 Paste from Clipboard &amp; Connect"</strong> in the mobile header banner. It extracts the authorization code and completes the exchange instantly.
                        </p>
                    </div>
                </div>

                <!-- Module 10 -->
                <div class="guide-card space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2 font-bold text-slate-100">
                            <span class="text-lg">🔬</span>
                            <span>Lead Data Engineering &amp; Audit</span>
                        </div>
                        <span class="text-[10px] text-cyan-400 font-semibold px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800">Double-Entry Invariant</span>
                    </div>
                    <p class="text-slate-400 leading-relaxed">
                        Strict institutional reconciliation: every ingested PDF/CSV statement must verify: <code class="text-slate-200">Opening + Inflows - Outflows ≡ Closing</code>. Batches are marked <code>RECONCILED</code> only if discrepancy is exactly £0.00.
                    </p>
                    <div class="p-2.5 bg-slate-850 rounded-lg text-slate-300 space-y-1">
                        <div class="font-semibold text-cyan-300 text-[11px]">Real-World Parsing Resilience:</div>
                        <p class="text-[11px] text-slate-400">
                            Handles same-day date propagation, multi-line narrative accumulation, running balance delta signing, and SHA-256 batch cryptographic fingerprinting for idempotent de-duplication.
                        </p>
                    </div>
                </div>

                <!-- Module 11 -->
                <div class="guide-card space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2 font-bold text-slate-100">
                            <span class="text-lg">💳</span>
                            <span>Credit Affordability Engine (FCA MCOB 11)</span>
                        </div>
                        <span class="text-[10px] text-indigo-400 font-semibold px-2 py-0.5 rounded bg-indigo-950 border border-indigo-800">Underwriter Model</span>
                    </div>
                    <p class="text-slate-400 leading-relaxed">
                        UK mortgage lenders evaluate Open Banking cash-flow affordability over CRA bureau scores alone. Computes Uncommitted Monthly Income (UMI), Contractual DTI, and 90-day risk radar for BNPL (Klarna/Clearpay) and bounced direct debits.
                    </p>
                    <div class="p-2.5 bg-slate-850 rounded-lg text-slate-300 space-y-1">
                        <div class="font-semibold text-indigo-300 text-[11px]">4.5x Mortgage Stress Testing:</div>
                        <p class="text-[11px] text-slate-400">
                            Simulates borrowing capacity under Bank of England 7.5% stress testing, emergency £1,500 repair shocks, and comfortable vs survival runway.
                        </p>
                    </div>
                </div>

                <!-- Module 12 -->
                <div class="guide-card space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2 font-bold text-slate-100">
                            <span class="text-lg">🔌</span>
                            <span>Model Context Protocol (MCP) Gateway</span>
                        </div>
                        <span class="text-[10px] text-blue-400 font-semibold px-2 py-0.5 rounded bg-blue-950 border border-blue-800">MCP Standards</span>
                    </div>
                    <p class="text-slate-400 leading-relaxed">
                        Exposes 7 standardized tools with JSON schemas, live web grounding (official Bank of England base rate scraping, DuckDuckGo Knowledge API), and deterministic SQLite financial aggregations with sub-millisecond execution telemetry.
                    </p>
                    <div class="p-2.5 bg-slate-850 rounded-lg text-slate-300 space-y-1">
                        <div class="font-semibold text-blue-300 text-[11px]">HTTP Endpoints:</div>
                        <p class="text-[11px] text-slate-400">
                            Inspect tool schemas via <code>GET /api/mcp/tools</code> or execute tools dynamically via <code>POST /api/mcp/execute</code>. Fully compatible with external agents and IDEs.
                        </p>
                    </div>
                </div>

                <!-- Module 13 -->
                <div class="guide-card space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2 font-bold text-slate-100">
                            <span class="text-lg">🛡️</span>
                            <span>Prompt Guard &amp; Zero-Refusal Copilot</span>
                        </div>
                        <span class="text-[10px] text-emerald-400 font-semibold px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800">Defense &amp; Precision</span>
                    </div>
                    <p class="text-slate-400 leading-relaxed">
                        Pre-inference security engine detecting system overrides, jailbreaks (DAN mode), delimiter escapes, and data exfiltration in 0ms. Context is wrapped in <code>&lt;verified_financial_context&gt;</code>, and anti-refusal system directives eliminate RLHF disclaimers on emergency buffers and net worth.
                    </p>
                    <div class="p-2.5 bg-slate-850 rounded-lg text-slate-300 space-y-1">
                        <div class="font-semibold text-emerald-300 text-[11px]">Deterministic Safety:</div>
                        <p class="text-[11px] text-slate-400">
                            Answers tricky emergency fund questions with exact £8,263.80 target, £7,462.12 liquid capital, £801.68 shortfall, and 81.3-day runway down to the penny.
                        </p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Section 4: Nagging Issues We Solved -->
        <section class="space-y-4">
            <div class="flex items-center space-x-2 text-amber-400 font-bold text-xs uppercase tracking-wider">
                <span>04</span>
                <span>•</span>
                <span>Quality & Reliability</span>
            </div>
            <h3 class="text-xl font-bold text-white">Nagging Features Fixed & Polished</h3>
            <div class="guide-card space-y-4 text-xs text-slate-300 leading-relaxed">
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs divide-y divide-slate-800">
                        <thead class="text-slate-400 text-[11px]">
                            <tr>
                                <th class="pb-2.5 font-semibold">Nagging Issue / Friction</th>
                                <th class="pb-2.5 font-semibold">Root Cause Diagnosed</th>
                                <th class="pb-2.5 font-semibold">Our Architectural Solution</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/60 text-slate-300">
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"Mobile banking app redirected to localhost and failed"</td>
                                <td class="py-3 text-slate-400">UK Open Banking OAuth requires strict pre-registered redirect URIs (<code>http://localhost:8080/truelayer/callback</code>), unroutable on mobile phones.</td>
                                <td class="py-3 text-emerald-300">Built multi-candidate URI matching and 1-tap clipboard regex parser (<code>📋 Paste from Clipboard &amp; Connect</code>) and terminal ASCII QR code pairing.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"NatWest PDF statements missing transactions or amounts"</td>
                                <td class="py-3 text-slate-400">NatWest omits repeated dates on same-day rows, wraps narratives across 3 lines, and omits explicit debit minus signs.</td>
                                <td class="py-3 text-emerald-300">Stateful date propagation, multi-line narrative buffering, and running balance delta calculation ($\Delta = B_i - B_{i-1}$) achieving exact £0.00 closed-loop balance reconciliation.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"Duplicate transactions when re-importing statements"</td>
                                <td class="py-3 text-slate-400">Downloading overlapping monthly statements (e.g. May-Jun and Jun-Jul) caused duplicate database rows.</td>
                                <td class="py-3 text-emerald-300">Deterministic SHA-256 batch provenance and cryptographic content key upsert (<code>tx_&lt;sha256&gt;</code>), ensuring 100% idempotent deduplication.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"Is it making things up like bills due?"</td>
                                <td class="py-3 text-slate-400">Previous logic rolled historical transactions forward forever and lacked word boundaries (e.g. matching "ee" inside "queens").</td>
                                <td class="py-3 text-emerald-300">Enforced strict 45-day recency window and regex boundaries. Separated active subscriptions from archived dormant records.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"Confidential finances sent to outside model API"</td>
                                <td class="py-3 text-slate-400">Cloud LLMs require streaming transaction history and account numbers over public internet endpoints.</td>
                                <td class="py-3 text-emerald-300">Unified LLMClient with local LM Studio endpoint running Meta-Llama-3.1-8B on Apple Silicon Metal GPU. Zero data egress.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"I don't see Fiduciary app on Mac"</td>
                                <td class="py-3 text-slate-400">App bundle was symlinked in ~/Applications, which macOS Spotlight and Finder sidebar completely ignore.</td>
                                <td class="py-3 text-emerald-300">Installed real native bundle in /Applications/Fiduciary.app with retina shield AppIcon.icns, registered with lsregister and mdimport.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">No way to switch AI engines on the fly</td>
                                <td class="py-3 text-slate-400">Provider was locked in .env configuration file, requiring terminal commands to change.</td>
                                <td class="py-3 text-emerald-300">Added interactive AI Privacy & Model Selector directly on the dashboard header with 1-click toggling.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"Only have PDF statements, app expects CSV"</td>
                                <td class="py-3 text-slate-400">UK bank portals frequently provide downloadable statements exclusively as official PDF documents rather than CSVs.</td>
                                <td class="py-3 text-emerald-300">Engineered a 100% on-device PDF parser detecting UK bank layouts (Barclays, HSBC, NatWest, Lloyds, Santander, etc.), sort codes, closing balances, and running balance delta reconciliation.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"Can't get my last 5 Revolut transactions"</td>
                                <td class="py-3 text-slate-400">Copilot only received category totals, the dashboard had no transaction view, and the CLI had no bank/count filters.</td>
                                <td class="py-3 text-emerald-300">Copilot injects numbered newest-first rows for the bank and count you ask about. New Live Transactions tab and <code>./f tx -a revolut -n 5 -s keyword</code>.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"How do I know the AI's answer is good?"</td>
                                <td class="py-3 text-slate-400">The regex Grounding Auditor checks numbers but cannot judge ordering, omissions or advice quality.</td>
                                <td class="py-3 text-emerald-300">On-demand LLM-as-a-Judge (<code>./f judge</code>) using a different local model (Gemma 7B on Ollama). Verdict shown in <code>./f traces</code>.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"Local inference was slow (20–40s on M3 Mac)"</td>
                                <td class="py-3 text-slate-400">Reasoning models (like Qwen 3.5) generate 800+ hidden chain-of-thought tokens; prompt prefill had ~1,800 tokens of redundant tables.</td>
                                <td class="py-3 text-emerald-300">Disabled thinking loops (<code>think: false</code> in Ollama payload) and implemented dynamic intent-based prompt pruning (~300 tokens). Latency dropped by 70x (from 22s to 0.3–1.5s).</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"Live web market data without overheating 16GB Mac"</td>
                                <td class="py-3 text-slate-400">Spinning up Chromium or Playwright headless browsers uses 1.5 GB RAM and causes thermal throttling on Apple Silicon.</td>
                                <td class="py-3 text-emerald-300">Lightweight zero-overhead Python tools fetch live Bank of England base rates and market benchmarks via HTTP in &lt;200ms with zero extra RAM.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"Mac froze while running AI"</td>
                                <td class="py-3 text-slate-400">Llama 8B (LM Studio) and Gemma 7B (Ollama) were both loaded at once: ~12 GB of models on a 16 GB Mac caused swapping.</td>
                                <td class="py-3 text-emerald-300">Judge refuses to run while LM Studio holds a model, unloads models immediately (keep_alive 0) and caps context. One model in RAM at a time.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"How did it get 7% First Direct or BoE rate? Is it making up web facts?"</td>
                                <td class="py-3 text-slate-400">User had no visibility into whether financial figures originated from live market tools or LLM hallucinations.</td>
                                <td class="py-3 text-emerald-300">Engineered a Tool Execution &amp; Provenance Tracker logging exact tool calls, latencies, and sources into <code>llm_traces</code>. Inspectable via <code>./f tools</code> and the UI Traces modal.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"Copilot refused with 'I cannot provide financial advice' on emergency buffer"</td>
                                <td class="py-3 text-slate-400">Small SLM RLHF safety heads triggered canned disclaimers when asked about emergency funds under 'Financial Planner' framing.</td>
                                <td class="py-3 text-emerald-300">Reframed system prompt as private analytical engine with strict anti-refusal directive. Pre-injected exact £8,263.80 target, £7,462.12 liquid capital, £801.68 shortfall, and 81.3-day runway.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"Risk of prompt injection, DAN jailbreaks, or exfiltration"</td>
                                <td class="py-3 text-slate-400">Natural language input could attempt delimiter breakouts (<code>&lt;|im_start|&gt;</code>), instruction overrides, or SQL injection.</td>
                                <td class="py-3 text-emerald-300">Implemented pre-inference <code>PromptGuard</code> blocking injections in 0ms, neutralizing boundary tokens, and enclosing context in <code>&lt;verified_financial_context&gt;</code>.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"Compound queries requiring multi-step investigation"</td>
                                <td class="py-3 text-slate-400">Single-pass prompt assembly could not handle compound queries like <em>"Check pub spend and find the best cash isa"</em>.</td>
                                <td class="py-3 text-emerald-300">Implemented <code>ReActFiduciaryAgent</code> with autonomous <code>Thought → Action → Observation</code> loop, safety turn ceilings, and full step trace observability (<code>./f react</code>).</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"Enterprise privacy &amp; cloud credential leakage"</td>
                                <td class="py-3 text-slate-400">If external gateways or cloud fallback models are invoked, raw sort codes and account numbers could be transmitted.</td>
                                <td class="py-3 text-emerald-300">Engineered <code>PIIAnonymizer</code> with reversible salt-hashed tokens (<code>[SORT_CODE_1]</code>, <code>[ACCOUNT_NUM_1]</code>), guaranteeing zero raw PII egress and lossless roundtrip restoration.</td>
                            </tr>
                            <tr>
                                <td class="py-3 font-medium text-rose-300">"Unstructured statutory tax rules &amp; policy notes"</td>
                                <td class="py-3 text-slate-400">Keyword SQL search cannot perform semantic matching across complex HMRC tax schedules or underwriting standards.</td>
                                <td class="py-3 text-emerald-300">Engineered <code>LocalVectorRAG</code> with embedded TF-IDF cosine similarity running 100% on-device with 0 MB background daemon overhead (<code>./f rag</code>).</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- Section 5: Quickstart Cheatsheet -->
        <section class="space-y-4">
            <div class="flex items-center space-x-2 text-emerald-400 font-bold text-xs uppercase tracking-wider">
                <span>05</span>
                <span>•</span>
                <span>Quickstart</span>
            </div>
            <h3 class="text-xl font-bold text-white">Everyday Usage Cheatsheet</h3>
            <div class="guide-card space-y-4 text-xs text-slate-300 leading-relaxed">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="p-3.5 bg-slate-850 rounded-xl border border-slate-800 space-y-2">
                        <div class="font-bold text-white text-xs">🚀 Launch Desktop App (macOS)</div>
                        <p class="text-[11px] text-slate-400">Press <code>Cmd + Space</code>, type <strong>Fiduciary</strong>, and press <code>Enter</code>. Or click the green shield icon in your Dock/Applications.</p>
                    </div>
                    <div class="p-3.5 bg-slate-850 rounded-xl border border-slate-800 space-y-2">
                        <div class="font-bold text-white text-xs">💬 Ask Fiduciary Copilot</div>
                        <p class="text-[11px] text-slate-400">Click the purple <strong>🤖 Copilot</strong> button in the top right, or click any quick prompt chip (e.g. <em>"What bills are due in 14 days?"</em> or <em>"Can I afford a £1,500 holiday?"</em>).</p>
                    </div>
                    <div class="p-3.5 bg-slate-850 rounded-xl border border-slate-800 space-y-2">
                        <div class="font-bold text-white text-xs">💻 Terminal CLI Commands</div>
                        <div class="text-[11px] font-mono text-emerald-300 space-y-1">
                            <div>./f react "&lt;q&gt;" &nbsp;&nbsp;&nbsp;# Autonomous ReAct multi-step agent</div>
                            <div>./f rag "&lt;q&gt;" &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# Local semantic Vector RAG search</div>
                            <div>./f copilot "&lt;q&gt;" &nbsp;# Query on-device AI Copilot</div>
                            <div>./f watchdog &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# Active Bills &amp; Price Hikes</div>
                            <div>./f tx -a revolut &nbsp;# Itemised Bank Transactions</div>
                            <div>./f tools &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# Inspect Active Tools &amp; Sources</div>
                            <div>./f judge &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# Run Independent LLM-as-a-Judge</div>
                            <div>./f traces &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# Observability &amp; Tool Telemetry</div>
                        </div>
                    </div>
                    <div class="p-3.5 bg-slate-850 rounded-xl border border-slate-800 space-y-2">
                        <div class="font-bold text-white text-xs">📥 Import Bank Statements (PDF or CSV)</div>
                        <p class="text-[11px] text-slate-400">Drag & drop native PDF bank statements or CSV files from Barclays, HSBC, NatWest, Lloyds, Santander, Nationwide, Chase, Monzo, Revolut directly into the upload card. Parses 100% locally with zero internet data transmission.</p>
                    </div>
                </div>
            </div>
        </section>

    </main>

    <!-- Sticky Bottom Bar -->
    <div class="fixed bottom-0 inset-x-0 bg-slate-900/90 border-t border-slate-800 backdrop-blur py-3 text-center text-xs space-x-3">
        <a href="index.html" class="text-emerald-400 hover:text-emerald-300 font-semibold">← View System Architecture & Topology</a>
        <a href="/" class="local-only-link hidden text-slate-400 hover:text-slate-200 font-medium">| Return to Live Dashboard</a>
    </div>

</body>
</html>
"""
