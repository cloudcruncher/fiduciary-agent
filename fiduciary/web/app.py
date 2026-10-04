from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from fiduciary.agent.advisor import FiduciaryAdvisor
from fiduciary.agent.automation import SmartAutomationEngine
from fiduciary.agent.copilot import AICopilotEngine
from fiduciary.agent.scout import MarketScout
from fiduciary.analysis.evaluator import FinancialEvaluator
from fiduciary.analysis.profiler import TransactionProfiler
from fiduciary.analysis.tax_optimizer import UKTaxOptimizer
from fiduciary.analysis.watchdog import FinancialWatchdog
from fiduciary.connectors.csv_importer import detect_bank_and_parse
from fiduciary.connectors.wise import WiseClient
from fiduciary.storage.db import (
    clear_chat_history,
    delete_account,
    get_chat_history,
    get_net_worth_breakdown,
    get_recent_transactions,
    init_db,
    save_net_worth_snapshot,
    upsert_custom_asset,
)
from fiduciary.web.architecture import ARCHITECTURE_HTML
from fiduciary.web.guide import GUIDE_HTML

app = FastAPI(title="Personal Fiduciary Financial Harness")

class CopilotQueryRequest(BaseModel):
    query: str

class AssetAddRequest(BaseModel):
    name: str
    asset_class: str
    account_type: Optional[str] = None
    balance: float
    notes: Optional[str] = None

class CancelLetterRequest(BaseModel):
    service_name: str
    monthly_cost: float
    account_reference: Optional[str] = None

class LLMProviderRequest(BaseModel):
    provider: str

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personal Fiduciary Harness • Autonomous UK Wealth Intelligence</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
        .card { @apply bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0f172a; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans antialiased pb-24">

    <!-- Top Sticky Header -->
    <header class="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40">
        <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <span class="text-2xl">🛡️</span>
                <div>
                    <h1 class="font-bold text-base leading-tight bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">Personal Fiduciary Harness</h1>
                    <p class="text-[11px] text-slate-400">Autonomous UK Wealth Architecture • Zero Affiliate Bias</p>
                </div>
            </div>
            
            <div class="flex items-center space-x-2.5">
                <button onclick="location.reload()" title="Reload (Cmd+R)" class="p-1.5 bg-slate-800 hover:bg-slate-700 text-xs rounded-lg border border-slate-700 text-slate-300 transition">
                    🔄
                </button>
                <div id="llm-status-pill" class="hidden md:flex items-center space-x-2 px-3 py-1 bg-slate-800/90 border border-slate-700/80 rounded-full text-xs font-medium cursor-pointer hover:border-slate-600 transition" onclick="openAIModelModal()" title="Click to Switch AI Engine / Privacy Mode">
                    <span id="llm-status-dot" class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span id="llm-status-text" class="text-slate-200">Detecting AI Engine...</span>
                </div>
                <button onclick="switchMainTab('walkthrough')" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold rounded-lg transition flex items-center space-x-1.5 border border-slate-700 text-slate-200 shadow-sm">
                    <span>🧭 Tour & Guide</span>
                </button>
                <a href="/architecture" target="_blank" class="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold rounded-lg transition flex items-center space-x-1.5 border border-slate-700 text-slate-300 shadow-sm" title="System Architecture & Data Flow Design">
                    <span>🏛️ Architecture</span>
                </a>
                <button onclick="openTracesModal()" class="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold rounded-lg transition flex items-center space-x-1.5 border border-slate-700 text-slate-300 shadow-sm" title="Inspect AI Agent Traces, Latency, Grounding Audit & LLM Judge Reports">
                    <span>⚖️ Traces & Judge</span>
                </button>
                <button onclick="toggleCopilot()" class="px-3 py-1.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-xs font-semibold rounded-lg transition flex items-center space-x-1.5 shadow-md text-white">
                    <span>🤖 Copilot</span>
                    <span id="copilot-badge" class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                </button>
                <button onclick="syncAllAccounts()" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold rounded-lg transition flex items-center space-x-1.5 shadow-sm text-white" title="Sync live balances & transactions for Wise & Open Banking (Revolut)">
                    <span id="btn-sync-all-label">⚡ Sync All</span>
                </button>
                <button onclick="connectTrueLayer()" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-xs font-semibold rounded-lg transition flex items-center space-x-1.5 shadow-sm text-white" title="Connect or renew UK Open Banking consent (Revolut, Chase, etc.)">
                    <span id="btn-connect-bank-label">🏦 Connect Bank</span>
                </button>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 mt-6 space-y-6">

        <!-- Executive Metrics Row -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="card border-l-4 border-l-emerald-500">
                <div class="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Total Net Worth</div>
                <div class="text-2xl font-bold mt-1 text-white" id="stat-net-worth">£0.00</div>
                <div class="text-xs text-slate-500 mt-1" id="stat-net-worth-sub">Liquid: £0.00</div>
            </div>
            <div class="card border-l-4 border-l-rose-500" id="card-runway">
                <div class="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Liquid Cash Runway</div>
                <div class="text-2xl font-bold mt-1 text-rose-400" id="stat-runway">0.0 Days</div>
                <div class="text-xs text-slate-500 mt-1" id="stat-daily-burn">Burn: £0/day</div>
            </div>
            <div class="card border-l-4 border-l-cyan-500">
                <div class="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Upcoming Bills (14d)</div>
                <div class="text-2xl font-bold mt-1 text-cyan-400" id="stat-upcoming-bills">£0.00</div>
                <div class="text-xs text-slate-500 mt-1" id="stat-bills-count">0 recurring bills due</div>
            </div>
            <div class="card border-l-4 border-l-amber-500">
                <div class="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Debit Card Spend Drag</div>
                <div class="text-2xl font-bold mt-1 text-amber-400" id="stat-card-drag">+£0.00 / yr</div>
                <div class="text-xs text-slate-500 mt-1" id="stat-card-spend">1% Chase UK reward potential</div>
            </div>
        </div>

        <!-- Navigation Tabs Bar -->
        <div class="flex items-center space-x-2 border-b border-slate-800 pb-2 overflow-x-auto text-xs font-semibold">
            <button onclick="switchMainTab('overview')" id="tab-btn-overview" class="px-3.5 py-1.5 bg-slate-800 text-emerald-400 rounded-lg whitespace-nowrap">🎯 Fiduciary Plan & Holdings</button>
            <button onclick="switchMainTab('networth')" id="tab-btn-networth" class="px-3.5 py-1.5 text-slate-400 hover:text-slate-200 rounded-lg whitespace-nowrap">💰 Whole Net Worth</button>
            <button onclick="switchMainTab('transactions')" id="tab-btn-transactions" class="px-3.5 py-1.5 text-slate-400 hover:text-slate-200 rounded-lg whitespace-nowrap">💳 Live Transactions</button>
            <button onclick="switchMainTab('watchdog')" id="tab-btn-watchdog" class="px-3.5 py-1.5 text-slate-400 hover:text-slate-200 rounded-lg whitespace-nowrap flex items-center space-x-1.5">
                <span>🚨 Watchdog & Bills</span>
                <span id="badge-watchdog-alert" class="hidden px-1.5 py-0.2 bg-rose-500/20 text-rose-300 rounded-full text-[10px]">!</span>
            </button>
            <button onclick="switchMainTab('credit')" id="tab-btn-credit" class="px-3.5 py-1.5 text-slate-400 hover:text-slate-200 rounded-lg whitespace-nowrap flex items-center space-x-1.5">
                <span>🏦 Credit & Borrowing</span>
                <span id="badge-credit-score" class="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-emerald-400 font-semibold border border-slate-700">Audit</span>
            </button>
            <button onclick="switchMainTab('tax')" id="tab-btn-tax" class="px-3.5 py-1.5 text-slate-400 hover:text-slate-200 rounded-lg whitespace-nowrap">🇬🇧 UK Tax Optimization</button>
            <button onclick="switchMainTab('sweep')" id="tab-btn-sweep" class="px-3.5 py-1.5 text-slate-400 hover:text-slate-200 rounded-lg whitespace-nowrap">⚡ Smart Sweeper</button>
            <button onclick="switchMainTab('scout')" id="tab-btn-scout" class="px-3.5 py-1.5 text-slate-400 hover:text-slate-200 rounded-lg whitespace-nowrap">🌐 Market Scout</button>
            <button onclick="switchMainTab('walkthrough')" id="tab-btn-walkthrough" class="px-3.5 py-1.5 text-slate-400 hover:text-slate-200 rounded-lg whitespace-nowrap flex items-center space-x-1.5"><span class="text-emerald-400">🧭</span><span>System Walkthrough & Guide</span></button>
        </div>

        <!-- TAB 1: OVERVIEW & FIDUCIARY PLAN -->
        <div id="section-overview" class="space-y-6">
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

                <!-- Left Column: Holdings & Spending (5 cols) -->
                <div class="lg:col-span-5 space-y-6">
                    <div class="card">
                        <div class="flex items-center justify-between mb-3">
                            <h2 class="font-bold text-xs tracking-wider uppercase text-slate-300">Connected Holdings</h2>
                            <span class="text-[11px] text-slate-500">Live & Verified</span>
                        </div>
                        <div id="accounts-list" class="space-y-2">
                            <div class="text-center py-4 text-slate-500 text-xs">Loading accounts...</div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="flex items-center justify-between mb-3">
                            <h2 class="font-bold text-xs tracking-wider uppercase text-slate-300">30-Day Spending Audit</h2>
                            <span class="text-xs text-emerald-400 font-semibold" id="stat-30d-total">£0.00</span>
                        </div>
                        <div id="spending-categories-list" class="space-y-2.5">
                            <div class="text-center py-3 text-slate-500 text-xs">Loading spending categories...</div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="flex items-center justify-between mb-3">
                            <h2 class="font-bold text-xs tracking-wider uppercase text-slate-300">Top Frequent Venues</h2>
                            <span class="text-[11px] text-slate-500">30 Days</span>
                        </div>
                        <div id="top-merchants-list" class="space-y-2">
                            <div class="text-center py-3 text-slate-500 text-xs">Loading venues...</div>
                        </div>
                    </div>

                    <!-- Drop CSV/PDF Importer -->
                    <div class="card border-dashed border-2 border-slate-800 hover:border-slate-700 transition">
                        <div class="flex items-center justify-between">
                            <h3 class="font-bold text-xs text-slate-300 flex items-center space-x-1.5">
                                <span>📄</span>
                                <span>Import Bank Statement (PDF or CSV)</span>
                            </h3>
                            <span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-300 font-semibold">100% Private & Local</span>
                        </div>
                        <p class="text-[11px] text-slate-400 mt-1">Upload official <strong>PDF statements</strong> or CSV exports from <strong>Barclays, HSBC, NatWest, Lloyds, Santander, Nationwide, Chase, Monzo, Revolut</strong>:</p>
                        <form id="upload-form" class="mt-3 flex items-center space-x-2">
                            <input type="file" id="file-input" accept=".pdf,.csv,application/pdf,text/csv" class="block w-full text-xs text-slate-400 file:mr-2 file:py-1 file:px-2.5 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700 cursor-pointer">
                            <button type="submit" id="btn-upload-statement" class="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold rounded text-white whitespace-nowrap shadow">
                                Parse & Import
                            </button>
                        </form>
                        <div id="upload-status" class="text-xs mt-2 text-emerald-400 hidden"></div>
                    </div>
                </div>

                <!-- Right Column: Fiduciary Recommendations & AI Memo (7 cols) -->
                <div class="lg:col-span-7 space-y-6">
                    <div class="card">
                        <div class="flex items-center justify-between mb-3">
                            <div class="flex items-center space-x-2">
                                <span class="text-lg">🎯</span>
                                <h2 class="font-bold text-xs tracking-wider uppercase text-slate-300">Fiduciary Action Plan</h2>
                            </div>
                            <div class="flex items-center space-x-2">
                                <button onclick="generateAIBriefing()" id="btn-ai-briefing" class="px-2.5 py-1 bg-purple-600 hover:bg-purple-500 text-xs font-semibold rounded-md text-white transition flex items-center space-x-1 shadow">
                                    <span>🤖 Live AI Memo</span>
                                </button>
                                <div class="text-xs bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded-full font-semibold">
                                    Projected: <span id="total-projected-gain">+£0/yr</span>
                                </div>
                            </div>
                        </div>
                        <p class="text-xs text-slate-400 mb-4">Select items to calculate combined net annual upside:</p>

                        <div id="ai-briefing-box" class="hidden mb-4 p-4 rounded-xl bg-purple-950/20 border border-purple-800/40 text-xs leading-relaxed space-y-2">
                            <div class="flex items-center justify-between border-b border-purple-800/40 pb-2">
                                <span class="font-bold text-purple-300 text-xs flex items-center space-x-1">
                                    <span>🤖</span><span>AI Fiduciary Strategy Memorandum</span>
                                </span>
                                <span class="text-[10px] text-purple-400">Powered by Gemini</span>
                            </div>
                            <div id="ai-briefing-content" class="text-slate-200 prose prose-invert max-w-none text-xs whitespace-pre-line"></div>
                        </div>

                        <div id="action-cards" class="space-y-3">
                            <!-- Rendered by JS -->
                        </div>
                    </div>
                </div>

            </div>
        </div>

        <!-- TAB 2: WHOLE NET WORTH & MULTI-ASSET -->
        <div id="section-networth" class="hidden space-y-6">
            <div class="card flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                    <h2 class="text-lg font-bold text-white">Whole-of-Wealth Balance Sheet</h2>
                    <p class="text-xs text-slate-400 mt-1">Multi-asset tracking across Cash, Investments, Pensions, Property, and Liabilities.</p>
                </div>
                <button onclick="openAddAssetModal()" class="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold rounded-lg transition text-white flex items-center space-x-1.5 shadow">
                    <span>+ Add Custom Asset / Debt</span>
                </button>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div class="lg:col-span-5 card flex flex-col items-center justify-center">
                    <h3 class="font-bold text-xs uppercase text-slate-400 mb-4 w-full text-left">Asset Class Allocation</h3>
                    <div class="w-full max-w-xs h-64 flex items-center justify-center">
                        <canvas id="netWorthChart"></canvas>
                    </div>
                </div>

                <div class="lg:col-span-7 card">
                    <h3 class="font-bold text-xs uppercase text-slate-400 mb-3">Balance Sheet Breakdown</h3>
                    <div id="networth-tables" class="space-y-4">
                        <!-- Rendered by JS -->
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB: TRANSACTIONS FEED -->
        <div id="section-transactions" class="hidden space-y-4">
            <div class="card space-y-4">
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-3">
                    <div>
                        <h2 class="text-sm font-bold text-white flex items-center space-x-2">
                            <span>💳</span>
                            <span>Live Bank Transactions Feed</span>
                        </h2>
                        <p class="text-xs text-slate-400 mt-0.5">Itemized transaction records ingested from Open Banking (Revolut, Wise) &amp; Bank Statements (NatWest)</p>
                    </div>
                    <div class="flex items-center space-x-2">
                        <span id="tx-count-badge" class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 border border-slate-700 text-slate-300">0 transactions</span>
                    </div>
                </div>

                <!-- Filters Bar -->
                <div class="grid grid-cols-1 sm:grid-cols-12 gap-3 text-xs">
                    <div class="sm:col-span-4">
                        <label class="block text-[11px] text-slate-400 mb-1 font-medium">Filter by Bank / Account</label>
                        <select id="tx-filter-bank" onchange="loadTransactionsFeed()" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-200">
                            <option value="">All Accounts &amp; Banks</option>
                            <option value="revolut">Revolut (Open Banking)</option>
                            <option value="natwest">NatWest (Imported Statement)</option>
                            <option value="wise">Wise (Multi-Currency)</option>
                        </select>
                    </div>
                    <div class="sm:col-span-3">
                        <label class="block text-[11px] text-slate-400 mb-1 font-medium">Record Limit</label>
                        <select id="tx-filter-limit" onchange="loadTransactionsFeed()" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-200">
                            <option value="5">Last 5 Transactions</option>
                            <option value="10">Last 10 Transactions</option>
                            <option value="25">Last 25 Transactions</option>
                            <option value="50" selected>Last 50 Transactions</option>
                            <option value="all">All Stored Records</option>
                        </select>
                    </div>
                    <div class="sm:col-span-5">
                        <label class="block text-[11px] text-slate-400 mb-1 font-medium">Search Keyword / Merchant</label>
                        <input id="tx-filter-search" oninput="loadTransactionsFeed()" type="text" placeholder="e.g. Sainsburys, Sumup, British Gas..." class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-200 placeholder-slate-500">
                    </div>
                </div>

                <!-- Transactions Table -->
                <div class="overflow-x-auto">
                    <table class="w-full text-left">
                        <thead>
                            <tr class="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400">
                                <th class="py-2.5">Date</th>
                                <th class="py-2.5">Bank</th>
                                <th class="py-2.5">Counterparty / Merchant</th>
                                <th class="py-2.5">Category</th>
                                <th class="py-2.5 text-right">Amount</th>
                            </tr>
                        </thead>
                        <tbody id="tx-table-body" class="divide-y divide-slate-800/40">
                            <!-- Injected by loadTransactionsFeed -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 3: WATCHDOG & RECURRING BILLS -->
        <div id="section-watchdog" class="hidden space-y-6">
            <!-- Liquidity Warning Banner -->
            <div id="watchdog-shortfall-box" class="hidden p-4 rounded-xl border"></div>

            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div class="lg:col-span-6 space-y-6">
                    <!-- Price Hikes -->
                    <div class="card border-l-4 border-l-rose-500">
                        <div class="flex items-center justify-between mb-3">
                            <h3 class="font-bold text-xs uppercase text-rose-400 flex items-center space-x-1.5">
                                <span>🚨</span><span>Detected Price Hikes & Stealth Increases</span>
                            </h3>
                            <span id="badge-price-hikes-count" class="text-xs font-bold text-rose-400">0 alerts</span>
                        </div>
                        <p class="text-xs text-slate-400 mb-3">Subscriptions that silently increased in cost between billing cycles:</p>
                        <div id="price-hikes-list" class="space-y-2.5"></div>
                    </div>

                    <!-- Duplicate Charges -->
                    <div class="card border-l-4 border-l-amber-500">
                        <div class="flex items-center justify-between mb-3">
                            <h3 class="font-bold text-xs uppercase text-amber-400 flex items-center space-x-1.5">
                                <span>⚠️</span><span>Suspicious Duplicate Charges (&lt;48h)</span>
                            </h3>
                            <span id="badge-duplicates-count" class="text-xs font-bold text-amber-400">0 alerts</span>
                        </div>
                        <div id="duplicate-charges-list" class="space-y-2"></div>
                    </div>
                </div>

                <div class="lg:col-span-6 space-y-6">
                    <div class="card">
                        <div class="flex items-center justify-between mb-3">
                            <h3 class="font-bold text-xs uppercase text-slate-300">📅 Upcoming Bills & Direct Debits (Next 14 Days)</h3>
                            <span class="text-xs font-bold text-cyan-400" id="stat-upcoming-14d-total">£0.00</span>
                        </div>
                        <div id="upcoming-bills-list" class="space-y-2"></div>
                    </div>

                    <div class="card space-y-3">
                        <div class="flex items-center justify-between border-b border-slate-800 pb-2.5">
                            <div>
                                <h3 class="font-bold text-xs uppercase text-slate-300">Verified Active Subscriptions (&le;45 Days)</h3>
                                <p class="text-[10px] text-slate-500">Strictly recurring software & contracts. Discretionary spending excluded to eliminate false alarms.</p>
                            </div>
                            <span class="text-xs font-bold text-emerald-400" id="badge-active-contracts-count">0 active</span>
                        </div>
                        <div id="active-contracts-list" class="space-y-2"></div>
                    </div>

                    <div class="card p-4">
                        <details class="group">
                            <summary class="cursor-pointer font-bold text-xs uppercase text-slate-400 flex items-center justify-between list-none">
                                <span class="flex items-center space-x-2">
                                    <span>📁</span>
                                    <span>Historical Dormant Subscriptions (&gt;45 Days Inactive)</span>
                                </span>
                                <span id="badge-inactive-contracts-count" class="text-xs text-slate-500 group-open:rotate-180 transition-transform">▼</span>
                            </summary>
                            <div id="inactive-contracts-list" class="mt-3 space-y-2 pt-2 border-t border-slate-800/80"></div>
                        </details>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB: CREDIT & BORROWING HEALTH (FCA MCOB 11 UNDERWRITER AUDIT) -->
        <div id="section-credit" class="hidden space-y-6">

            <!-- Executive Banner & Readiness Score -->
            <div class="card bg-gradient-to-br from-slate-900 via-slate-850 to-slate-900 border border-slate-700/80 shadow-xl">
                <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
                    <div class="space-y-2 max-w-2xl">
                        <div class="flex items-center space-x-2.5">
                            <span class="text-xl">🏦</span>
                            <h2 class="text-lg font-bold text-white tracking-wide">Credit & Borrowing Health Audit</h2>
                            <span id="credit-tier-badge" class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-900/60 text-blue-300 border border-blue-700/60">
                                Tier 2 • Mainstream
                            </span>
                            <span class="text-[10px] px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-300 font-semibold">
                                100% Local Privacy
                            </span>
                        </div>
                        <p class="text-xs text-slate-300 leading-relaxed" id="credit-tier-memo">
                            Institutional Underwriter Standard (FCA MCOB 11). Evaluates live Open Banking cash-flow affordability, debt service, BNPL usage, and payment integrity without transmitting your financial data off this device.
                        </p>
                    </div>

                    <!-- Score Card / Gauge -->
                    <div class="flex items-center space-x-5 bg-slate-950/70 p-4 rounded-xl border border-slate-800 min-w-[280px]">
                        <div class="text-center">
                            <div class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Borrowing Readiness</div>
                            <div class="text-4xl font-black mt-0.5 text-white flex items-baseline justify-center space-x-1">
                                <span id="credit-score-val" class="text-emerald-400">84</span>
                                <span class="text-xs text-slate-500 font-semibold">/ 100</span>
                            </div>
                        </div>
                        <div class="h-10 w-[1px] bg-slate-800"></div>
                        <div class="flex-1 space-y-1.5 text-[11px]">
                            <div class="flex justify-between text-slate-400">
                                <span>Cash Flow (UMI)</span>
                                <span id="comp-cashflow" class="text-slate-200 font-bold">40/40</span>
                            </div>
                            <div class="flex justify-between text-slate-400">
                                <span>Debt Ratio (DTI)</span>
                                <span id="comp-dti" class="text-slate-200 font-bold">20/20</span>
                            </div>
                            <div class="flex justify-between text-slate-400">
                                <span>Risk Record (BNPL/DD)</span>
                                <span id="comp-hygiene" class="text-amber-400 font-bold">14/25</span>
                            </div>
                            <div class="flex justify-between text-slate-400">
                                <span>Stability / Identity</span>
                                <span id="comp-stability" class="text-slate-200 font-bold">15/15</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 3-Column Core Underwriter Grid -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

                <!-- 1. Cash-Flow Affordability (MCOB 11) -->
                <div class="card space-y-4 border-t-4 border-t-cyan-500">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-2.5">
                        <div class="flex items-center space-x-2">
                            <span class="text-base">📊</span>
                            <h3 class="font-bold text-xs uppercase tracking-wider text-slate-200">Cash-Flow Affordability</h3>
                        </div>
                        <span class="text-[10px] text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800 font-medium">MCOB 11</span>
                    </div>

                    <div class="space-y-3 text-xs">
                        <div class="flex justify-between items-center p-2.5 bg-slate-850 rounded-lg">
                            <span class="text-slate-400">Verified Monthly Net Pay</span>
                            <span class="text-white font-bold text-sm" id="cf-monthly-net">£0.00</span>
                        </div>
                        <div class="flex justify-between items-center p-2.5 bg-slate-850 rounded-lg">
                            <span class="text-slate-400">Estimated Gross Annual Pay</span>
                            <span class="text-slate-200 font-semibold" id="cf-annual-gross">£0.00</span>
                        </div>
                        <div class="flex justify-between items-center p-2 bg-slate-900 border border-slate-800 rounded">
                            <span class="text-slate-400">Fixed Living Commitments</span>
                            <span class="text-rose-300 font-medium" id="cf-fixed-needs">-£0.00/mo</span>
                        </div>
                        <div class="flex justify-between items-center p-2 bg-slate-900 border border-slate-800 rounded">
                            <span class="text-slate-400">Contractual Debt Repayments</span>
                            <span class="text-rose-300 font-medium" id="cf-debt-commitments">-£0.00/mo</span>
                        </div>

                        <!-- UMI Highlight -->
                        <div class="p-3 bg-cyan-950/20 border border-cyan-800/60 rounded-xl space-y-1">
                            <div class="flex justify-between items-center">
                                <span class="text-[11px] font-bold uppercase text-cyan-300">Uncommitted Monthly Income (UMI)</span>
                                <span class="text-xs px-2 py-0.5 rounded-full bg-cyan-900/60 text-cyan-200 font-bold" id="cf-umi-pct">0% surplus</span>
                            </div>
                            <div class="text-xl font-extrabold text-cyan-400" id="cf-umi-amount">£0.00 / mo</div>
                            <p class="text-[10px] text-slate-400">Free uncommitted cash flow available after meeting all contractual debts, shelter, and essential living costs.</p>
                        </div>

                        <!-- DTI Ratio -->
                        <div class="p-2.5 bg-slate-850 rounded-lg space-y-1.5">
                            <div class="flex justify-between text-[11px]">
                                <span class="text-slate-400">Debt-to-Income (DTI)</span>
                                <span class="text-emerald-400 font-bold" id="cf-dti-val">0.0%</span>
                            </div>
                            <div class="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                                <div id="cf-dti-bar" class="bg-emerald-500 h-1.5 rounded-full" style="width: 10%"></div>
                            </div>
                            <div class="text-[10px] text-slate-500 flex justify-between">
                                <span>Prime &lt;20%</span>
                                <span>Mainstream &lt;35%</span>
                                <span>High Risk &gt;50%</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 2. Underwriter Risk Flags Scanner -->
                <div class="card space-y-4 border-t-4 border-t-amber-500">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-2.5">
                        <div class="flex items-center space-x-2">
                            <span class="text-base">🛡️</span>
                            <h3 class="font-bold text-xs uppercase tracking-wider text-slate-200">Risk Flag Scanner</h3>
                        </div>
                        <span class="text-[10px] text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800 font-medium">Underwriter Radar</span>
                    </div>

                    <div class="space-y-2.5 text-xs" id="underwriter-flags-container">
                        <!-- Flag items rendered dynamically -->
                    </div>
                </div>

                <!-- 3. Indicative Mortgage Capacity -->
                <div class="card space-y-4 border-t-4 border-t-emerald-500">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-2.5">
                        <div class="flex items-center space-x-2">
                            <span class="text-base">🏡</span>
                            <h3 class="font-bold text-xs uppercase tracking-wider text-slate-200">Indicative Mortgage Capacity</h3>
                        </div>
                        <span class="text-[10px] text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800 font-medium">4.5x Multiplier</span>
                    </div>

                    <div class="space-y-3 text-xs">
                        <div class="p-3 bg-emerald-950/20 border border-emerald-800/60 rounded-xl space-y-1">
                            <div class="text-[11px] font-bold uppercase text-emerald-300">Net Maximum Borrowing Capacity</div>
                            <div class="text-2xl font-extrabold text-emerald-400" id="mc-net-capacity">£0.00</div>
                            <div class="text-[10px] text-slate-400 flex justify-between pt-1">
                                <span id="mc-gross-base">Gross Base (4.5x): £0.00</span>
                                <span id="mc-debt-deduction" class="text-rose-400">Debt drag: -£0.00</span>
                            </div>
                        </div>

                        <div class="grid grid-cols-2 gap-2.5">
                            <div class="p-2.5 bg-slate-850 rounded-lg border border-slate-800">
                                <div class="text-[10px] text-slate-400 uppercase font-semibold">Indicative 25-yr Fixed</div>
                                <div class="text-base font-bold text-white mt-0.5" id="mc-indicative-repayment">£0.00<span class="text-[10px] text-slate-500 font-normal">/mo</span></div>
                                <div class="text-[10px] text-emerald-400 mt-0.5" id="mc-indicative-rate">4.40% rate</div>
                            </div>
                            <div class="p-2.5 bg-slate-850 rounded-lg border border-slate-800">
                                <div class="text-[10px] text-slate-400 uppercase font-semibold">BoE +3% Stress Test</div>
                                <div class="text-base font-bold text-amber-300 mt-0.5" id="mc-stress-repayment">£0.00<span class="text-[10px] text-slate-500 font-normal">/mo</span></div>
                                <div class="text-[10px] text-amber-400 mt-0.5" id="mc-stress-rate">7.50% rate</div>
                            </div>
                        </div>

                        <div class="p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-[11px] space-y-1">
                            <div class="flex justify-between items-center">
                                <span class="text-slate-400">Stress Test UMI Headroom:</span>
                                <span class="font-bold text-emerald-400" id="mc-stress-headroom">+£0.00/mo surplus</span>
                            </div>
                            <p class="text-[10px] text-slate-500">MCOB affordability buffer ensures household remains solvent if BoE base rates rise to 7.5%.</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Emergency Runway & Financial Stress Simulator -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

                <!-- Stress Scenarios (7 cols) -->
                <div class="lg:col-span-7 card space-y-4">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-2.5">
                        <div class="flex items-center space-x-2">
                            <span class="text-base">⚡</span>
                            <h3 class="font-bold text-xs uppercase tracking-wider text-slate-200">Financial Stress & Runway Simulator</h3>
                        </div>
                        <div class="flex items-center space-x-3 text-xs">
                            <span class="text-slate-400">Comfortable: <strong class="text-emerald-400" id="sim-runway-comfort">0.0 mo</strong></span>
                            <span class="text-slate-400">Survival: <strong class="text-cyan-400" id="sim-runway-survival">0.0 mo</strong></span>
                        </div>
                    </div>

                    <div class="space-y-3" id="stress-scenarios-container">
                        <!-- Scenario rows rendered dynamically -->
                    </div>

                    <!-- Inflation Erosion Drag Callout -->
                    <div class="p-3 bg-slate-850/80 border border-slate-800 rounded-xl flex items-center justify-between text-xs">
                        <div class="space-y-0.5">
                            <div class="font-bold text-slate-300 flex items-center space-x-1.5">
                                <span>📉</span>
                                <span>UK CPI Inflation Erosion Drag (3.2%)</span>
                            </div>
                            <p class="text-[11px] text-slate-500">Uninvested current account cash loses purchasing power every month.</p>
                        </div>
                        <div class="text-right">
                            <div class="text-rose-400 font-bold" id="sim-inflation-loss">-£0.00 / yr</div>
                            <div class="text-[10px] text-emerald-400" id="sim-isa-recovery">+£0.00 / yr potential in Cash ISA</div>
                        </div>
                    </div>
                </div>

                <!-- Self-Reported Credit Bureau Tracking (5 cols) -->
                <div class="lg:col-span-5 card space-y-4">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-2.5">
                        <div class="flex items-center space-x-2">
                            <span class="text-base">📋</span>
                            <h3 class="font-bold text-xs uppercase tracking-wider text-slate-200">Credit Bureau Tracking</h3>
                        </div>
                        <span class="text-[10px] text-slate-400">Self-Reported Baseline</span>
                    </div>

                    <p class="text-[11px] text-slate-400 leading-relaxed">
                        Track your 3 major UK Credit Reference Agency (CRA) scores locally. Modern mortgage underwriters evaluate cash-flow affordability (UMI/DTI) first, but bureau scores verify your identity and credit history.
                    </p>

                    <div class="space-y-3 text-xs">
                        <div class="grid grid-cols-3 gap-2">
                            <div>
                                <label class="text-[10px] uppercase font-semibold text-slate-400 block mb-1">Experian (999)</label>
                                <input type="number" id="input-score-experian" min="0" max="999" placeholder="865" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs font-bold text-white focus:outline-none focus:border-emerald-500">
                            </div>
                            <div>
                                <label class="text-[10px] uppercase font-semibold text-slate-400 block mb-1">Equifax (1000)</label>
                                <input type="number" id="input-score-equifax" min="0" max="1000" placeholder="740" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs font-bold text-white focus:outline-none focus:border-emerald-500">
                            </div>
                            <div>
                                <label class="text-[10px] uppercase font-semibold text-slate-400 block mb-1">TransUnion (710)</label>
                                <input type="number" id="input-score-transunion" min="0" max="710" placeholder="645" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs font-bold text-white focus:outline-none focus:border-emerald-500">
                            </div>
                        </div>

                        <div class="flex items-center justify-between p-2.5 bg-slate-850 rounded-lg border border-slate-800">
                            <div class="flex items-center space-x-2">
                                <input type="checkbox" id="input-score-electoral" class="rounded bg-slate-800 border-slate-700 text-emerald-500 focus:ring-0">
                                <label for="input-score-electoral" class="text-xs text-slate-300 font-medium cursor-pointer">Registered on UK Electoral Roll</label>
                            </div>
                            <span class="text-[10px] text-emerald-400 font-semibold">+15 pts</span>
                        </div>

                        <div class="flex items-center justify-between pt-1">
                            <span id="credit-save-status" class="text-[11px] text-slate-500">Local SQLite storage</span>
                            <button onclick="saveCreditScores()" id="btn-save-credit-scores" class="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-semibold text-xs transition shadow-sm">
                                Save Bureau Scores
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Prioritized Action Playbook -->
            <div class="card space-y-3">
                <div class="flex items-center justify-between border-b border-slate-800 pb-2.5">
                    <div class="flex items-center space-x-2">
                        <span class="text-base">🎯</span>
                        <h3 class="font-bold text-xs uppercase tracking-wider text-slate-200">Underwriter Action Playbook</h3>
                    </div>
                    <span class="text-[10px] text-slate-400">Automated Remediation Roadmap</span>
                </div>
                <div id="credit-playbook-cards" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    <!-- Action Playbook cards rendered dynamically -->
                </div>
            </div>

        </div>

        <!-- TAB 4: UK TAX OPTIMIZATION -->
        <div id="section-tax" class="hidden space-y-6">
            <div class="card">
                <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div>
                        <h2 class="text-lg font-bold text-white">UK Tax & Wealth Optimization Engine</h2>
                        <p class="text-xs text-slate-400 mt-1">Audit personal allowance tapering, 60% marginal tax trap, and SIPP relief.</p>
                    </div>
                    <div class="flex items-center space-x-2">
                        <label class="text-xs text-slate-400">Annual Gross Income (£):</label>
                        <input type="number" id="input-tax-income" value="60000" step="5000" class="px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs font-bold text-white w-32 focus:outline-none focus:border-emerald-500">
                        <button onclick="recalculateTaxAudit()" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold rounded-lg text-white">Recalculate</button>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div class="lg:col-span-6 space-y-6">
                    <!-- 60% Trap Card -->
                    <div class="card" id="card-60-trap">
                        <h3 class="font-bold text-xs uppercase tracking-wider text-slate-300 mb-2">60% Personal Allowance Taper Trap</h3>
                        <div id="content-60-trap" class="text-xs space-y-2"></div>
                    </div>

                    <!-- Personal Savings Allowance Drag -->
                    <div class="card">
                        <h3 class="font-bold text-xs uppercase tracking-wider text-slate-300 mb-2">Personal Savings Allowance (PSA) Drag</h3>
                        <div id="content-psa-drag" class="text-xs space-y-2"></div>
                    </div>
                </div>

                <div class="lg:col-span-6 card">
                    <h3 class="font-bold text-xs uppercase tracking-wider text-slate-300 mb-3">Pension / SIPP Immediate Relief Math</h3>
                    <p class="text-xs text-slate-400 mb-3">Tax relief calculated on a standard £1,000 gross pension contribution:</p>
                    <div id="content-sipp-relief" class="space-y-2.5"></div>
                </div>
            </div>
        </div>

        <!-- TAB 5: SMART SWEEPER -->
        <div id="section-sweep" class="hidden space-y-6">
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div class="lg:col-span-7 space-y-6">
                    <div class="card border-l-4 border-l-emerald-500">
                        <h2 class="font-bold text-sm text-white mb-2">Smart Cash Sweeper</h2>
                        <div id="sweep-status-box" class="text-xs leading-relaxed space-y-2"></div>
                    </div>

                    <div class="card">
                        <h3 class="font-bold text-xs uppercase text-slate-300 mb-2">Automated Monthly Standing Order Plan</h3>
                        <div id="standing-order-box" class="text-xs space-y-2"></div>
                    </div>
                </div>

                <div class="lg:col-span-5 card">
                    <h3 class="font-bold text-xs uppercase text-slate-300 mb-2">1-Click Subscription Cancellation Generator</h3>
                    <p class="text-xs text-slate-400 mb-3">Generate a legally compliant UK statutory cancellation letter:</p>
                    <div class="space-y-3">
                        <input type="text" id="cancel-service" placeholder="Service Name (e.g. Anthropic, Spotify)" class="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-xs text-white">
                        <input type="number" id="cancel-cost" placeholder="Monthly Cost (£)" class="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-xs text-white">
                        <input type="text" id="cancel-ref" placeholder="Account / Email Reference (optional)" class="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-xs text-white">
                        <button onclick="generateCancelLetter()" class="w-full py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded font-semibold text-xs text-white">Generate Cancellation Notice</button>
                    </div>
                    <div id="cancel-letter-output" class="hidden mt-4 p-3 bg-slate-950 rounded border border-slate-800 text-[11px] space-y-2">
                        <div class="flex justify-between items-center">
                            <span class="font-bold text-emerald-400" id="cancel-letter-subject"></span>
                            <button onclick="copyCancelLetter()" class="text-slate-400 hover:text-white">Copy</button>
                        </div>
                        <pre id="cancel-letter-body" class="whitespace-pre-wrap font-sans text-slate-300"></pre>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 6: MARKET SCOUT -->
        <div id="section-scout" class="hidden space-y-6">
            <div class="card">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="font-bold text-sm text-slate-200">Live UK Retail Banking Benchmarks</h3>
                    <span class="text-xs text-slate-500">FSCS Protected & Flexible</span>
                </div>
                <div class="flex space-x-2 border-b border-slate-800 pb-2 mb-4 text-xs font-semibold">
                    <button onclick="switchScoutTab('isas')" id="tab-btn-scout-isas" class="px-3 py-1 bg-slate-800 text-emerald-400 rounded-md">Cash ISAs (Tax-Free)</button>
                    <button onclick="switchScoutTab('taxable')" id="tab-btn-scout-taxable" class="px-3 py-1 text-slate-400 hover:text-slate-200">Taxable Savings (After Tax)</button>
                    <button onclick="switchScoutTab('switches')" id="tab-btn-scout-switches" class="px-3 py-1 text-slate-400 hover:text-slate-200">Bank Switch Bounties</button>
                </div>

                <div id="scout-tab-isas" class="scout-subtab overflow-x-auto">
                    <table class="w-full text-xs text-left">
                        <thead class="text-slate-400 border-b border-slate-800">
                            <tr><th class="pb-2">Provider</th><th class="pb-2">AER Yield</th><th class="pb-2">Type</th><th class="pb-2">Key Terms</th></tr>
                        </thead>
                        <tbody id="tbody-isas" class="divide-y divide-slate-800/60"></tbody>
                    </table>
                </div>

                <div id="scout-tab-taxable" class="scout-subtab hidden overflow-x-auto">
                    <table class="w-full text-xs text-left">
                        <thead class="text-slate-400 border-b border-slate-800">
                            <tr><th class="pb-2">Provider</th><th class="pb-2">Gross AER</th><th class="pb-2">Net (After Your Tax)</th><th class="pb-2">Notes</th></tr>
                        </thead>
                        <tbody id="tbody-taxable" class="divide-y divide-slate-800/60"></tbody>
                    </table>
                </div>

                <div id="scout-tab-switches" class="scout-subtab hidden overflow-x-auto">
                    <table class="w-full text-xs text-left">
                        <thead class="text-slate-400 border-b border-slate-800">
                            <tr><th class="pb-2">Bank</th><th class="pb-2">Bounty</th><th class="pb-2">Required DDs</th><th class="pb-2">Qualification</th></tr>
                        </thead>
                        <tbody id="tbody-switches" class="divide-y divide-slate-800/60"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 7: APP WALKTHROUGH & USER GUIDE -->
        <div id="section-walkthrough" class="hidden space-y-6">
            <!-- Hero Banner -->
            <div class="card bg-gradient-to-br from-slate-900 via-slate-850 to-slate-900 border-slate-700/80">
                <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div>
                        <div class="inline-flex items-center space-x-2 px-2.5 py-1 rounded-full bg-emerald-950 border border-emerald-800 text-emerald-400 text-xs font-semibold mb-2">
                            <span>🛡️ Institutional UK Fiduciary Architecture</span>
                        </div>
                        <h2 class="text-xl font-bold text-white">How This App Works & How to Use It</h2>
                        <p class="text-xs text-slate-300 mt-1.5 max-w-2xl leading-relaxed">
                            Personal Fiduciary Harness is your private, autonomous wealth operating system. Unlike retail apps (Emma, Snoop, Plum) that monetize by selling credit cards and loans, this platform operates under a strict <strong>100% fiduciary standard</strong>: zero kickbacks, zero affiliate fluff, and complete on-device privacy.
                        </p>
                    </div>
                    <div class="flex flex-col sm:flex-row gap-2">
                        <button onclick="openAIModelModal()" class="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold rounded-lg text-slate-200 flex items-center space-x-1.5">
                            <span>⚙️ Switch AI Mode</span>
                        </button>
                        <a href="/architecture" target="_blank" class="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold rounded-lg text-slate-200 flex items-center space-x-1.5 shadow">
                            <span>🏛️ Architecture Diagram</span>
                        </a>
                        <a href="/guide" target="_blank" class="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold rounded-lg text-white flex items-center space-x-1.5 shadow">
                            <span>↗ Full Page Guide</span>
                        </a>
                    </div>
                </div>
            </div>

            <!-- Deep Dive: Local Model Intelligence vs Cloud -->
            <div class="card border-l-4 border-l-purple-500 space-y-4">
                <div class="flex items-center justify-between">
                    <h3 class="font-bold text-sm text-purple-300 flex items-center space-x-2">
                        <span>🧠</span>
                        <span>Is the Local Model Intelligent Enough? (Honest Fiduciary Assessment)</span>
                    </h3>
                    <span class="text-[11px] px-2 py-0.5 rounded bg-purple-950 border border-purple-800 text-purple-300 font-semibold">Model Benchmarks</span>
                </div>
                <div class="text-xs text-slate-300 leading-relaxed space-y-3">
                    <p>
                        <strong>Yes, for 95% of day-to-day wealth management tasks.</strong> On your 16GB Apple Silicon MacBook, running <strong>Meta-Llama-3.1-8B-Instruct</strong> or <strong>Mistral-7B</strong> via LM Studio with full GPU Metal offloading produces answers in <strong>~1.2 seconds</strong> with zero privacy leaks.
                    </p>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                        <div class="p-3 bg-slate-850 rounded-xl border border-slate-800 space-y-2">
                            <div class="font-bold text-emerald-400 text-xs flex items-center space-x-1.5">
                                <span>🟢</span>
                                <span>Where Local Model Excels (100% Private):</span>
                            </div>
                            <ul class="list-disc list-inside space-y-1 text-[11px] text-slate-300">
                                <li><strong>Deterministic Grounding (RAG)</strong>: Our Python backend queries SQLite first, then injects exact balances, burn rates, and active bills directly into the model context.</li>
                                <li><strong>Daily Burn & Runway Math</strong>: Calculating whether you can afford an expense (e.g. £1,500 holiday or £50 dinner) against your 1.5-day liquid buffer.</li>
                                <li><strong>Zero Data Egress</strong>: Financial account numbers and spend habits never touch any external server.</li>
                            </ul>
                        </div>
                        <div class="p-3 bg-slate-850 rounded-xl border border-slate-800 space-y-2">
                            <div class="font-bold text-purple-400 text-xs flex items-center space-x-1.5">
                                <span>🟣</span>
                                <span>When Cloud Gemini is Superior:</span>
                            </div>
                            <ul class="list-disc list-inside space-y-1 text-[11px] text-slate-300">
                                <li><strong>Complex Multi-Year Tax Modeling</strong>: Multi-tier pension annual allowance carry-forward, tapering, and Scottish vs England tax bracket calculations.</li>
                                <li><strong>Enormous Context Windows</strong>: Synthesizing hundreds of raw PDF or CSV statement pages simultaneously (1M+ tokens).</li>
                                <li><strong>Deep Strategic Synthesis</strong>: Crafting multi-page formal fiduciary memorandums.</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Card-by-Card Feature Guide -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <!-- 1. Holdings & Runway -->
                <div class="card space-y-2.5">
                    <div class="text-xl">⏱️</div>
                    <h3 class="font-bold text-xs uppercase tracking-wider text-white">1. Liquid Cash Runway & Burn</h3>
                    <p class="text-xs text-slate-400 leading-relaxed">
                        Measures how many days of living expenses you have before your cash balance hits £0. It divides your verified daily burn (£18.72/day) into your liquid GBP cash.
                    </p>
                    <div class="text-[11px] text-emerald-400 font-medium">
                        💡 Tip: Replaces stress of reactive £100 manual top-ups with an automated 1st-of-the-month float.
                    </div>
                </div>

                <!-- 2. Zero-Hallucination Watchdog -->
                <div class="card space-y-2.5">
                    <div class="text-xl">🚨</div>
                    <h3 class="font-bold text-xs uppercase tracking-wider text-white">2. Financial Watchdog</h3>
                    <p class="text-xs text-slate-400 leading-relaxed">
                        Eliminates false alarms. Uses strict 45-day recency and regex word boundaries so one-off pub visits or groceries are never forecasted as upcoming bills. Tracks stealth price hikes and double charges.
                    </p>
                    <div class="text-[11px] text-emerald-400 font-medium">
                        💡 Tip: View the "Archived / Inactive" section to see past cancelled contracts without clutter.
                    </div>
                </div>

                <!-- 3. Whole Net Worth -->
                <div class="card space-y-2.5">
                    <div class="text-xl">💰</div>
                    <h3 class="font-bold text-xs uppercase tracking-wider text-white">3. Whole Net Worth</h3>
                    <p class="text-xs text-slate-400 leading-relaxed">
                        Complete balance sheet beyond current accounts. Click <strong>"+ Add Custom Asset"</strong> to log Cash ISAs, Stocks & Shares ISAs, Workplace Pensions, SIPPs, Property Equity, or Crypto.
                    </p>
                    <div class="text-[11px] text-emerald-400 font-medium">
                        💡 Tip: Updates the allocation doughnut chart and tracks total net worth over time.
                    </div>
                </div>

                <!-- 4. UK Tax Engine -->
                <div class="card space-y-2.5">
                    <div class="text-xl">🇬🇧</div>
                    <h3 class="font-bold text-xs uppercase tracking-wider text-white">4. UK Tax Optimization</h3>
                    <p class="text-xs text-slate-400 leading-relaxed">
                        Audits your exposure to the infamous <strong>60% marginal tax trap</strong> (£100k–£125,140 personal allowance taper). Calculates the exact pension sacrifice needed to restore your tax-free allowance.
                    </p>
                    <div class="text-[11px] text-emerald-400 font-medium">
                        💡 Tip: Also checks if savings interest exceeds your Personal Savings Allowance (£1,000 or £500).
                    </div>
                </div>

                <!-- 5. Smart Sweeper & Cancellations -->
                <div class="card space-y-2.5">
                    <div class="text-xl">⚡</div>
                    <h3 class="font-bold text-xs uppercase tracking-wider text-white">5. Sweeper & 1-Click Cancel</h3>
                    <p class="text-xs text-slate-400 leading-relaxed">
                        Identifies excess idle cash in 0% accounts and generates an automated monthly operating float plan. Includes a statutory UK Consumer Rights Act subscription cancellation notice generator.
                    </p>
                    <div class="text-[11px] text-emerald-400 font-medium">
                        💡 Tip: Type a service name like "Anthropic" to generate an immediate legal cancellation letter.
                    </div>
                </div>

                <!-- 6. Market Scout -->
                <div class="card space-y-2.5">
                    <div class="text-xl">🌐</div>
                    <h3 class="font-bold text-xs uppercase tracking-wider text-white">6. Live Market Scout</h3>
                    <p class="text-xs text-slate-400 leading-relaxed">
                        Real-time FSCS-protected market rates: Trading 212 Flexible Cash ISA (4.87% tax-free), Chase UK 1% debit cashback (+£67/yr on everyday spend), and verified bank switch bounties (+£175 to +£200).
                    </p>
                    <div class="text-[11px] text-emerald-400 font-medium">
                        💡 Tip: Shows effective yields *after* your personal income tax bracket.
                    </div>
                </div>
            </div>

            <!-- Nagging Issues Resolved Section -->
            <div class="card border border-slate-700/80 space-y-3">
                <h3 class="font-bold text-xs uppercase tracking-wider text-slate-300 flex items-center space-x-2">
                    <span>🔧</span>
                    <span>Nagging Features & Bug Fixes Delivered</span>
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-slate-300">
                    <div class="p-3 bg-slate-850 rounded-lg space-y-1">
                        <div class="font-semibold text-emerald-400">✓ No More Hallucinated Bills</div>
                        <p class="text-[11px] text-slate-400">Discretionary card spending (pubs, Deliveroo, groceries) previously rolled forward infinitely. Guarded by strict 45-day recency and regex word boundaries.</p>
                    </div>
                    <div class="p-3 bg-slate-850 rounded-lg space-y-1">
                        <div class="font-semibold text-emerald-400">✓ 100% Local On-Device AI</div>
                        <p class="text-[11px] text-slate-400">No confidential finances are sent over third-party APIs when running LM Studio on Apple Silicon GPU Metal.</p>
                    </div>
                    <div class="p-3 bg-slate-850 rounded-lg space-y-1">
                        <div class="font-semibold text-emerald-400">✓ Native macOS Application</div>
                        <p class="text-[11px] text-slate-400">Installed in <code>/Applications/Fiduciary.app</code> with retina shield icon, indexed in Spotlight, and launchable in 1 click.</p>
                    </div>
                    <div class="p-3 bg-slate-850 rounded-lg space-y-1">
                        <div class="font-semibold text-emerald-400">✓ Live Model Provenance in Chat</div>
                        <p class="text-[11px] text-slate-400">Every Copilot response displays a badge certifying whether it was generated locally or via cloud.</p>
                    </div>
                </div>
            </div>
        </div>

    </main>

    <!-- FLOATING INTERACTIVE AI COPILOT DRAWER -->
    <div id="copilot-drawer" class="fixed bottom-6 right-6 w-96 max-w-[calc(100vw-3rem)] h-[520px] bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col z-50 overflow-hidden transition-all duration-300 transform translate-y-0">
        <!-- Copilot Header -->
        <div class="px-4 py-3 bg-slate-850 border-b border-slate-800 flex items-center justify-between">
            <div class="flex items-center space-x-2">
                <span class="text-lg">🤖</span>
                <div>
                    <h3 class="font-bold text-xs text-white leading-tight">Fiduciary AI Copilot</h3>
                    <p class="text-[10px] text-emerald-400" id="copilot-subhead-status">Grounded in Live Accounts & Taxes</p>
                </div>
            </div>
            <div class="flex items-center space-x-2">
                <button onclick="clearChat()" title="Clear chat" class="text-slate-400 hover:text-slate-200 text-xs">🗑️</button>
                <button onclick="toggleCopilot()" class="text-slate-400 hover:text-white text-sm font-bold">✕</button>
            </div>
        </div>

        <!-- Chat Messages Container -->
        <div id="copilot-messages" class="flex-1 p-3 overflow-y-auto space-y-3 text-xs">
            <div class="p-2.5 bg-slate-800/70 rounded-xl text-slate-300">
                👋 Hello! I am your unconflicted UK Fiduciary Copilot. I analyze your live transactions, runway, upcoming bills, and tax bracket. Ask me anything!
            </div>
        </div>

        <!-- Quick Prompt Chips -->
        <div class="px-3 py-1.5 bg-slate-950/80 border-t border-slate-800 flex space-x-1.5 overflow-x-auto text-[10px] whitespace-nowrap">
            <button onclick="sendQuickPrompt('How much did I spend on pubs?')" class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-amber-300 rounded-full">🍺 Pub Spend</button>
            <button onclick="sendQuickPrompt('Show my last 10 transactions')" class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded-full">💳 Last 10 Txs</button>
            <button onclick="sendQuickPrompt('What is my financial health score and what should I do?')" class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-emerald-300 rounded-full">🧬 Health Score &amp; DNA</button>
            <button onclick="sendQuickPrompt('Can I afford a £1,500 holiday?')" class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-full">Afford £1.5k holiday?</button>
            <button onclick="sendQuickPrompt('What bills are due in the next 14 days?')" class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-full">Bills in 14 days</button>
            <button onclick="sendQuickPrompt('Explain my 60% tax trap risk')" class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-full">60% Tax Trap</button>
        </div>

        <!-- Input Bar -->
        <form id="copilot-form" class="p-2.5 bg-slate-850 border-t border-slate-800 flex items-center space-x-2">
            <input type="text" id="copilot-input" placeholder="Ask your fiduciary..." class="flex-1 px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-xl text-xs text-white focus:outline-none focus:border-purple-500">
            <button type="submit" id="copilot-send-btn" class="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-semibold">Send</button>
        </form>
    </div>

    <!-- AI MODEL SELECTOR MODAL -->
    <div id="ai-model-modal" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center hidden">
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-md shadow-2xl space-y-4">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                <div class="flex items-center space-x-2">
                    <span class="text-xl">⚙️</span>
                    <div>
                        <h3 class="font-bold text-sm text-white">AI Engine & Privacy Selector</h3>
                        <p class="text-[11px] text-slate-400">Choose between local on-device privacy or cloud reasoning</p>
                    </div>
                </div>
                <button onclick="closeAIModelModal()" class="text-slate-400 hover:text-white">✕</button>
            </div>

            <div class="space-y-3 text-xs">
                <!-- Option 1: Local Ollama / LM Studio -->
                <div onclick="selectAIProvider('local')" id="opt-provider-local" class="p-3.5 rounded-xl border border-slate-700 bg-slate-850 hover:border-emerald-500 cursor-pointer transition flex items-start space-x-3">
                    <span class="text-2xl mt-0.5">🟢</span>
                    <div class="flex-1">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-slate-100">100% Local (Ollama / LM Studio)</span>
                            <span class="px-2 py-0.5 rounded text-[10px] bg-emerald-950 border border-emerald-800 text-emerald-300 font-semibold">100% Private</span>
                        </div>
                        <p class="text-[11px] text-slate-400 mt-1">Runs directly on your MacBook GPU (Metal) using Ollama (qwen3.5:4b) or LM Studio (Llama 3.1). <strong>Zero confidential banking or transaction data leaves your laptop.</strong> Fast sub-second latency.</p>
                    </div>
                </div>

                <!-- Option 2: Cloud Gemini -->
                <div onclick="selectAIProvider('gemini')" id="opt-provider-gemini" class="p-3.5 rounded-xl border border-slate-700 bg-slate-850 hover:border-purple-500 cursor-pointer transition flex items-start space-x-3">
                    <span class="text-2xl mt-0.5">🟣</span>
                    <div class="flex-1">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-slate-100">Google Gemini 2.0 Cloud</span>
                            <span class="px-2 py-0.5 rounded text-[10px] bg-purple-950 border border-purple-800 text-purple-300 font-semibold">Cloud API</span>
                        </div>
                        <p class="text-[11px] text-slate-400 mt-1">Deep institutional reasoning with 1M+ context window. Best for complex multi-year UK tax planning and retirement modeling.</p>
                    </div>
                </div>

                <!-- Option 3: Auto Hybrid -->
                <div onclick="selectAIProvider('auto')" id="opt-provider-auto" class="p-3.5 rounded-xl border border-slate-700 bg-slate-850 hover:border-cyan-500 cursor-pointer transition flex items-start space-x-3">
                    <span class="text-2xl mt-0.5">⚡</span>
                    <div class="flex-1">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-slate-100">Auto Hybrid (Default)</span>
                            <span class="px-2 py-0.5 rounded text-[10px] bg-cyan-950 border border-cyan-800 text-cyan-300 font-semibold">Adaptive</span>
                        </div>
                        <p class="text-[11px] text-slate-400 mt-1">Uses Local LM Studio whenever it is running. If LM Studio is stopped, automatically falls back to Gemini Cloud.</p>
                    </div>
                </div>

                <!-- Option 4: AI Gateway / LiteLLM Proxy -->
                <div onclick="selectAIProvider('gateway')" id="opt-provider-gateway" class="p-3.5 rounded-xl border border-slate-700 bg-slate-850 hover:border-blue-500 cursor-pointer transition flex items-start space-x-3">
                    <span class="text-2xl mt-0.5">🔵</span>
                    <div class="flex-1">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-slate-100">AI Gateway (LiteLLM / Proxy)</span>
                            <span class="px-2 py-0.5 rounded text-[10px] bg-blue-950 border border-blue-800 text-blue-300 font-semibold">Router / Proxy</span>
                        </div>
                        <p class="text-[11px] text-slate-400 mt-1">Routes via an OpenAI-compatible intelligent proxy or enterprise gateway (LiteLLM, Portkey, Cloudflare) with centralized rate-limiting, failovers, and caching.</p>
                    </div>
                </div>
            </div>

            <div class="pt-2 border-t border-slate-800 flex justify-end">
                <button onclick="closeAIModelModal()" class="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold rounded-lg text-white">Close</button>
            </div>
        </div>
    </div>

    <!-- ADD ASSET MODAL -->
    <div id="add-asset-modal" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center hidden">
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <div class="flex items-center justify-between mb-4">
                <h3 class="font-bold text-sm text-white">Add Custom Asset or Debt</h3>
                <button onclick="closeAddAssetModal()" class="text-slate-400 hover:text-white">✕</button>
            </div>
            <form id="add-asset-form" class="space-y-3.5 text-xs">
                <div>
                    <label class="block text-slate-400 mb-1">Asset Name</label>
                    <input type="text" id="asset-name" required placeholder="e.g. London Flat Equity or Vanguard ISA" class="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-white">
                </div>
                <div>
                    <label class="block text-slate-400 mb-1">Asset Class</label>
                    <select id="asset-class" class="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-white">
                        <option value="property">Property / Real Estate</option>
                        <option value="investment">Investment / Stocks & Shares ISA</option>
                        <option value="pension">Pension / SIPP</option>
                        <option value="liability">Liability / Mortgage / Debt</option>
                        <option value="cash">Cash / Offline Account</option>
                    </select>
                </div>
                <div>
                    <label class="block text-slate-400 mb-1">Current Value / Balance (£)</label>
                    <input type="number" id="asset-balance" step="0.01" required placeholder="e.g. 250000" class="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-white">
                </div>
                <div>
                    <label class="block text-slate-400 mb-1">Notes (Optional)</label>
                    <input type="text" id="asset-notes" placeholder="e.g. 5-year fixed at 4.2%" class="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-white">
                </div>
                <div class="flex justify-end space-x-2 pt-2">
                    <button type="button" onclick="closeAddAssetModal()" class="px-3 py-1.5 bg-slate-800 rounded-lg text-slate-300">Cancel</button>
                    <button type="submit" class="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 font-semibold text-white rounded-lg">Save Asset</button>
                </div>
            </form>
        </div>
    </div>

    <!-- AI TRACES & OBSERVABILITY MODAL -->
    <div id="ai-traces-modal" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center hidden p-4">
        <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] shadow-2xl flex flex-col">
            <div class="p-5 border-b border-slate-800 flex items-center justify-between">
                <div class="flex items-center space-x-2.5">
                    <span class="text-xl">⚖️</span>
                    <div>
                        <h3 class="font-bold text-sm text-white">AI Agent Observability, Traces & LLM Judge Reports</h3>
                        <p class="text-[11px] text-slate-400">Inspect exact prompts, latencies, model invocations, grounding audits, and independent LLM-as-a-Judge evaluations</p>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <button onclick="toggleToolsCatalogUI()" class="px-2.5 py-1 bg-cyan-950/70 hover:bg-cyan-900 border border-cyan-800 text-cyan-300 text-xs rounded-lg transition font-medium flex items-center gap-1" title="Inspect available deterministic and live web tools">
                        <span>🛠️ Tools Catalog</span>
                    </button>
                    <button id="btn-judge-latest" onclick="evaluateLatestJudgeUI()" class="px-2.5 py-1 bg-fuchsia-950/70 hover:bg-fuchsia-900 border border-fuchsia-800 text-fuchsia-300 text-xs rounded-lg transition font-medium flex items-center gap-1" title="Audit the latest AI response using independent local Ollama judge model">
                        <span>⚖️ Judge Latest</span>
                    </button>
                    <button onclick="clearTracesUI()" class="px-2.5 py-1 bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 text-xs rounded-lg transition font-medium">Clear Traces</button>
                    <button onclick="closeTracesModal()" class="text-slate-400 hover:text-white px-2 py-1">✕</button>
                </div>
            </div>

            <!-- Tools catalog drawer -->
            <div id="tools-catalog-panel" class="hidden p-4 bg-slate-950/95 border-b border-slate-800 text-xs space-y-2.5">
                <div class="flex items-center justify-between">
                    <h4 class="font-bold text-cyan-300 text-xs uppercase tracking-wider flex items-center gap-1.5">
                        <span>🛠️</span>
                        <span>Available Deterministic & Live Web Tools</span>
                    </h4>
                    <span class="text-[10px] text-slate-400">Zero-browser HTTP (&lt;250ms), zero cloud egress, 100% on-device</span>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                    <div class="p-2.5 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                        <div class="flex items-center justify-between">
                            <span class="font-mono font-bold text-cyan-400 text-[11px]">fetch_boe_base_rate</span>
                            <span class="px-1.5 py-0.5 rounded text-[9px] bg-cyan-950 text-cyan-300 border border-cyan-800 font-mono">Scraper HTTP</span>
                        </div>
                        <p class="text-[10px] text-slate-400 leading-tight">Scrapes official BoE base rate (3.75%) directly from bankofengland.co.uk in &lt;200ms.</p>
                        <div class="text-[9px] text-slate-500 font-mono truncate">bankofengland.co.uk</div>
                    </div>
                    <div class="p-2.5 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                        <div class="flex items-center justify-between">
                            <span class="font-mono font-bold text-emerald-400 text-[11px]">fetch_top_savings_and_isas</span>
                            <span class="px-1.5 py-0.5 rounded text-[9px] bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono">Market Feed</span>
                        </div>
                        <p class="text-[10px] text-slate-400 leading-tight">Live UK benchmarks: Trading 212 Cash ISA (4.87%), First Direct Regular Saver (7.00%), Nationwide (£175).</p>
                        <div class="text-[9px] text-slate-500 font-mono">Retail Benchmarks</div>
                    </div>
                    <div class="p-2.5 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                        <div class="flex items-center justify-between">
                            <span class="font-mono font-bold text-amber-400 text-[11px]">query_local_transactions</span>
                            <span class="px-1.5 py-0.5 rounded text-[9px] bg-amber-950 text-amber-300 border border-amber-800 font-mono">SQLite DB</span>
                        </div>
                        <p class="text-[10px] text-slate-400 leading-tight">Deterministic queries on local transactions from Revolut, Wise, etc., in &lt;2ms.</p>
                        <div class="text-[9px] text-slate-500 font-mono">data/financial.db</div>
                    </div>
                </div>
            </div>

            <!-- Metrics bar -->
            <div class="px-5 py-3 bg-slate-950 border-b border-slate-800 grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
                <div>
                    <span class="text-[10px] text-slate-400 uppercase font-semibold">Total Invocations</span>
                    <div id="trace-metric-total" class="font-bold text-sm text-white">0</div>
                </div>
                <div>
                    <span class="text-[10px] text-slate-400 uppercase font-semibold">Average Latency</span>
                    <div id="trace-metric-latency" class="font-bold text-sm text-cyan-400">0 ms</div>
                </div>
                <div>
                    <span class="text-[10px] text-slate-400 uppercase font-semibold">Grounding Pass Rate</span>
                    <div id="trace-metric-grounding" class="font-bold text-sm text-emerald-400">100%</div>
                </div>
                <div>
                    <span class="text-[10px] text-slate-400 uppercase font-semibold">Local Privacy Share</span>
                    <div id="trace-metric-local" class="font-bold text-sm text-purple-400">100%</div>
                </div>
                <div>
                    <span class="text-[10px] text-slate-400 uppercase font-semibold">Judge Pass Rate</span>
                    <div id="trace-metric-judge" class="font-bold text-sm text-fuchsia-400">100%</div>
                </div>
            </div>

            <!-- Trace list -->
            <div id="traces-list-container" class="p-5 overflow-y-auto space-y-3 flex-1 text-xs">
                <div class="text-center py-8 text-slate-500">Loading traces...</div>
            </div>

            <div class="p-4 border-t border-slate-800 flex justify-between items-center text-xs text-slate-400">
                <span class="text-[11px]">Audit Engine: Checks every currency citation (£) against deterministic context.</span>
                <button onclick="closeTracesModal()" class="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold rounded-lg text-white">Close</button>
            </div>
        </div>
    </div>

    <script>
        let currentData = null;
        let selectedActions = new Set();
        let netWorthChart = null;

        async function fetchAllState() {
            try {
                const res = await fetch('/api/state');
                currentData = await res.json();
                renderUI();
                await Promise.all([
                    loadLLMStatus(),
                    loadNetWorth(),
                    loadTransactionsFeed(),
                    loadWatchdog(),
                    loadCreditAudit(),
                    loadTaxAudit(),
                    loadSweeper(),
                    loadChatHistory()
                ]);
            } catch (err) {
                console.error("Failed to fetch state:", err);
            }
        }

        function renderUI() {
            if (!currentData) return;
            const { state, profile, scout, recommendations } = currentData;
            const txSummary = profile.transaction_30d_summary || {};

            const runway = profile.liquid_runway_days || 1.5;
            document.getElementById('stat-runway').innerText = `${runway.toFixed(1)} Days`;
            document.getElementById('stat-daily-burn').innerText = `Burn: £${profile.daily_burn_rate.toFixed(2)}/day`;

            const runwayCard = document.getElementById('card-runway');
            if (runway < 7.0) {
                runwayCard.className = "card border-l-4 border-l-rose-500 bg-rose-950/10";
            } else {
                runwayCard.className = "card border-l-4 border-l-amber-500";
            }

            document.getElementById('stat-card-drag').innerText = `+£${profile.annual_cashback_potential.toFixed(2)} / yr`;
            document.getElementById('stat-card-spend').innerText = `1% cashback on £${(txSummary.card_spend_total || 0).toFixed(2)}/mo`;

            // Accounts List
            const accsList = document.getElementById('accounts-list');
            if (state.accounts_detail.length === 0) {
                accsList.innerHTML = `<div class="text-center py-4 text-slate-500 text-xs">No accounts loaded.</div>`;
            } else {
                accsList.innerHTML = state.accounts_detail.map(acc => `
                    <div class="flex items-center justify-between p-2.5 bg-slate-850 border border-slate-800 rounded-lg">
                        <div class="flex items-center space-x-2.5">
                            <span class="w-2 h-2 rounded-full ${acc.current_balance > 0 ? 'bg-emerald-400' : 'bg-slate-600'}"></span>
                            <div>
                                <div class="text-xs font-semibold text-slate-200">${acc.name}</div>
                                <div class="text-[10px] text-slate-500 uppercase">${acc.institution_name} • ${acc.account_type}</div>
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="text-xs font-bold text-white">£${acc.current_balance.toLocaleString('en-GB', {minimumFractionDigits: 2})}</div>
                        </div>
                    </div>
                `).join('');
            }

            // Spending Categories
            const cats = txSummary.categories || {};
            const catsList = document.getElementById('spending-categories-list');
            document.getElementById('stat-30d-total').innerText = `Total: £${(txSummary.living_spend_total || 0).toLocaleString('en-GB', {minimumFractionDigits: 2})}`;

            if (Object.keys(cats).length === 0) {
                catsList.innerHTML = `<div class="text-center py-3 text-slate-500 text-xs">No spending recorded.</div>`;
            } else {
                catsList.innerHTML = Object.entries(cats).map(([name, data]) => `
                    <div class="space-y-1">
                        <div class="flex justify-between text-xs">
                            <span class="text-slate-300 font-medium">${name}</span>
                            <span class="text-slate-200 font-bold">£${data.total.toLocaleString('en-GB', {minimumFractionDigits: 2})} <span class="text-[10px] text-slate-500 font-normal">(${data.pct_of_outflow}%)</span></span>
                        </div>
                        <div class="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                            <div class="bg-emerald-500 h-1.5 rounded-full" style="width: ${Math.min(100, data.pct_of_outflow)}%"></div>
                        </div>
                    </div>
                `).join('');
            }

            // Top Merchants
            const merchants = txSummary.top_merchants || [];
            const merchList = document.getElementById('top-merchants-list');
            if (merchants.length === 0) {
                merchList.innerHTML = `<div class="text-center py-3 text-slate-500 text-xs">No merchants recorded.</div>`;
            } else {
                merchList.innerHTML = merchants.slice(0, 5).map(m => `
                    <div class="flex items-center justify-between p-2 bg-slate-850 rounded border border-slate-800/80 text-xs">
                        <div>
                            <div class="font-semibold text-slate-200">${m.name}</div>
                            <div class="text-[10px] text-slate-500">${m.count} visits • ${m.category}</div>
                        </div>
                        <div class="font-bold text-white">£${m.total.toFixed(2)}</div>
                    </div>
                `).join('');
            }

            // Action Cards
            const actionsContainer = document.getElementById('action-cards');
            actionsContainer.innerHTML = recommendations.map((rec, idx) => {
                const isSelected = selectedActions.has(idx);
                return `
                    <div class="p-3.5 rounded-xl border transition cursor-pointer ${isSelected ? 'bg-emerald-950/30 border-emerald-600' : 'bg-slate-850 border-slate-800 hover:border-slate-700'}" onclick="toggleAction(${idx})">
                        <div class="flex items-start justify-between">
                            <div class="flex items-start space-x-2.5">
                                <input type="checkbox" ${isSelected ? 'checked' : ''} class="mt-0.5 rounded border-slate-700 bg-slate-800 text-emerald-500 focus:ring-0">
                                <div>
                                    <div class="text-xs font-bold text-slate-100">[${rec.category}] ${rec.title}</div>
                                    <p class="text-xs text-slate-400 mt-1">${rec.summary}</p>
                                </div>
                            </div>
                            <div class="text-right whitespace-nowrap ml-3">
                                <span class="text-xs font-bold ${rec.annual_gain_gbp > 0 ? 'text-emerald-400' : 'text-slate-400'}">
                                    ${rec.annual_gain_gbp > 0 ? '+£' + rec.annual_gain_gbp.toLocaleString('en-GB', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '/yr' : 'Risk Shield'}
                                </span>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            updateGainTotal();
            renderScoutTables(scout);
        }

        function toggleAction(idx) {
            if (selectedActions.has(idx)) selectedActions.delete(idx);
            else selectedActions.add(idx);
            renderUI();
        }

        function updateGainTotal() {
            if (!currentData) return;
            let sum = 0;
            selectedActions.forEach(idx => {
                const rec = currentData.recommendations[idx];
                if (rec && rec.annual_gain_gbp) sum += rec.annual_gain_gbp;
            });
            document.getElementById('total-projected-gain').innerText = `+£${sum.toLocaleString('en-GB', {minimumFractionDigits: 2})}/yr`;
        }

        async function loadNetWorth() {
            try {
                const res = await fetch('/api/networth');
                const data = await res.json();
                document.getElementById('stat-net-worth').innerText = `£${data.net_worth.toLocaleString('en-GB', {minimumFractionDigits: 2})}`;
                document.getElementById('stat-net-worth-sub').innerText = `Liquid: £${data.liquid_net_worth.toLocaleString('en-GB', {minimumFractionDigits: 2})}`;

                // Render Chart
                const ctx = document.getElementById('netWorthChart').getContext('2d');
                const b = data.breakdown;
                if (netWorthChart) netWorthChart.destroy();
                netWorthChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Cash', 'Investments', 'Pensions', 'Property', 'Debt'],
                        datasets: [{
                            data: [b.cash, b.investment, b.pension, b.property, b.liability],
                            backgroundColor: ['#10b981', '#3b82f6', '#8b5cf6', '#06b6d4', '#f43f5e'],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 10 } } }
                        }
                    }
                });

                // Render Tables
                const tablesContainer = document.getElementById('networth-tables');
                tablesContainer.innerHTML = Object.entries(data.accounts_by_class).map(([cls, accs]) => `
                    <div class="border border-slate-800 rounded-lg p-3 bg-slate-850">
                        <div class="flex justify-between items-center mb-2">
                            <span class="font-bold text-xs uppercase text-slate-300">${cls}</span>
                            <span class="font-bold text-xs ${cls === 'liability' ? 'text-rose-400' : 'text-emerald-400'}">
                                ${cls === 'liability' ? '-£' : '£'}${data.breakdown[cls].toLocaleString('en-GB', {minimumFractionDigits: 2})}
                            </span>
                        </div>
                        ${accs.length === 0 ? '<div class="text-[11px] text-slate-500">None added yet.</div>' : `
                            <div class="space-y-1">
                                ${accs.map(a => `
                                    <div class="flex justify-between items-center text-[11px] text-slate-400">
                                        <span>${a.name}</span>
                                        <div class="flex items-center space-x-2">
                                            <span class="font-semibold text-slate-200">£${a.current_balance.toLocaleString('en-GB', {minimumFractionDigits: 2})}</span>
                                            ${(a.id.startsWith('asset_') || a.id.startsWith('acc_') || a.id.includes('statement') || a.id.includes('imported')) ? `<button onclick="deleteAsset('${a.id}')" title="Remove account" class="text-rose-400 hover:text-rose-300 text-[10px] px-1 hover:bg-rose-950/40 rounded transition">✕</button>` : ''}
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        `}
                    </div>
                `).join('');

            } catch (err) {
                console.error("Net worth load error:", err);
            }
        }

        async function loadWatchdog() {
            try {
                const res = await fetch('/api/watchdog');
                const data = await res.json();

                const bills14 = data.upcoming_bills_14d || [];
                const sum14 = bills14.reduce((acc, b) => acc + b.expected_amount, 0);
                document.getElementById('stat-upcoming-bills').innerText = `£${sum14.toLocaleString('en-GB', {minimumFractionDigits: 2})}`;
                document.getElementById('stat-bills-count').innerText = `${bills14.length} bills in next 14 days`;
                document.getElementById('stat-upcoming-14d-total').innerText = `£${sum14.toLocaleString('en-GB', {minimumFractionDigits: 2})}`;

                // Liquidity Shortfall Banner
                const sf = data.liquidity_shortfall_alert;
                const sfBox = document.getElementById('watchdog-shortfall-box');
                if (sf) {
                    sfBox.className = sf.level === 'CRITICAL' ? "p-4 rounded-xl border border-rose-500/50 bg-rose-950/20 text-rose-300 text-xs" : "p-4 rounded-xl border border-amber-500/50 bg-amber-950/20 text-amber-300 text-xs";
                    sfBox.innerHTML = `<strong>⚠️ ${sf.title}:</strong> ${sf.message}`;
                    sfBox.classList.remove('hidden');
                    document.getElementById('badge-watchdog-alert').classList.remove('hidden');
                } else {
                    sfBox.classList.add('hidden');
                }

                // Price Hikes
                const hikes = data.price_hike_alerts || [];
                document.getElementById('badge-price-hikes-count').innerText = `${hikes.length} alerts`;
                document.getElementById('price-hikes-list').innerHTML = hikes.length === 0 ? '<div class="text-slate-500 text-xs py-2">No price hikes detected.</div>' : hikes.map(h => `
                    <div class="p-2.5 rounded bg-rose-950/20 border border-rose-900/40 text-xs flex justify-between items-center">
                        <div>
                            <div class="font-bold text-rose-300">${h.merchant}</div>
                            <div class="text-[10px] text-slate-400">Jumped from £${h.previous_amount.toFixed(2)} to £${h.latest_amount.toFixed(2)} on ${h.date_detected}</div>
                        </div>
                        <div class="font-bold text-rose-400">+£${h.increase_amount.toFixed(2)} (+${h.percentage_increase}%)</div>
                    </div>
                `).join('');

                // Duplicates
                const dups = data.duplicate_charge_alerts || [];
                document.getElementById('badge-duplicates-count').innerText = `${dups.length} alerts`;
                document.getElementById('duplicate-charges-list').innerHTML = dups.length === 0 ? '<div class="text-slate-500 text-xs py-2">No duplicate charges detected.</div>' : dups.map(d => `
                    <div class="p-2 bg-amber-950/20 border border-amber-900/40 rounded text-xs flex justify-between">
                        <div>
                            <div class="font-bold text-amber-300">${d.merchant}</div>
                            <div class="text-[10px] text-slate-400">Charged twice: ${d.date_1} & ${d.date_2}</div>
                        </div>
                        <div class="font-bold text-amber-400">£${d.amount.toFixed(2)}</div>
                    </div>
                `).join('');

                // Upcoming Bills List
                document.getElementById('upcoming-bills-list').innerHTML = bills14.length === 0 ? '<div class="text-slate-500 text-xs py-2">No bills due in next 14 days.</div>' : bills14.map(b => `
                    <div class="p-2.5 bg-slate-850 rounded border border-slate-800 flex justify-between items-center text-xs">
                        <div>
                            <div class="font-semibold text-slate-200">${b.merchant}</div>
                            <div class="text-[10px] text-slate-500">Due: ${b.next_due_date} (${b.days_away} days away) • ${b.category}</div>
                        </div>
                        <div class="font-bold text-emerald-400">£${b.expected_amount.toFixed(2)}</div>
                    </div>
                `).join('');

                // Active Recurring Contracts
                const activeBills = data.active_recurring_bills || [];
                const activeCountEl = document.getElementById('badge-active-contracts-count');
                if (activeCountEl) activeCountEl.innerText = `${activeBills.length} active`;
                const activeListEl = document.getElementById('active-contracts-list');
                if (activeListEl) {
                    activeListEl.innerHTML = activeBills.length === 0 ? '<div class="text-slate-500 text-xs py-2">No active recurring contracts detected.</div>' : activeBills.map(b => `
                        <div class="p-2.5 bg-slate-850 rounded-lg border border-slate-800 flex justify-between items-center text-xs">
                            <div>
                                <div class="font-semibold text-slate-200">${b.merchant}</div>
                                <div class="text-[10px] text-slate-400">Last paid: ${b.last_date} • Next: ${b.next_due_date} (${b.frequency}) • ${b.category}</div>
                            </div>
                            <div class="text-right">
                                <div class="font-bold text-emerald-400">£${b.expected_amount.toFixed(2)}</div>
                                <span class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-300">Active</span>
                            </div>
                        </div>
                    `).join('');
                }

                // Inactive Historical Bills
                const inactiveBills = data.inactive_historical_bills || [];
                const inactiveCountEl = document.getElementById('badge-inactive-contracts-count');
                if (inactiveCountEl) inactiveCountEl.innerText = `${inactiveBills.length} archived ▼`;
                const inactiveListEl = document.getElementById('inactive-contracts-list');
                if (inactiveListEl) {
                    inactiveListEl.innerHTML = inactiveBills.length === 0 ? '<div class="text-slate-500 text-xs py-2">No dormant subscriptions.</div>' : inactiveBills.map(b => `
                        <div class="p-2 bg-slate-900/80 rounded border border-slate-800/60 flex justify-between items-center text-xs opacity-75">
                            <div>
                                <div class="font-medium text-slate-300">${b.merchant}</div>
                                <div class="text-[10px] text-slate-500">Last paid: ${b.last_date} (${b.days_dormant} days ago) • ${b.category}</div>
                            </div>
                            <div class="text-right">
                                <div class="text-slate-400 font-medium">£${b.expected_amount.toFixed(2)}</div>
                                <span class="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">Dormant</span>
                            </div>
                        </div>
                    `).join('');
                }

            } catch (err) {
                console.error("Watchdog error:", err);
            }
        }

        async function loadLLMStatus() {
            try {
                const res = await fetch('/api/llm/status');
                const data = await res.json();
                const pill = document.getElementById('llm-status-pill');
                const text = document.getElementById('llm-status-text');
                const dot = document.getElementById('llm-status-dot');
                const subhead = document.getElementById('copilot-subhead-status');

                if (data.mode === 'gateway') {
                    const gwModel = data.gateway_model || 'LiteLLM Proxy';
                    if (text) text.innerHTML = `<strong>AI Gateway</strong> <span class="text-blue-400 font-semibold">(${gwModel})</span>`;
                    if (dot) dot.className = "w-2 h-2 rounded-full bg-blue-400 shadow-sm shadow-blue-400 animate-pulse";
                    if (pill) pill.className = "hidden md:flex items-center space-x-2 px-3 py-1 bg-blue-950/40 border border-blue-700/60 rounded-full text-xs font-medium cursor-pointer hover:border-blue-500 transition";
                    if (subhead) subhead.innerHTML = `🔵 AI Gateway (${gwModel}) • Enterprise Router`;
                } else if (data.mode === 'local') {
                    const localProvName = data.local_provider === 'ollama' ? 'Local Ollama' : 'Local LM Studio';
                    if (text) text.innerHTML = `<strong>${localProvName}</strong> <span class="text-emerald-400 font-semibold">(100% Private)</span>`;
                    if (dot) dot.className = "w-2 h-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400 animate-pulse";
                    if (pill) pill.className = "hidden md:flex items-center space-x-2 px-3 py-1 bg-emerald-950/40 border border-emerald-700/60 rounded-full text-xs font-medium cursor-pointer hover:border-emerald-500 transition";
                    if (subhead) subhead.innerHTML = `🟢 ${localProvName} (${data.local_model || 'Model'}) • 100% On-Device Privacy`;
                } else if (data.mode === 'gemini') {
                    if (text) text.innerHTML = `<strong>Google Gemini</strong> <span class="text-purple-400 font-semibold">(Cloud API)</span>`;
                    if (dot) dot.className = "w-2 h-2 rounded-full bg-purple-400 shadow-sm shadow-purple-400 animate-pulse";
                    if (pill) pill.className = "hidden md:flex items-center space-x-2 px-3 py-1 bg-purple-950/40 border border-purple-700/60 rounded-full text-xs font-medium cursor-pointer hover:border-purple-500 transition";
                    if (subhead) subhead.innerHTML = `🟣 Google Gemini Cloud API`;
                } else {
                    if (text) text.innerHTML = `<span class="text-slate-400">Offline (Start Ollama / Gateway)</span>`;
                    if (dot) dot.className = "w-2 h-2 rounded-full bg-slate-500";
                    if (pill) pill.className = "hidden md:flex items-center space-x-2 px-3 py-1 bg-slate-800 border border-slate-700 rounded-full text-xs font-medium cursor-pointer";
                    if (subhead) subhead.innerHTML = `⚠️ No AI Model Connected`;
                }

                ['local', 'gemini', 'auto', 'gateway'].forEach(p => {
                    const el = document.getElementById(`opt-provider-${p}`);
                    if (el) {
                        if (data.configured_provider === p) {
                            el.className = "p-3.5 rounded-xl border-2 border-emerald-500 bg-slate-800 shadow-md cursor-pointer transition flex items-start space-x-3";
                        } else {
                            el.className = "p-3.5 rounded-xl border border-slate-700 bg-slate-850 hover:border-slate-500 cursor-pointer transition flex items-start space-x-3";
                        }
                    }
                });
            } catch (e) {
                console.error("LLM status error:", e);
            }
        }

        function openAIModelModal() {
            document.getElementById('ai-model-modal').classList.remove('hidden');
        }

        function closeAIModelModal() {
            document.getElementById('ai-model-modal').classList.add('hidden');
        }

        async function selectAIProvider(provider) {
            try {
                const res = await fetch('/api/llm/provider', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider })
                });
                const data = await res.json();
                await loadLLMStatus();
                closeAIModelModal();
            } catch (err) {
                console.error("Failed to select AI provider:", err);
            }
        }

        async function loadTaxAudit(incomeOverride) {
            try {
                const income = incomeOverride || document.getElementById('input-tax-income').value || 60000;
                const res = await fetch(`/api/tax/audit?income=${income}`);
                const data = await res.json();

                // 60% Trap
                const trap = data.trap_60_percent;
                const trapBox = document.getElementById('content-60-trap');
                trapBox.innerHTML = `
                    <div class="p-3 rounded-lg ${trap.is_affected ? 'bg-rose-950/30 border border-rose-800' : 'bg-emerald-950/30 border border-emerald-800'}">
                        <div class="font-bold ${trap.is_affected ? 'text-rose-300' : 'text-emerald-300'} mb-1">${trap.is_affected ? '⚠️ Exposed to 60% Trap' : '✓ Safe from 60% Trap'}</div>
                        <p class="text-slate-300">${trap.message}</p>
                        ${trap.is_affected ? `<div class="mt-2 text-[11px] font-semibold text-emerald-400">Recommended Pension Sacrifice: £${trap.recommended_pension_sacrifice.toLocaleString('en-GB', {minimumFractionDigits: 2})} to save £${trap.tax_drag_gbp.toLocaleString('en-GB', {minimumFractionDigits: 2})} in tax.</div>` : ''}
                    </div>
                `;

                // PSA Drag
                const psa = data.psa_cash_drag;
                document.getElementById('content-psa-drag').innerHTML = `
                    <div class="space-y-1.5 text-slate-300">
                        <div>Tax Band: <strong class="text-white">${data.tax_band}</strong></div>
                        <div>Personal Savings Allowance: <strong class="text-white">£${psa.personal_savings_allowance}/yr</strong></div>
                        <div>Annual Gross Interest: <strong class="text-white">£${psa.annual_gross_interest.toFixed(2)}</strong></div>
                        <div>Tax Drag on Savings: <strong class="text-rose-400">£${psa.tax_drag_gbp.toFixed(2)}/yr</strong></div>
                        <div class="text-[11px] text-emerald-400 mt-2">${psa.recommendation}</div>
                    </div>
                `;

                // SIPP Relief Example
                const sipp = data.sipp_relief_example;
                document.getElementById('content-sipp-relief').innerHTML = `
                    <div class="space-y-2 text-slate-300">
                        <div class="flex justify-between"><span>Gross Contribution:</span><strong class="text-white">£${sipp.gross_contribution.toFixed(2)}</strong></div>
                        <div class="flex justify-between"><span>Upfront Cash You Pay:</span><strong class="text-slate-200">£${sipp.upfront_cash_paid.toFixed(2)}</strong></div>
                        <div class="flex justify-between text-emerald-400"><span>Basic 20% Relief at Source:</span><strong>+£${sipp.basic_relief_at_source.toFixed(2)}</strong></div>
                        <div class="flex justify-between text-emerald-400"><span>Higher/Additional Relief Claim:</span><strong>+£${sipp.higher_relief_to_reclaim.toFixed(2)}</strong></div>
                        <div class="flex justify-between border-t border-slate-800 pt-2 font-bold text-white"><span>Effective Net Cost:</span><span class="text-cyan-400">£${sipp.effective_net_cost.toFixed(2)}</span></div>
                        <div class="p-2 bg-emerald-950/40 rounded text-center text-xs font-bold text-emerald-300">Instant ROI on Net Cash: ${sipp.effective_roi_instant}%</div>
                    </div>
                `;
            } catch (err) {
                console.error("Tax audit error:", err);
            }
        }

        function recalculateTaxAudit() {
            const inc = document.getElementById('input-tax-income').value;
            loadTaxAudit(inc);
        }

        async function loadSweeper() {
            try {
                const res = await fetch('/api/sweep');
                const data = await res.json();
                const sw = data.sweeper;
                const so = data.standing_order;

                document.getElementById('sweep-status-box').innerHTML = `
                    <p class="text-slate-200">${sw.action_memo}</p>
                    <div class="grid grid-cols-3 gap-2 pt-2 text-[11px]">
                        <div class="p-2 bg-slate-850 rounded">Liquid Cash: <strong>£${sw.current_liquid_cash.toFixed(2)}</strong></div>
                        <div class="p-2 bg-slate-850 rounded">Operating Float: <strong>£${sw.target_operating_float.toFixed(2)}</strong></div>
                        <div class="p-2 bg-slate-850 rounded">Ready to Sweep: <strong class="text-emerald-400">£${sw.excess_cash_to_sweep.toFixed(2)}</strong></div>
                    </div>
                `;

                document.getElementById('standing-order-box').innerHTML = `
                    <p class="text-slate-300 mb-2">${so.rationale}</p>
                    <ul class="space-y-1 list-disc list-inside text-slate-400">
                        ${so.instructions.map(i => `<li>${i}</li>`).join('')}
                    </ul>
                `;
            } catch (err) {
                console.error("Sweeper error:", err);
            }
        }

        function renderScoutTables(scout) {
            // ISAs
            document.getElementById('tbody-isas').innerHTML = scout.cash_isas.map(i => `
                <tr class="hover:bg-slate-850">
                    <td class="py-2 font-medium text-slate-200">${i.provider}</td>
                    <td class="py-2 text-emerald-400 font-bold">${i.gross_aer}%</td>
                    <td class="py-2 text-slate-400">${i.flexible ? 'Flexible' : 'Standard'}</td>
                    <td class="py-2 text-slate-500">${i.notes}</td>
                </tr>
            `).join('');

            // Taxable
            document.getElementById('tbody-taxable').innerHTML = scout.taxable_savings.map(t => `
                <tr class="hover:bg-slate-850">
                    <td class="py-2 font-medium text-slate-200">${t.provider}</td>
                    <td class="py-2 text-slate-300">${t.gross_aer}%</td>
                    <td class="py-2 text-amber-400 font-bold">${t.net_aer_after_tax}%</td>
                    <td class="py-2 text-slate-500">${t.notes || t.access}</td>
                </tr>
            `).join('');

            // Switches
            document.getElementById('tbody-switches').innerHTML = scout.bank_switches.map(s => `
                <tr class="hover:bg-slate-850">
                    <td class="py-2 font-medium text-slate-200">${s.bank}</td>
                    <td class="py-2 text-emerald-400 font-bold">+£${s.bonus_cash}</td>
                    <td class="py-2 text-slate-400">${s.required_direct_debits}</td>
                    <td class="py-2">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold ${s.eligible ? 'bg-emerald-900/60 text-emerald-300' : 'bg-rose-900/60 text-rose-300'}">
                            ${s.eligible ? '✓ Qualified' : '✗ Needs ' + s.required_direct_debits + ' DDs'}
                        </span>
                    </td>
                </tr>
            `).join('');
        }

        // Credit & Borrowing Health Engine
        async function loadCreditAudit() {
            try {
                const res = await fetch('/api/credit/audit');
                const data = await res.json();
                renderCreditAudit(data);
            } catch (err) {
                console.error("Credit audit error:", err);
            }
        }

        function renderCreditAudit(audit) {
            if (!audit) return;
            const score = audit.borrowing_readiness_score || 0;
            const tier = audit.underwriter_tier || "Mainstream";
            const badgeColor = audit.tier_badge_color || "blue";

            // Tab badge
            const tabBadge = document.getElementById('badge-credit-score');
            if (tabBadge) {
                tabBadge.innerText = score;
                tabBadge.className = `px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                    score >= 85 ? 'bg-emerald-950 border-emerald-800 text-emerald-300' :
                    score >= 70 ? 'bg-blue-950 border-blue-800 text-blue-300' :
                    score >= 50 ? 'bg-amber-950 border-amber-800 text-amber-300' :
                    'bg-rose-950 border-rose-800 text-rose-300'
                }`;
            }

            // Executive Banner
            const scoreVal = document.getElementById('credit-score-val');
            if (scoreVal) {
                scoreVal.innerText = score;
                scoreVal.className = score >= 85 ? 'text-emerald-400' : score >= 70 ? 'text-blue-400' : score >= 50 ? 'text-amber-400' : 'text-rose-400';
            }

            const tierBadge = document.getElementById('credit-tier-badge');
            if (tierBadge) {
                tierBadge.innerText = tier;
                tierBadge.className = `px-2.5 py-0.5 rounded-full text-xs font-bold ${
                    badgeColor === 'emerald' ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700/60' :
                    badgeColor === 'blue' ? 'bg-blue-900/60 text-blue-300 border border-blue-700/60' :
                    badgeColor === 'amber' ? 'bg-amber-900/60 text-amber-300 border border-amber-700/60' :
                    'bg-rose-900/60 text-rose-300 border border-rose-700/60'
                }`;
            }

            const tierMemo = document.getElementById('credit-tier-memo');
            if (tierMemo) tierMemo.innerText = audit.tier_description || "";

            // Component scores
            const comps = audit.score_breakdown || {};
            if (comps.cash_flow_affordability && document.getElementById('comp-cashflow')) {
                document.getElementById('comp-cashflow').innerText = `${comps.cash_flow_affordability.score}/${comps.cash_flow_affordability.max_points}`;
            }
            if (comps.debt_to_income && document.getElementById('comp-dti')) {
                document.getElementById('comp-dti').innerText = `${comps.debt_to_income.score}/${comps.debt_to_income.max_points}`;
            }
            if (comps.underwriter_clean_record && document.getElementById('comp-hygiene')) {
                const s = comps.underwriter_clean_record.score;
                const m = comps.underwriter_clean_record.max_points;
                const el = document.getElementById('comp-hygiene');
                el.innerText = `${s}/${m}`;
                el.className = s === m ? 'text-emerald-400 font-bold' : 'text-amber-400 font-bold';
            }
            if (comps.stability_and_identity && document.getElementById('comp-stability')) {
                document.getElementById('comp-stability').innerText = `${comps.stability_and_identity.score}/${comps.stability_and_identity.max_points}`;
            }

            // Cash-Flow Affordability
            const cf = audit.cash_flow_affordability || {};
            if (document.getElementById('cf-monthly-net')) document.getElementById('cf-monthly-net').innerText = `£${(cf.monthly_net_income || 0).toLocaleString('en-GB', {minimumFractionDigits: 2})}`;
            if (document.getElementById('cf-annual-gross')) document.getElementById('cf-annual-gross').innerText = `£${(cf.estimated_annual_gross || 0).toLocaleString('en-GB', {minimumFractionDigits: 2})}`;
            if (document.getElementById('cf-fixed-needs')) document.getElementById('cf-fixed-needs').innerText = `-£${(cf.monthly_fixed_needs || 0).toLocaleString('en-GB', {minimumFractionDigits: 2})}/mo`;
            if (document.getElementById('cf-debt-commitments')) document.getElementById('cf-debt-commitments').innerText = `-£${(cf.monthly_committed_debt || 0).toLocaleString('en-GB', {minimumFractionDigits: 2})}/mo`;
            if (document.getElementById('cf-umi-amount')) document.getElementById('cf-umi-amount').innerText = `£${(cf.uncommitted_monthly_income_umi || 0).toLocaleString('en-GB', {minimumFractionDigits: 2})} / mo`;
            if (document.getElementById('cf-umi-pct')) document.getElementById('cf-umi-pct').innerText = `${cf.umi_surplus_pct || 0}% surplus`;
            if (document.getElementById('cf-dti-val')) document.getElementById('cf-dti-val').innerText = `${cf.contractual_dti_pct || 0}%`;
            if (document.getElementById('cf-dti-bar')) {
                const pct = Math.min(100, (cf.contractual_dti_pct || 0) * 2);
                document.getElementById('cf-dti-bar').style.width = `${pct}%`;
                document.getElementById('cf-dti-bar').className = (cf.contractual_dti_pct || 0) > 35 ? 'bg-rose-500 h-1.5 rounded-full' : (cf.contractual_dti_pct || 0) > 20 ? 'bg-amber-500 h-1.5 rounded-full' : 'bg-emerald-500 h-1.5 rounded-full';
            }

            // Risk Flags Scanner
            const rf = audit.underwriter_risk_flags || {};
            const rfContainer = document.getElementById('underwriter-flags-container');
            if (rfContainer) {
                rfContainer.innerHTML = `
                    <div class="p-2.5 bg-slate-850 rounded-lg flex items-center justify-between border ${rf.bnpl_detected ? 'border-amber-800/80 bg-amber-950/20' : 'border-slate-800'}">
                        <div>
                            <div class="font-bold text-slate-200 flex items-center space-x-1.5">
                                <span>${rf.bnpl_detected ? '⚠️' : '✅'}</span>
                                <span>Buy-Now-Pay-Later (BNPL / Klarna)</span>
                            </div>
                            <div class="text-[11px] text-slate-400 mt-0.5">${rf.bnpl_summary || 'No BNPL instalments detected'}</div>
                        </div>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold ${rf.bnpl_detected ? 'bg-amber-900/60 text-amber-300' : 'bg-emerald-900/60 text-emerald-300'}">
                            ${rf.bnpl_detected ? 'Warning' : 'Clean'}
                        </span>
                    </div>

                    <div class="p-2.5 bg-slate-850 rounded-lg flex items-center justify-between border ${rf.bounced_direct_debits_detected ? 'border-rose-800/80 bg-rose-950/20' : 'border-slate-800'}">
                        <div>
                            <div class="font-bold text-slate-200 flex items-center space-x-1.5">
                                <span>${rf.bounced_direct_debits_detected ? '🚨' : '✅'}</span>
                                <span>Returned Direct Debits (180d)</span>
                            </div>
                            <div class="text-[11px] text-slate-400 mt-0.5">${rf.bounced_direct_debits_detected ? rf.bounced_count + ' returned DD unpaid' : 'Zero returned payments'}</div>
                        </div>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold ${rf.bounced_direct_debits_detected ? 'bg-rose-900/60 text-rose-300' : 'bg-emerald-900/60 text-emerald-300'}">
                            ${rf.bounced_direct_debits_detected ? 'Action Required' : 'Clean'}
                        </span>
                    </div>

                    <div class="p-2.5 bg-slate-850 rounded-lg flex items-center justify-between border ${rf.overdraft_reliance ? 'border-amber-800/80' : 'border-slate-800'}">
                        <div>
                            <div class="font-bold text-slate-200 flex items-center space-x-1.5">
                                <span>${rf.overdraft_reliance ? '⚠️' : '✅'}</span>
                                <span>Overdraft Reliance & Fees</span>
                            </div>
                            <div class="text-[11px] text-slate-400 mt-0.5">${rf.overdraft_reliance ? 'Overdraft interest or unarranged fees detected' : 'Operating in surplus (no overdraft charges)'}</div>
                        </div>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold ${rf.overdraft_reliance ? 'bg-amber-900/60 text-amber-300' : 'bg-emerald-900/60 text-emerald-300'}">
                            ${rf.overdraft_reliance ? 'Caution' : 'Clean'}
                        </span>
                    </div>

                    <div class="p-2.5 bg-slate-850 rounded-lg flex items-center justify-between border border-slate-800">
                        <div>
                            <div class="font-bold text-slate-200 flex items-center space-x-1.5">
                                <span>${rf.gambling_pct_of_income > 1.0 ? '⚠️' : '✅'}</span>
                                <span>Gambling Spend Velocity (30d)</span>
                            </div>
                            <div class="text-[11px] text-slate-400 mt-0.5">£${(rf.gambling_spend_30d || 0).toFixed(2)} (${rf.gambling_pct_of_income}% of net income)</div>
                        </div>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold ${rf.gambling_pct_of_income < 1.0 ? 'bg-emerald-900/60 text-emerald-300' : 'bg-amber-900/60 text-amber-300'}">
                            ${rf.gambling_risk}
                        </span>
                    </div>

                    <div class="p-2.5 bg-slate-850 rounded-lg flex items-center justify-between border border-slate-800">
                        <div>
                            <div class="font-bold text-slate-200 flex items-center space-x-1.5">
                                <span>✅</span>
                                <span>UK Electoral Roll Identity</span>
                            </div>
                            <div class="text-[11px] text-slate-400 mt-0.5">${rf.electoral_roll_verified ? 'Registered at current address' : 'Not registered on electoral register'}</div>
                        </div>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold ${rf.electoral_roll_verified ? 'bg-emerald-900/60 text-emerald-300' : 'bg-rose-900/60 text-rose-300'}">
                            ${rf.electoral_roll_verified ? 'Verified' : 'Missing'}
                        </span>
                    </div>
                `;
            }

            // Mortgage Capacity
            const mc = audit.mortgage_borrowing_capacity || {};
            if (document.getElementById('mc-net-capacity')) document.getElementById('mc-net-capacity').innerText = `£${(mc.net_maximum_borrowing_capacity || 0).toLocaleString('en-GB', {minimumFractionDigits: 2})}`;
            if (document.getElementById('mc-gross-base')) document.getElementById('mc-gross-base').innerText = `Gross Base (4.5x): £${(mc.gross_income_baseline || 0).toLocaleString('en-GB', {minimumFractionDigits: 0})}`;
            if (document.getElementById('mc-debt-deduction')) document.getElementById('mc-debt-deduction').innerText = `Debt drag: -£${(mc.debt_commitment_deduction || 0).toLocaleString('en-GB', {minimumFractionDigits: 0})}`;
            if (document.getElementById('mc-indicative-repayment')) document.getElementById('mc-indicative-repayment').innerHTML = `£${(mc.indicative_monthly_repayment || 0).toFixed(2)}<span class="text-[10px] text-slate-500 font-normal">/mo</span>`;
            if (document.getElementById('mc-indicative-rate')) document.getElementById('mc-indicative-rate').innerText = `${mc.indicative_rate_pct || 4.40}% rate (25-yr)`;
            if (document.getElementById('mc-stress-repayment')) document.getElementById('mc-stress-repayment').innerHTML = `£${(mc.stress_tested_monthly_repayment || 0).toFixed(2)}<span class="text-[10px] text-slate-500 font-normal">/mo</span>`;
            if (document.getElementById('mc-stress-rate')) document.getElementById('mc-stress-rate').innerText = `${mc.stress_tested_rate_pct || 7.50}% stress test`;

            const stressHeadroom = Math.round((cf.uncommitted_monthly_income_umi || 0) - (mc.stress_tested_monthly_repayment || 0));
            const headroomEl = document.getElementById('mc-stress-headroom');
            if (headroomEl) {
                headroomEl.innerText = `${stressHeadroom >= 0 ? '+' : ''}£${stressHeadroom.toLocaleString('en-GB')}/mo surplus`;
                headroomEl.className = stressHeadroom >= 0 ? 'font-bold text-emerald-400' : 'font-bold text-rose-400';
            }

            // Stress & Runway Simulator
            const er = audit.emergency_runway_and_stress || {};
            if (document.getElementById('sim-runway-comfort')) document.getElementById('sim-runway-comfort').innerText = `${er.comfortable_runway_months || 0} mo`;
            if (document.getElementById('sim-runway-survival')) document.getElementById('sim-runway-survival').innerText = `${er.survival_runway_months || 0} mo`;

            const scenContainer = document.getElementById('stress-scenarios-container');
            if (scenContainer && er.scenarios) {
                scenContainer.innerHTML = er.scenarios.map(sc => `
                    <div class="p-3 bg-slate-850 rounded-xl border border-slate-800 space-y-1.5">
                        <div class="flex justify-between items-start">
                            <div>
                                <div class="font-bold text-slate-200 text-xs">${sc.name}</div>
                                <div class="text-[11px] text-slate-400">${sc.description}</div>
                            </div>
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
                                sc.status ? (sc.status.includes('Resilient') ? 'bg-emerald-900/60 text-emerald-300' : 'bg-rose-900/60 text-rose-300') :
                                sc.absorbed_comfortably !== undefined ? (sc.absorbed_comfortably ? 'bg-emerald-900/60 text-emerald-300' : 'bg-amber-900/60 text-amber-300') :
                                sc.is_affordable ? 'bg-emerald-900/60 text-emerald-300' : 'bg-rose-900/60 text-rose-300'
                            }">
                                ${sc.status || (sc.absorbed_comfortably ? 'Absorbed Comfortably' : (sc.is_affordable ? 'Affordable' : 'Tight Margin'))}
                            </span>
                        </div>
                        <div class="text-[11px] text-slate-400 flex items-center space-x-3 pt-1 border-t border-slate-800/60">
                            ${sc.comfortable_months !== undefined ? `<span>Comfortable Runway: <strong class="text-white">${sc.comfortable_months} mo</strong></span>` : ''}
                            ${sc.survival_months !== undefined ? `<span>Survival Runway: <strong class="text-emerald-400">${sc.survival_months} mo</strong></span>` : ''}
                            ${sc.remaining_cash !== undefined ? `<span>Remaining Cash: <strong class="text-white">£${sc.remaining_cash.toLocaleString('en-GB', {minimumFractionDigits: 2})}</strong></span>` : ''}
                            ${sc.remaining_runway_months !== undefined ? `<span>Runway: <strong class="text-emerald-400">${sc.remaining_runway_months} mo</strong></span>` : ''}
                            ${sc.new_umi !== undefined ? `<span>Adjusted UMI: <strong class="text-white">£${sc.new_umi.toFixed(2)}/mo</strong></span>` : ''}
                            ${sc.new_dti_pct !== undefined ? `<span>New DTI: <strong class="text-cyan-400">${sc.new_dti_pct}%</strong></span>` : ''}
                        </div>
                    </div>
                `).join('');
            }

            const inf = er.inflation_erosion || {};
            if (document.getElementById('sim-inflation-loss')) document.getElementById('sim-inflation-loss').innerText = `-£${(inf.annual_purchasing_power_loss_gbp || 0).toLocaleString('en-GB', {minimumFractionDigits: 2})} / yr`;
            if (document.getElementById('sim-isa-recovery')) document.getElementById('sim-isa-recovery').innerText = `+£${(inf.cash_isa_recovery_gain_gbp || 0).toLocaleString('en-GB', {minimumFractionDigits: 2})} / yr in Top Cash ISA`;

            // Bureau Scores inputs
            const bs = audit.bureau_scores || {};
            if (document.getElementById('input-score-experian') && bs.experian !== null && bs.experian !== undefined) {
                document.getElementById('input-score-experian').value = bs.experian;
            }
            if (document.getElementById('input-score-equifax') && bs.equifax !== null && bs.equifax !== undefined) {
                document.getElementById('input-score-equifax').value = bs.equifax;
            }
            if (document.getElementById('input-score-transunion') && bs.transunion !== null && bs.transunion !== undefined) {
                document.getElementById('input-score-transunion').value = bs.transunion;
            }
            if (document.getElementById('input-score-electoral')) {
                document.getElementById('input-score-electoral').checked = bs.electoral_roll !== false;
            }

            // Action Playbook
            const playbook = audit.action_playbook || [];
            const pbContainer = document.getElementById('credit-playbook-cards');
            if (pbContainer) {
                if (playbook.length === 0) {
                    pbContainer.innerHTML = `<div class="col-span-3 text-center py-4 text-xs text-slate-500">Your profile is prime. No immediate corrective underwriter actions required.</div>`;
                } else {
                    pbContainer.innerHTML = playbook.map(card => {
                        const isCrit = card.priority === 'CRITICAL';
                        const isHigh = card.priority === 'HIGH';
                        const borderCls = isCrit ? 'border-l-4 border-l-rose-500' : isHigh ? 'border-l-4 border-l-amber-500' : 'border-l-4 border-l-blue-500';
                        const badgeCls = isCrit ? 'bg-rose-950 text-rose-300 border-rose-800' : isHigh ? 'bg-amber-950 text-amber-300 border-amber-800' : 'bg-blue-950 text-blue-300 border-blue-800';
                        return `
                            <div class="card p-4 space-y-2 ${borderCls}">
                                <div class="flex items-center justify-between">
                                    <span class="text-[10px] px-2 py-0.5 rounded font-bold uppercase border ${badgeCls}">${card.priority}</span>
                                    <span class="text-[10px] text-slate-500 uppercase font-semibold">Underwriter Guidance</span>
                                </div>
                                <div class="font-bold text-xs text-white">${card.title}</div>
                                <p class="text-[11px] text-slate-400 leading-relaxed">${card.action}</p>
                            </div>
                        `;
                    }).join('');
                }
            }
        }

        async function saveCreditScores() {
            const expVal = document.getElementById('input-score-experian').value;
            const eqVal = document.getElementById('input-score-equifax').value;
            const tuVal = document.getElementById('input-score-transunion').value;
            const elVal = document.getElementById('input-score-electoral').checked;
            const statusEl = document.getElementById('credit-save-status');
            const btn = document.getElementById('btn-save-credit-scores');

            if (btn) btn.disabled = true;
            if (statusEl) statusEl.innerText = "Saving to SQLite...";

            try {
                const res = await fetch('/api/credit/scores', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        experian: expVal ? parseInt(expVal) : null,
                        equifax: eqVal ? parseInt(eqVal) : null,
                        transunion: tuVal ? parseInt(tuVal) : null,
                        electoral_roll: elVal
                    })
                });
                const result = await res.json();
                if (statusEl) {
                    statusEl.innerText = "✓ Saved & re-audited";
                    setTimeout(() => { statusEl.innerText = "Local SQLite storage"; }, 3000);
                }
                await loadCreditAudit();
            } catch (err) {
                console.error("Failed to save credit scores:", err);
                if (statusEl) statusEl.innerText = "Error saving scores";
            } finally {
                if (btn) btn.disabled = false;
            }
        }

        // Navigation Tabs
        function switchMainTab(tabId) {
            ['overview', 'networth', 'transactions', 'watchdog', 'credit', 'tax', 'sweep', 'scout', 'walkthrough'].forEach(t => {
                const sec = document.getElementById(`section-${t}`);
                if (sec) sec.classList.add('hidden');
                const btn = document.getElementById(`tab-btn-${t}`);
                if (btn) btn.className = 'px-3.5 py-1.5 text-slate-400 hover:text-slate-200 rounded-lg whitespace-nowrap';
            });
            const activeSec = document.getElementById(`section-${tabId}`);
            if (activeSec) activeSec.classList.remove('hidden');
            const activeBtn = document.getElementById(`tab-btn-${tabId}`);
            if (activeBtn) activeBtn.className = 'px-3.5 py-1.5 bg-slate-800 text-emerald-400 rounded-lg whitespace-nowrap';
            if (tabId === 'transactions') {
                loadTransactionsFeed();
            } else if (tabId === 'credit') {
                loadCreditAudit();
            }
        }

        async function loadTransactionsFeed() {
            const bankSelect = document.getElementById('tx-filter-bank');
            const limitSelect = document.getElementById('tx-filter-limit');
            const searchInput = document.getElementById('tx-filter-search');
            const tbody = document.getElementById('tx-table-body');
            const countBadge = document.getElementById('tx-count-badge');
            if (!tbody) return;

            const bank = bankSelect ? bankSelect.value : '';
            const limit = limitSelect ? limitSelect.value : '50';
            const search = searchInput ? searchInput.value.trim() : '';

            const params = new URLSearchParams();
            if (bank) params.append('account', bank);
            if (limit && limit !== 'all') params.append('limit', limit);
            if (search) params.append('search', search);

            try {
                const res = await fetch(`/api/transactions?${params.toString()}`);
                const data = await res.json();
                const txs = data.transactions || [];

                if (countBadge) {
                    countBadge.innerText = `${txs.length} transaction${txs.length === 1 ? '' : 's'}`;
                }

                if (txs.length === 0) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="5" class="py-8 text-center text-slate-500 text-xs">
                                📭 No transactions found matching selected filters.
                            </td>
                        </tr>
                    `;
                    return;
                }

                tbody.innerHTML = txs.map(t => {
                    const inst = (t.institution_name || t.account_name || '').toLowerCase();
                    let badgeClass = 'bg-slate-800 text-slate-300 border-slate-700';
                    let bankLabel = t.institution_name || 'Bank';
                    if (inst.includes('revolut')) {
                        badgeClass = 'bg-sky-500/15 text-sky-300 border-sky-500/30';
                        bankLabel = 'Revolut';
                    } else if (inst.includes('natwest')) {
                        badgeClass = 'bg-purple-500/15 text-purple-300 border-purple-500/30';
                        bankLabel = 'NatWest';
                    } else if (inst.includes('wise')) {
                        badgeClass = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
                        bankLabel = 'Wise';
                    }

                    const isCredit = t.amount > 0;
                    const amountFormatted = isCredit
                        ? `+£${t.amount.toFixed(2)}`
                        : `-£${Math.abs(t.amount).toFixed(2)}`;
                    const amountClass = isCredit ? 'text-emerald-400 font-bold' : 'text-slate-200 font-medium';

                    const merchantName = t.counterparty_name || t.description || 'Unknown Counterparty';
                    const isPending = (t.status || '').toLowerCase() === 'pending';
                    const pendingBadge = isPending
                        ? `<span class="ml-1.5 px-1.5 py-0.5 rounded text-[9px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 uppercase tracking-wider">Pending</span>`
                        : '';
                    const subText = t.account_name ? `<span class="text-[10px] text-slate-500 block">${t.account_name}</span>` : '';

                    return `
                        <tr class="hover:bg-slate-850/60 transition text-xs">
                            <td class="py-2.5 font-mono text-slate-400 whitespace-nowrap text-[11px]">${t.booking_date || 'N/A'}</td>
                            <td class="py-2.5 whitespace-nowrap">
                                <span class="px-2 py-0.5 rounded text-[10px] font-semibold border ${badgeClass}">
                                    ${bankLabel}
                                </span>
                            </td>
                            <td class="py-2.5 font-medium text-slate-200">
                                <div class="flex items-center space-x-1.5">
                                    <span>${merchantName}</span>
                                    ${pendingBadge}
                                </div>
                                ${subText}
                            </td>
                            <td class="py-2.5 text-slate-400 text-[11px]">
                                <span class="px-2 py-0.5 rounded bg-slate-800/80 text-slate-300 text-[10px]">
                                    ${t.category || 'General'}
                                </span>
                            </td>
                            <td class="py-2.5 text-right font-mono text-xs ${amountClass} whitespace-nowrap">
                                ${amountFormatted}
                            </td>
                        </tr>
                    `;
                }).join('');
            } catch (err) {
                console.error("Failed to load transactions feed:", err);
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" class="py-4 text-center text-rose-400 text-xs">
                            ⚠️ Error loading transactions feed: ${err}
                        </td>
                    </tr>
                `;
            }
        }

        function switchScoutTab(tab) {
            document.querySelectorAll('.scout-subtab').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('[id^="tab-btn-scout-"]').forEach(el => {
                el.className = 'px-3 py-1 text-slate-400 hover:text-slate-200';
            });
            document.getElementById('scout-tab-' + tab).classList.remove('hidden');
            document.getElementById('tab-btn-scout-' + tab).className = 'px-3 py-1 bg-slate-800 text-emerald-400 rounded-md';
        }

        // AI Copilot Drawer & Chat
        function toggleCopilot() {
            const drawer = document.getElementById('copilot-drawer');
            drawer.classList.toggle('hidden');
        }

        async function loadChatHistory() {
            try {
                const res = await fetch('/api/copilot/history');
                const data = await res.json();
                const container = document.getElementById('copilot-messages');
                if (data.messages && data.messages.length > 0) {
                    container.innerHTML = data.messages.map(m => `
                        <div class="p-2.5 rounded-xl ${m.role === 'user' ? 'bg-purple-950/30 border border-purple-800/40 text-purple-200 ml-6' : 'bg-slate-800 text-slate-200 mr-6'}">
                            <div class="font-bold text-[10px] mb-1 opacity-70">${m.role.toUpperCase()}</div>
                            <div class="prose prose-invert max-w-none text-xs">${marked.parse(m.content)}</div>
                        </div>
                    `).join('');
                    container.scrollTop = container.scrollHeight;
                }
            } catch (e) {
                console.error("Chat history error:", e);
            }
        }

        async function submitCopilotQuery(query) {
            const container = document.getElementById('copilot-messages');
            container.innerHTML += `
                <div class="p-2.5 rounded-xl bg-purple-950/30 border border-purple-800/40 text-purple-200 ml-6">
                    <div class="font-bold text-[10px] mb-1 opacity-70">YOU</div>
                    <div>${query}</div>
                </div>
                <div class="p-2.5 rounded-xl bg-slate-800 text-slate-200 mr-6" id="loading-copilot-msg">
                    <span class="animate-pulse">Consulting fiduciary intelligence...</span>
                </div>
            `;
            container.scrollTop = container.scrollHeight;

            try {
                const res = await fetch('/api/copilot/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query })
                });
                const data = await res.json();
                document.getElementById('loading-copilot-msg').remove();
                const badge = data.badge ? `<span class="text-[9px] px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300 font-normal">${data.badge}</span>` : '';
                container.innerHTML += `
                    <div class="p-2.5 rounded-xl bg-slate-800 text-slate-200 mr-6">
                        <div class="font-bold text-[10px] mb-1 opacity-70 flex items-center justify-between">
                            <span>FIDUCIARY COPILOT</span>
                            ${badge}
                        </div>
                        <div class="prose prose-invert max-w-none text-xs">${marked.parse(data.answer)}</div>
                    </div>
                `;
                container.scrollTop = container.scrollHeight;
            } catch (err) {
                document.getElementById('loading-copilot-msg').innerHTML = `<span class="text-rose-400">Error: ${err}</span>`;
            }
        }

        document.getElementById('copilot-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const input = document.getElementById('copilot-input');
            const q = input.value.trim();
            if (!q) return;
            input.value = '';
            submitCopilotQuery(q);
        });

        function sendQuickPrompt(prompt) {
            const drawer = document.getElementById('copilot-drawer');
            drawer.classList.remove('hidden');
            submitCopilotQuery(prompt);
        }

        async function clearChat() {
            await fetch('/api/copilot/clear', { method: 'POST' });
            document.getElementById('copilot-messages').innerHTML = `
                <div class="p-2.5 bg-slate-800/70 rounded-xl text-slate-300">
                    Chat history cleared. How can I help you today?
                </div>
            `;
        }

        // Custom Asset Modal
        function openAddAssetModal() { document.getElementById('add-asset-modal').classList.remove('hidden'); }
        function closeAddAssetModal() { document.getElementById('add-asset-modal').classList.add('hidden'); }

        document.getElementById('add-asset-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('asset-name').value;
            const asset_class = document.getElementById('asset-class').value;
            const balance = parseFloat(document.getElementById('asset-balance').value);
            const notes = document.getElementById('asset-notes').value;

            await fetch('/api/assets/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, asset_class, balance, notes })
            });

            closeAddAssetModal();
            await loadNetWorth();
        });

        async function deleteAsset(accId) {
            if (!confirm(`Are you sure you want to remove this account/asset?`)) return;
            await fetch(`/api/assets/${accId}`, { method: 'DELETE' });
            await fetchAllState();
        }

        // AI Observability & Traces Modal
        function openTracesModal() {
            document.getElementById('ai-traces-modal').classList.remove('hidden');
            loadTracesUI();
        }

        function closeTracesModal() {
            document.getElementById('ai-traces-modal').classList.add('hidden');
        }

        async function loadTracesUI() {
            const container = document.getElementById('traces-list-container');
            try {
                const res = await fetch('/api/traces');
                const data = await res.json();

                document.getElementById('trace-metric-total').innerText = data.metrics.total_invocations;
                document.getElementById('trace-metric-latency').innerText = `${data.metrics.avg_latency_ms.toFixed(0)} ms`;
                document.getElementById('trace-metric-grounding').innerText = `${data.metrics.grounding_pass_rate_pct.toFixed(0)}%`;
                document.getElementById('trace-metric-local').innerText = `${data.metrics.local_share_pct.toFixed(0)}%`;
                const judgeEl = document.getElementById('trace-metric-judge');
                if (judgeEl) {
                    judgeEl.innerText = `${data.metrics.judge_pass_rate_pct.toFixed(0)}% (${data.metrics.judged_count || 0}/${data.metrics.total_invocations || 0})`;
                }

                if (!data.traces || data.traces.length === 0) {
                    container.innerHTML = '<div class="text-center py-8 text-slate-500">No AI agent traces recorded yet. Query the Copilot or generate an AI Memo to populate live traces.</div>';
                    return;
                }

                container.innerHTML = data.traces.map(t => {
                    const isGrounded = t.grounding_status === 'VERIFIED_GROUNDED';
                    const badgeColor = isGrounded ? 'bg-emerald-950 text-emerald-300 border-emerald-800' : 'bg-amber-950 text-amber-300 border-amber-800';
                    const provColor = t.provider === 'local' ? 'bg-emerald-950 text-emerald-400 border-emerald-800' : 'bg-purple-950 text-purple-400 border-purple-800';
                    const provLabel = t.provider === 'local' ? `🟢 Local (${t.model})` : `🟣 ${t.provider}`;

                    const je = t.judge_evaluation;
                    let judgePill = '';
                    let judgeSection = '';

                    if (je) {
                        const v = (je.verdict || 'PASSED').toUpperCase();
                        const vBadge = v === 'PASSED'
                            ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                            : (v === 'WARNING' ? 'bg-amber-950 text-amber-300 border-amber-800' : 'bg-rose-950 text-rose-300 border-rose-800');
                        const scorePct = je.overall_score !== undefined ? `${(je.overall_score * 100).toFixed(0)}%` : '100%';
                        const faithPct = je.faithfulness !== undefined ? `${(je.faithfulness * 100).toFixed(0)}%` : '100%';
                        const relPct = je.relevance !== undefined ? `${(je.relevance * 100).toFixed(0)}%` : '100%';
                        const fidPct = je.fiduciary_soundness !== undefined ? `${(je.fiduciary_soundness * 100).toFixed(0)}%` : '100%';
                        const latStr = je.judge_latency_ms ? `${je.judge_latency_ms.toFixed(0)} ms` : '';
                        const judgeModelStr = je.judge_model || 'Local Ollama';

                        judgePill = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold border ${vBadge}">⚖️ Judge: ${v} (${scorePct})</span>`;

                        judgeSection = `
                            <div class="mt-3 p-3 rounded-lg bg-fuchsia-950/20 border border-fuchsia-900/50 space-y-2">
                                <div class="flex items-center justify-between">
                                    <div class="flex items-center space-x-2">
                                        <span class="text-[11px] font-bold text-fuchsia-300 flex items-center gap-1">⚖️ Independent LLM Judge Audit</span>
                                        <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${vBadge}">${v} (${scorePct})</span>
                                    </div>
                                    <div class="text-[10px] text-fuchsia-400/80 font-mono">
                                        <span>${judgeModelStr}</span> ${latStr ? '• <span>' + latStr + '</span>' : ''}
                                    </div>
                                </div>
                                <div class="grid grid-cols-3 gap-2 text-center text-[10px] py-1.5 bg-slate-950/70 rounded border border-slate-800 font-mono">
                                    <div>
                                        <div class="text-slate-400 text-[9px] uppercase font-sans">Faithfulness</div>
                                        <div class="font-bold text-emerald-400">${faithPct}</div>
                                    </div>
                                    <div>
                                        <div class="text-slate-400 text-[9px] uppercase font-sans">Relevance</div>
                                        <div class="font-bold text-cyan-400">${relPct}</div>
                                    </div>
                                    <div>
                                        <div class="text-slate-400 text-[9px] uppercase font-sans">Fiduciary Soundness</div>
                                        <div class="font-bold text-amber-400">${fidPct}</div>
                                    </div>
                                </div>
                                <div class="text-xs text-slate-300 bg-slate-950/90 p-2.5 rounded border border-slate-800/80">
                                    <span class="text-[10px] text-fuchsia-400 font-semibold uppercase block mb-1">Judge Critique & Reasoning:</span>
                                    <div class="text-slate-200 text-xs leading-relaxed font-sans">${je.reasoning || 'Evaluated successfully.'}</div>
                                </div>
                            </div>
                        `;
                    } else {
                        judgeSection = `
                            <div class="mt-2.5 flex items-center justify-between pt-2 border-t border-slate-800/60">
                                <span class="text-[11px] text-slate-500 italic">Independent judge evaluation not run yet</span>
                                <button id="judge-btn-${t.id}" onclick="runJudgeUI('${t.id}')" class="px-3 py-1 bg-fuchsia-950/50 hover:bg-fuchsia-900 border border-fuchsia-800/80 text-fuchsia-300 hover:text-fuchsia-200 rounded-lg text-[11px] font-semibold flex items-center gap-1.5 transition shadow-sm">
                                    <span>⚖️ Run Judge Audit</span>
                                </button>
                            </div>
                        `;
                    }

                    const tools = t.tools_used || [];
                    const toolsPill = tools.length > 0 ? `<span class="px-2 py-0.5 rounded text-[10px] font-semibold border bg-cyan-950 text-cyan-300 border-cyan-800">🛠️ ${tools.length} Tools</span>` : '';
                    let toolsSection = '';
                    if (tools.length > 0) {
                        toolsSection = `
                            <div class="mt-2.5 p-2.5 rounded-lg bg-slate-950/80 border border-cyan-900/40 space-y-1.5">
                                <div class="flex items-center justify-between text-[11px] font-bold text-cyan-300">
                                    <span class="flex items-center gap-1.5">
                                        <span>🛠️</span>
                                        <span>Active Tools & Data Ingestion (${tools.length} executed)</span>
                                    </span>
                                </div>
                                <div class="space-y-1.5 pt-0.5">
                                    ${tools.map(tool => {
                                        const typeColor = tool.type === 'live_web_scraping'
                                            ? 'text-cyan-400 bg-cyan-950/80 border-cyan-800'
                                            : (tool.type === 'market_benchmarks'
                                                ? 'text-emerald-400 bg-emerald-950/80 border-emerald-800'
                                                : (tool.type === 'web_api_lookup'
                                                    ? 'text-amber-400 bg-amber-950/80 border-amber-800'
                                                    : 'text-indigo-400 bg-indigo-950/80 border-indigo-800'));
                                        return `
                                            <div class="p-2 rounded bg-slate-900/90 border border-slate-800/80 text-[11px] flex flex-col space-y-0.5">
                                                <div class="flex items-center justify-between">
                                                    <span class="font-mono font-bold text-slate-200">${tool.tool_name}</span>
                                                    <div class="text-[10px] text-slate-400 font-mono flex items-center space-x-1.5">
                                                        <span class="px-1.5 py-0.5 rounded text-[9px] border ${typeColor}">${tool.type}</span>
                                                        <span>${tool.latency_ms ? tool.latency_ms.toFixed(1) + ' ms' : ''}</span>
                                                    </div>
                                                </div>
                                                <div class="text-slate-400 text-[10px] truncate">
                                                    <span class="text-slate-500 font-semibold">Source:</span> ${tool.url ? `<a href="${tool.url}" target="_blank" class="text-cyan-400 hover:underline font-mono">${tool.source}</a>` : `<span class="text-slate-300 font-mono">${tool.source}</span>`}
                                                </div>
                                                <div class="text-slate-300 text-[10px]">
                                                    <span class="text-slate-500 font-semibold">Data Ingested:</span> <span class="text-slate-200">${tool.summary}</span>
                                                </div>
                                            </div>
                                        `;
                                    }).join('')}
                                </div>
                            </div>
                        `;
                    }

                    return `
                        <div class="card p-4 space-y-2 border border-slate-800 hover:border-slate-700 transition">
                            <div class="flex items-center justify-between">
                                <div class="flex items-center space-x-2">
                                    <span class="font-bold text-xs uppercase text-slate-300">${t.caller}</span>
                                    <span class="px-2 py-0.5 rounded text-[10px] font-semibold border ${provColor}">${provLabel}</span>
                                    <span class="px-2 py-0.5 rounded text-[10px] font-semibold border ${badgeColor}">${isGrounded ? '✓ 100% Grounded' : t.grounding_status}</span>
                                    ${toolsPill}
                                    ${judgePill}
                                </div>
                                <div class="text-[11px] text-slate-400 font-mono">
                                    <span>${t.latency_ms.toFixed(0)} ms</span> • <span>${t.timestamp.slice(11, 19)}</span>
                                </div>
                            </div>
                            <div class="text-xs text-slate-300 bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
                                <div class="text-[10px] text-slate-500 uppercase font-semibold mb-1">User Query:</div>
                                <div class="text-slate-200">${(t.user_prompt.split('USER QUERY: ')[1] || t.user_prompt).trim()}</div>
                            </div>
                            <div class="text-xs text-slate-400 line-clamp-2">
                                <span class="text-slate-500 font-semibold">Response:</span> ${t.response}
                            </div>
                            ${toolsSection}
                            ${judgeSection}
                            <details class="text-[11px] text-slate-500">
                                <summary class="cursor-pointer hover:text-slate-300 transition py-1">View Full Raw Response & Grounding Context</summary>
                                <div class="space-y-2 pt-2 text-slate-300 font-mono text-[10px] bg-slate-950 p-3 rounded-lg border border-slate-800">
                                    <div class="font-bold text-slate-400 text-xs font-sans">Raw Response:</div>
                                    <div class="whitespace-pre-wrap font-sans text-xs text-slate-200 border-b border-slate-800 pb-2">${t.response}</div>
                                    <div class="font-bold text-slate-400 text-xs font-sans pt-1">Injected System Context (Ground Truth):</div>
                                    <div class="whitespace-pre-wrap max-h-48 overflow-y-auto text-[10px] text-slate-400">${t.system_prompt}</div>
                                </div>
                            </details>
                        </div>
                    `;
                }).join('');
            } catch (err) {
                container.innerHTML = `<div class="text-rose-400 text-center py-4">Error loading traces: ${err}</div>`;
            }
        }

        function toggleToolsCatalogUI() {
            const p = document.getElementById('tools-catalog-panel');
            if (p) p.classList.toggle('hidden');
        }

        async function runJudgeUI(traceId) {
            const btn = document.getElementById(`judge-btn-${traceId}`);
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = `<span class="animate-spin inline-block mr-1">⏳</span> Evaluating...`;
            }
            try {
                const res = await fetch(`/api/traces/${traceId}/judge`, { method: 'POST' });
                const data = await res.json();
                if (data.status === "ERROR" || data.error) {
                    alert(`Judge Error: ${data.error || data.reasoning}`);
                }
                await loadTracesUI();
            } catch (err) {
                alert(`Failed to evaluate trace: ${err}`);
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = `<span>⚖️ Run Judge Audit</span>`;
                }
            }
        }

        async function evaluateLatestJudgeUI() {
            const btn = document.getElementById('btn-judge-latest');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = `<span class="animate-spin inline-block mr-1">⏳</span> Evaluating...`;
            }
            try {
                const res = await fetch('/api/traces/judge-latest', { method: 'POST' });
                const data = await res.json();
                if (data.status === "ERROR" || data.error) {
                    alert(`Judge Error: ${data.error || data.reasoning}`);
                }
                await loadTracesUI();
            } catch (err) {
                alert(`Failed to evaluate latest trace: ${err}`);
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = `<span>⚖️ Judge Latest</span>`;
                }
            }
        }

        async function clearTracesUI() {
            if (!confirm('Clear all recorded AI agent traces?')) return;
            await fetch('/api/traces/clear', { method: 'POST' });
            await loadTracesUI();
        }

        // Cancellation Letter
        async function generateCancelLetter() {
            const service_name = document.getElementById('cancel-service').value;
            const monthly_cost = parseFloat(document.getElementById('cancel-cost').value || 0);
            const account_reference = document.getElementById('cancel-ref').value;

            const res = await fetch('/api/cancel-template', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ service_name, monthly_cost, account_reference })
            });
            const data = await res.json();
            document.getElementById('cancel-letter-subject').innerText = data.email_subject;
            document.getElementById('cancel-letter-body').innerText = data.email_body;
            document.getElementById('cancel-letter-output').classList.remove('hidden');
        }

        function copyCancelLetter() {
            const text = document.getElementById('cancel-letter-body').innerText;
            navigator.clipboard.writeText(text);
            alert("Cancellation notice copied to clipboard!");
        }

        async function generateAIBriefing() {
            const btn = document.getElementById('btn-ai-briefing');
            const box = document.getElementById('ai-briefing-box');
            const content = document.getElementById('ai-briefing-content');
            btn.innerText = 'Analyzing...';
            btn.disabled = true;
            try {
                const res = await fetch('/api/advisor/live', { method: 'POST' });
                const data = await res.json();
                content.innerHTML = marked.parse(data.briefing);
                box.classList.remove('hidden');
            } catch (e) {
                alert('Error generating AI briefing: ' + e);
            } finally {
                btn.innerText = '🤖 Live AI Memo';
                btn.disabled = false;
            }
        }

        async function connectTrueLayer() {
            const res = await fetch('/api/truelayer/auth-url');
            const data = await res.json();
            if (data.error) alert(data.error);
            else window.location.href = data.auth_url;
        }

        async function syncAllAccounts() {
            const label = document.getElementById('btn-sync-all-label');
            const originalText = label ? label.innerText : '⚡ Sync All';
            if (label) label.innerText = 'Syncing...';
            try {
                const res = await fetch('/api/sync/all', { method: 'POST' });
                const data = await res.json();
                if (data.truelayer && data.truelayer.status === 'needs_reconnect') {
                    console.log('Open Banking notification:', data.truelayer.error);
                }
            } catch (err) {
                console.error('Sync failed:', err);
            }
            if (label) label.innerText = originalText;
            await fetchAllState();
        }

        async function syncWise() {
            const label = document.getElementById('btn-sync-wise-label');
            if (label) label.innerText = 'Syncing...';
            await fetch('/api/sync/wise', { method: 'POST' });
            if (label) label.innerText = '⚡ Sync Wise';
            await fetchAllState();
        }

        document.getElementById('upload-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const input = document.getElementById('file-input');
            if (!input.files[0]) return;
            const fd = new FormData();
            fd.append('file', input.files[0]);
            const status = document.getElementById('upload-status');
            const submitBtn = document.getElementById('btn-upload-statement');
            if (submitBtn) { submitBtn.innerText = 'Parsing...'; submitBtn.disabled = true; }
            status.innerText = 'Parsing statement locally on your device...';
            status.className = 'text-xs mt-2 text-cyan-400';
            status.classList.remove('hidden');
            try {
                const res = await fetch('/api/upload', { method: 'POST', body: fd });
                const data = await res.json();
                if (data.status === 'success' || data.transactions_imported !== undefined) {
                    const recStatus = data.reconciliation_status || 'IMPORTED';
                    const isReconciled = recStatus === 'RECONCILED' || recStatus === 'CLOSING_BALANCE_VERIFIED';
                    const recBadge = isReconciled
                        ? `<span class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 font-semibold">100% Reconciled (£0.00 Discrepancy)</span>`
                        : (recStatus === 'UNRECONCILED_GAP'
                            ? `<span class="px-1.5 py-0.5 rounded text-[10px] bg-amber-950 text-amber-300 border border-amber-800 font-semibold">⚠️ Unreconciled Gap (£${Math.abs(data.discrepancy || 0).toFixed(2)})</span>`
                            : `<span class="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700 font-semibold">${recStatus}</span>`);

                    status.className = 'text-xs mt-2 text-emerald-400 font-semibold space-y-1';
                    status.innerHTML = `
                        <div class="flex items-center space-x-2 flex-wrap gap-y-1">
                            <span>✓ Imported ${data.transactions_imported} transactions from ${data.bank_name}</span>
                            ${recBadge}
                        </div>
                        <div class="text-[11px] text-slate-400 font-normal">
                            Inflows: <span class="text-emerald-400 font-semibold">+£${Number(data.total_inflows || 0).toLocaleString('en-GB', {minimumFractionDigits: 2})}</span> | 
                            Outflows: <span class="text-rose-400 font-semibold">-£${Number(data.total_outflows || 0).toLocaleString('en-GB', {minimumFractionDigits: 2})}</span> | 
                            Net Cashflow: <span class="text-slate-200 font-semibold">£${Number(data.calculated_delta || 0).toLocaleString('en-GB', {minimumFractionDigits: 2})}</span>
                        </div>
                    `;
                    input.value = '';
                    await fetchAllState();
                } else if (data.detail || data.error) {
                    status.className = 'text-xs mt-2 text-rose-400 font-semibold';
                    status.innerText = `⚠️ Error: ${data.detail || data.error}`;
                }
            } catch (err) {
                status.className = 'text-xs mt-2 text-rose-400 font-semibold';
                status.innerText = `⚠️ Upload failed: ${err}`;
            } finally {
                if (submitBtn) { submitBtn.innerText = 'Parse & Import'; submitBtn.disabled = false; }
            }
        });

        fetchAllState();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=DASHBOARD_HTML)

@app.get("/api/state")
def get_state():
    init_db()
    evaluator = FinancialEvaluator()
    state = evaluator.evaluate_financial_state()
    profiler = TransactionProfiler()
    profile = profiler.profile_finances()
    scout = MarketScout()
    market_quotes = scout.scout_market(profile)
    advisor = FiduciaryAdvisor()
    recommendations = advisor.generate_recommendations(state, profile)

    return {
        "state": state,
        "profile": profile,
        "scout": market_quotes,
        "recommendations": recommendations
    }

@app.get("/api/networth")
def get_net_worth():
    init_db()
    return get_net_worth_breakdown()

@app.post("/api/assets/add")
def add_custom_asset(req: AssetAddRequest):
    init_db()
    asset_id = f"asset_{req.name.lower().replace(' ', '_')[:24]}"
    upsert_custom_asset(
        asset_id=asset_id,
        name=req.name,
        asset_class=req.asset_class,
        account_type=req.account_type or req.asset_class,
        balance=req.balance,
        notes=req.notes
    )
    save_net_worth_snapshot()
    return {"status": "success", "asset_id": asset_id}

@app.delete("/api/assets/{acc_id}")
def remove_custom_asset(acc_id: str):
    init_db()
    success = delete_account(acc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found")
    save_net_worth_snapshot()
    return {"status": "deleted", "id": acc_id}

@app.get("/guide.html", response_class=HTMLResponse)
@app.get("/guide", response_class=HTMLResponse)
def guide_view():
    return HTMLResponse(content=GUIDE_HTML)

@app.get("/architecture.html", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
@app.get("/architecture", response_class=HTMLResponse)
def architecture_view():
    return HTMLResponse(content=ARCHITECTURE_HTML)

@app.get("/api/llm/status")
def get_llm_status():
    from fiduciary.agent.llm_client import LLMClient
    client = LLMClient()
    return client.get_status()

@app.post("/api/llm/provider")
def set_llm_provider(req: LLMProviderRequest):
    from fiduciary.agent.llm_client import (
        LLMClient,
        ensure_gateway_running,
        set_runtime_provider,
    )
    if req.provider not in ("auto", "local", "gemini", "gateway"):
        raise HTTPException(status_code=400, detail="Invalid provider")
    if req.provider == "gateway":
        ensure_gateway_running()
    set_runtime_provider(req.provider)
    client = LLMClient()
    return client.get_status()

@app.get("/api/watchdog")
def get_watchdog_audit():
    init_db()
    watchdog = FinancialWatchdog()
    return watchdog.run_full_audit()

@app.get("/api/tax/audit")
def get_tax_audit(income: Optional[float] = Query(default=None)):
    init_db()
    profiler = TransactionProfiler()
    profile = profiler.profile_finances()
    if not income:
        sal = profile.get("inferred_tax_profile", {}).get("monthly_net_salary_signal", 0.0)
        income = sal * 12 if sal > 0 else 60000.0
    liquid_cash = profile.get("gbp_balance", 0.0)
    return UKTaxOptimizer.full_tax_wealth_audit(gross_income=income, liquid_cash=liquid_cash)

@app.get("/api/sweep")
def get_sweep_plan():
    init_db()
    engine = SmartAutomationEngine()
    sweeper = engine.audit_sweeping_potential()
    standing_order = engine.generate_standing_order_plan()
    return {
        "sweeper": sweeper,
        "standing_order": standing_order
    }

@app.post("/api/cancel-template")
def get_cancel_template(req: CancelLetterRequest):
    engine = SmartAutomationEngine()
    return engine.generate_cancellation_letter(
        service_name=req.service_name,
        monthly_cost=req.monthly_cost,
        account_reference=req.account_reference
    )

@app.post("/api/copilot/chat")
def copilot_chat(req: CopilotQueryRequest):
    init_db()
    copilot = AICopilotEngine()
    answer = copilot.process_query(req.query)
    status = copilot.get_provider_status()
    return {
        "answer": answer,
        "mode": status["mode"],
        "badge": status["privacy_badge"]
    }

@app.get("/api/copilot/history")
def copilot_history(limit: int = 50):
    init_db()
    messages = get_chat_history(limit=limit)
    return {"messages": messages}

@app.post("/api/copilot/clear")
def copilot_clear():
    init_db()
    clear_chat_history()
    return {"status": "cleared"}

@app.get("/api/transactions")
def get_transactions(
    days: Optional[int] = None,
    account: Optional[str] = None,
    limit: Optional[int] = 50,
    search: Optional[str] = None,
    category: Optional[str] = None
):
    init_db()
    from fiduciary.storage.db import get_transaction_analytics
    txs = get_recent_transactions(days=days, account_id=account, limit=limit, search=search, category=category)
    analytics = get_transaction_analytics(days=days or 30)
    return {
        "transactions": txs,
        "analytics": analytics
    }

@app.get("/api/spending")
def get_spending_api(query: Optional[str] = None, days: Optional[int] = None, limit: int = 20):
    init_db()
    from fiduciary.analysis.spending import SpendingInsightEngine
    if query:
        return SpendingInsightEngine.query_spending(query_str=query, days=days, limit=limit)
    return {
        "velocity": SpendingInsightEngine.get_spending_velocity(),
        "micro_expenses": SpendingInsightEngine.get_micro_expense_analysis(threshold=10.0, days=30)
    }

@app.get("/api/profile/intelligence")
def get_customer_profile_api():
    init_db()
    from fiduciary.analysis.customer_profile import CustomerProfileEngine
    return CustomerProfileEngine.generate_profile()

class CreditScoresRequest(BaseModel):
    experian: Optional[int] = None
    equifax: Optional[int] = None
    transunion: Optional[int] = None
    electoral_roll: Optional[bool] = None

@app.get("/api/credit/audit")
def get_credit_audit_api():
    init_db()
    from fiduciary.analysis.credit_affordability import CreditAffordabilityEngine
    return CreditAffordabilityEngine.run_full_audit()

@app.post("/api/credit/scores")
def save_credit_scores_api(req: CreditScoresRequest):
    from fiduciary.storage.db import save_credit_bureau_scores
    return save_credit_bureau_scores(req.experian, req.equifax, req.transunion, req.electoral_roll)

@app.post("/api/sync/wise")
def sync_wise():
    init_db()
    client = WiseClient()
    res = client.sync_to_db()
    return res

@app.post("/api/sync/truelayer")
def sync_truelayer():
    init_db()
    from fiduciary.connectors.truelayer import TrueLayerClient
    client = TrueLayerClient()
    res = client.sync_latest()
    return res

@app.post("/api/sync/all")
def sync_all_accounts():
    init_db()
    results = {}
    # 1. Sync Wise
    try:
        wise_client = WiseClient()
        results["wise"] = wise_client.sync_to_db()
    except Exception as e:
        results["wise"] = {"status": "error", "error": str(e)}

    # 2. Sync TrueLayer (Revolut, etc.)
    try:
        from fiduciary.connectors.truelayer import TrueLayerClient
        tl_client = TrueLayerClient()
        results["truelayer"] = tl_client.sync_latest()
    except Exception as e:
        results["truelayer"] = {"status": "error", "error": str(e)}

    return results

@app.get("/api/truelayer/status")
def get_truelayer_status():
    from fiduciary.connectors.truelayer import TrueLayerClient
    client = TrueLayerClient()
    return client.get_connection_status()

@app.post("/api/advisor/live")
def get_live_ai_briefing():
    init_db()
    evaluator = FinancialEvaluator()
    state = evaluator.evaluate_financial_state()
    profiler = TransactionProfiler()
    profile = profiler.profile_finances()
    from fiduciary.agent.ai_advisor import AIFiduciaryAdvisor
    ai = AIFiduciaryAdvisor()
    briefing = ai.generate_live_briefing(state, profile)
    return {"briefing": briefing}

@app.get("/api/truelayer/auth-url")
def get_truelayer_auth_url():
    from fiduciary.connectors.truelayer import TrueLayerClient
    client = TrueLayerClient()
    if not client.is_configured():
        return {
            "error": "TrueLayer credentials not configured. Please add TRUELAYER_CLIENT_ID and TRUELAYER_CLIENT_SECRET to .env"
        }
    return {"auth_url": client.get_auth_url()}

@app.get("/truelayer/callback")
def truelayer_callback(code: str):
    from fastapi.responses import RedirectResponse

    from fiduciary.connectors.truelayer import TrueLayerClient
    client = TrueLayerClient()
    token_data = client.exchange_code(code)
    access_token = token_data.get("access_token")
    if access_token:
        client.sync_accounts(access_token)
    return RedirectResponse(url="/?synced=truelayer")

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    init_db()
    file_bytes = await file.read()
    filename_lower = file.filename.lower()

    if filename_lower.endswith(".pdf"):
        from fiduciary.connectors.pdf_importer import PDFStatementParser
        parser = PDFStatementParser()
        try:
            return parser.parse_pdf(file.filename, file_bytes)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        contents = file_bytes.decode("utf-8", errors="ignore")
        return detect_bank_and_parse(file.filename, contents)

@app.get("/api/traces")
def get_traces_api(limit: int = 25):
    init_db()
    from fiduciary.observability.tracer import get_observability_metrics, get_recent_traces
    return {
        "traces": get_recent_traces(limit=limit),
        "metrics": get_observability_metrics()
    }

@app.post("/api/traces/clear")
def clear_traces_api():
    init_db()
    from fiduciary.observability.tracer import clear_all_traces
    clear_all_traces()
    return {"status": "cleared"}

@app.get("/api/statement-batches")
def get_statement_batches_api(limit: int = 20):
    init_db()
    from fiduciary.storage.db import get_statement_batches
    return {"batches": get_statement_batches(limit=limit)}

@app.post("/api/traces/{trace_id}/judge")
def judge_trace_api(trace_id: str, model: Optional[str] = None):
    init_db()
    from fiduciary.observability.judge import LLMJudge
    judge = LLMJudge(default_model=model)
    if model:
        return judge.evaluate_trace(trace_id, judge_model=model)
    return judge.evaluate_trace(trace_id)

@app.post("/api/traces/judge-latest")
def judge_latest_trace_api(model: Optional[str] = None):
    init_db()
    from fiduciary.observability.judge import LLMJudge
    judge = LLMJudge(default_model=model)
    if model:
        res = judge.evaluate_latest_trace(judge_model=model)
    else:
        res = judge.evaluate_latest_trace()
    return res or {"error": "No traces available to evaluate"}

@app.get("/api/tools")
def get_tools_api():
    from fiduciary.agent.web_tools import get_available_tools_catalog
    return {"tools": get_available_tools_catalog()}



