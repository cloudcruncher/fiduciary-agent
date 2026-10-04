import argparse
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from fiduciary.agent.advisor import FiduciaryAdvisor
from fiduciary.agent.ai_advisor import AIFiduciaryAdvisor
from fiduciary.agent.automation import SmartAutomationEngine
from fiduciary.agent.copilot import AICopilotEngine
from fiduciary.agent.scout import MarketScout
from fiduciary.analysis.evaluator import FinancialEvaluator
from fiduciary.analysis.profiler import TransactionProfiler
from fiduciary.analysis.tax_optimizer import UKTaxOptimizer
from fiduciary.analysis.watchdog import FinancialWatchdog
from fiduciary.config import PORT
from fiduciary.connectors.truelayer import TrueLayerClient
from fiduciary.connectors.wise import WiseClient
from fiduciary.storage.db import (
    delete_account,
    get_net_worth_breakdown,
    get_recent_transactions,
    get_transaction_analytics,
    init_db,
    save_net_worth_snapshot,
    upsert_custom_asset,
)

console = Console()

def clear_database():
    from fiduciary.storage.db import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM transactions")
    c.execute("DELETE FROM accounts")
    c.execute("DELETE FROM institutions")
    conn.commit()
    conn.close()

def cmd_sync(args):
    """Sync live bank data from Wise and TrueLayer (Revolut, etc.)."""
    init_db()
    if getattr(args, "clean", False):
        clear_database()
        console.print("[dim]Database wiped.[/dim]")

    console.print("[green]🔗 Syncing live accounts...[/green]")
    # 1. Sync Wise
    try:
        wise_client = WiseClient(api_token=getattr(args, "token", None))
        res_w = wise_client.sync_to_db()
        console.print(f"[bold green]✓ Synced {len(res_w['accounts_synced'])} live Wise accounts and {res_w['transactions_count']} transactions.[/bold green]")
    except Exception as e:
        console.print(f"[bold yellow]Wise sync:[/bold yellow] {e}")

    # 2. Sync TrueLayer (Revolut, etc.)
    tl_client = TrueLayerClient()
    if tl_client.is_configured():
        tl_status = tl_client.get_connection_status()
        if tl_status.get("connected"):
            console.print("[cyan]🔄 Syncing Open Banking accounts (Revolut, etc.)...[/cyan]")
            res_tl = tl_client.sync_latest()
            if res_tl.get("status") == "success":
                console.print(f"[bold green]✓ Synced {len(res_tl['accounts_synced'])} Open Banking accounts and {res_tl['total_transactions']} transactions.[/bold green]")
            else:
                console.print(f"[bold yellow]Open Banking notice:[/bold yellow] {res_tl.get('error') or res_tl.get('message')}")
        else:
            console.print("[dim]💡 Tip: Run './f connect' to link Revolut / UK Open Banking for auto-syncing.[/dim]")

def cmd_connect(args):
    """Generate TrueLayer Open Banking connection URL for UK banks."""
    client = TrueLayerClient()
    if not client.is_configured():
        console.print("[red]❌ TrueLayer credentials not set in .env![/red]")
        console.print("\nTo connect Revolut, Chase, HSBC, NatWest, Lloyds, or Zopa:")
        console.print("1. Set TRUELAYER_CLIENT_ID and TRUELAYER_CLIENT_SECRET in `.env`")
        console.print("2. Set TRUELAYER_USE_SANDBOX=false (for live) or true (for sandbox)\n")
        sys.exit(1)

    auth_url = client.get_auth_url()
    console.print(Panel.fit(
        f"[bold green]🏦 CONNECT REAL BANK VIA TRUELAYER[/bold green]\n\n"
        f"Open this URL to authenticate with your bank app:\n\n"
        f"[cyan]{auth_url}[/cyan]\n\n"
        f"[dim]Supports Revolut, Chase UK, HSBC, NatWest, Lloyds, Zopa, etc.[/dim]",
        border_style="green"
    ))


def cmd_transactions(args):
    """View real transactions with filters by bank, search keyword, category, and limit."""
    init_db()
    days = None if getattr(args, "all", False) else getattr(args, "days", None)
    account = getattr(args, "account", None)
    limit = getattr(args, "limit", 50)
    search = getattr(args, "search", None)
    category = getattr(args, "category", None)

    txs = get_recent_transactions(days=days, account_id=account, limit=limit, search=search, category=category)

    filter_desc = []
    if account:
        filter_desc.append(f"Bank: {account.upper()}")
    if category:
        filter_desc.append(f"Category: '{category}'")
    if search:
        filter_desc.append(f"Keyword: '{search}'")
    if days:
        filter_desc.append(f"Last {days} Days")
    else:
        filter_desc.append(f"Limit {limit}")

    title_str = "Transactions (" + ", ".join(filter_desc) + ")"
    console.print(Panel.fit(
        f"[bold cyan]💳 {title_str.upper()}[/bold cyan]",
        border_style="cyan"
    ))

    t = Table(title=f"Transactions ({len(txs)} records shown)", border_style="blue")
    t.add_column("Date", style="cyan", no_wrap=True)
    t.add_column("Bank / Account", style="dim", no_wrap=True)
    t.add_column("Counterparty / Merchant", style="white")
    t.add_column("Category", style="yellow")
    t.add_column("Amount", justify="right", style="bold")

    for tx in txs:
        amt = float(tx.get("amount", 0.0))
        amt_str = f"+£{amt:,.2f}" if amt > 0 else f"-£{abs(amt):,.2f}"
        style_color = "green bold" if amt > 0 else ("white" if abs(amt) < 30 else "yellow bold")
        merchant = (tx.get("counterparty_name") or tx.get("description") or "")[:35]
        if (tx.get("status") or "").lower() == "pending":
            merchant += " [yellow bold](Pending)[/yellow bold]"
        t.add_row(
            tx.get("booking_date", "")[:10],
            (tx.get("institution_name") or tx.get("account_name") or tx.get("account_id") or "")[:20],
            merchant,
            tx.get("category", "General"),
            f"[{style_color}]{amt_str}[/{style_color}]"
        )
    console.print(t)

def cmd_spending(args):
    """Query deterministic spending by category, velocity shifts, and micro-expense leakage."""
    init_db()
    from fiduciary.analysis.spending import SpendingInsightEngine
    query = getattr(args, "query", None)
    days = getattr(args, "days", None)
    limit = getattr(args, "limit", 20)

    if query:
        res = SpendingInsightEngine.query_spending(query_str=query, days=days, limit=limit)
        console.print(Panel.fit(
            f"[bold cyan]🔍 SPENDING INSIGHT: '{query.upper()}'[/bold cyan]\n"
            f"[bold white]{res['narrative']}[/bold white]",
            border_style="cyan"
        ))

        if res.get("top_venues"):
            vt = Table(title="Top Venues in this Category", border_style="magenta")
            vt.add_column("Venue / Merchant", style="bold white")
            vt.add_column("Total Spent", style="green bold", justify="right")
            vt.add_column("Visits", style="cyan", justify="center")
            for v in res["top_venues"]:
                vt.add_row(v["merchant"], f"£{v['total']:,.2f}", str(v["count"]))
            console.print(vt)
            console.print("")

        items = res.get("itemized_transactions", [])
        if items:
            t = Table(title=f"Matching Itemised Records ({len(items)} shown)", border_style="blue")
            t.add_column("Date", style="cyan", no_wrap=True)
            t.add_column("Bank", style="dim", no_wrap=True)
            t.add_column("Merchant", style="white")
            t.add_column("Category", style="yellow")
            t.add_column("Amount", justify="right", style="bold")
            for tx in items:
                amt = float(tx.get("amount", 0.0))
                amt_str = f"-£{abs(amt):,.2f}"
                t.add_row(
                    tx.get("booking_date", "")[:10],
                    (tx.get("institution_name") or tx.get("account_name") or "")[:15],
                    (tx.get("counterparty_name") or tx.get("description") or "")[:35],
                    tx.get("category", "General"),
                    amt_str
                )
            console.print(t)
        return

    # If no query specified, show velocity shifts, micro expenses, and all categories
    vel = SpendingInsightEngine.get_spending_velocity()
    micro = SpendingInsightEngine.get_micro_expense_analysis(threshold=10.0, days=30)
    analytics = get_transaction_analytics(days=30)

    console.print(Panel.fit(
        "[bold cyan]📊 SPENDING VELOCITY & CASH LEAKAGE INSIGHT ENGINE[/bold cyan]",
        border_style="cyan"
    ))

    # Velocity panel
    v_style = "bold red" if vel["status"] == "ACCELERATING" else ("bold green" if vel["status"] == "DECELERATING" else "bold yellow")
    console.print(Panel(
        f"[bold]7-Day Spending Status:[/bold] [{v_style}]{vel['status']} ({vel['velocity_shift_pct']:+.1f}% vs 30d baseline)[/{v_style}]\n"
        f"• Actual Trailing 7-Day Living Outflow: £{vel['trailing_7d_spend']:,.2f}\n"
        f"• Normalized Expected Weekly Baseline: £{vel['normalized_weekly_baseline']:,.2f}\n"
        f"• Micro-Expense Bleed (<£10 purchases): £{micro['total_micro_spend_gbp']:,.2f} across {micro['micro_transaction_count']} transactions ({micro['pct_of_living_spend']}% of living spend)",
        title="Weekly Outflow Velocity & Bleed",
        border_style="blue"
    ))

    # Categories Table
    categories = analytics.get("categories", {})
    if categories:
        ct = Table(title="30-Day Living Spend by Category", border_style="yellow")
        ct.add_column("Category", style="bold white")
        ct.add_column("Total Spent", style="green bold", justify="right")
        ct.add_column("% of Living Spend", style="cyan", justify="right")
        ct.add_column("Transactions", style="dim", justify="right")
        for cat_name, c_data in categories.items():
            ct.add_row(cat_name, f"£{c_data['total']:,.2f}", f"{c_data['pct_of_outflow']}%", str(c_data['count']))
        console.print(ct)

def cmd_profile(args):
    """Profile real transactions, Financial DNA, Health Score, and Action Playbook Cards."""
    init_db()
    from fiduciary.analysis.customer_profile import CustomerProfileEngine
    cust_prof = CustomerProfileEngine.generate_profile()
    hs = cust_prof["health_score"]
    dna = cust_prof["financial_dna"]
    b50 = cust_prof["budget_50_30_20"]
    actions = cust_prof.get("action_cards", [])

    profiler = TransactionProfiler()
    profile = profiler.profile_finances()
    tx_summary = profile.get("transaction_30d_summary", {})

    console.print(Panel.fit(
        "[bold cyan]🧬 INTELLIGENT CUSTOMER PROFILE & FINANCIAL DNA[/bold cyan]",
        border_style="cyan"
    ))

    # Health Score & DNA
    h_color = "green" if hs["total"] >= 75 else ("yellow" if hs["total"] >= 60 else "red")
    console.print(Panel(
        f"[bold {h_color}]Financial Health Score: {hs['total']:.1f} / 100 [{hs['grade']}][/bold {h_color}]\n"
        f"  • Runway & Reserve: {hs['runway_score']:.1f}/30 pts   • Cash Drag Efficiency: {hs['drag_score']:.1f}/25 pts\n"
        f"  • 50/30/20 Budget:   {hs['budget_score']:.1f}/25 pts   • Commitment Hygiene:  {hs['hygiene_score']:.1f}/20 pts\n\n"
        f"[bold cyan]Financial DNA Archetype:[/bold cyan] [bold white]'{dna['archetype']}'[/bold white]\n"
        f"[dim]{dna['description']}[/dim]\n"
        f"Cognitive Friction Level: [bold yellow]{dna['cognitive_friction_level']}[/bold yellow] ({dna['manual_topup_count_30d']} manual top-ups/mo)\n\n"
        f"[bold cyan]50 / 30 / 20 Budget Split (30-Day):[/bold cyan]\n"
        f"  • Fixed Needs: £{b50['needs_total_gbp']:,.2f} ([bold]{b50['needs_pct']}%[/bold] vs 50% target)\n"
        f"  • Discretionary Wants: £{b50['wants_total_gbp']:,.2f} ([bold]{b50['wants_pct']}%[/bold] vs 30% target)",
        title="[bold]Financial Health & Archetype Diagnosis[/bold]",
        border_style="cyan"
    ))

    # Action Playbook Cards
    if actions:
        console.print("\n[bold cyan]🎯 PRIORITIZED INSIGHT-TO-ACTION PLAYBOOK CARDS:[/bold cyan]\n")
        for idx, a in enumerate(actions, 1):
            p_color = "red bold" if a["priority"] == "HIGH" else "yellow bold"
            gain_text = f"+£{a['annual_gain_gbp']:,.2f}/yr" if a["annual_gain_gbp"] > 0 else "Mental Friction Reduction"
            steps = "\n".join([f"    • {s}" for s in a.get("action_steps", [])])
            console.print(Panel(
                f"[bold white]{a['summary']}[/bold white]\n\n"
                f"[yellow]Action Steps:[/yellow]\n{steps}",
                title=f"#{idx} [{p_color}][{a['priority']}][/] [bold]{a['title']}[/bold] ([bold green]{gain_text}[/bold green])",
                border_style="green" if a["priority"] == "HIGH" else "blue"
            ))

    # Runway Alert Banner
    runway = profile.get("liquid_runway_days", 1.5)
    runway_color = "red" if runway < 7.0 else ("yellow" if runway < 30.0 else "green")
    console.print(Panel(
        f"[bold {runway_color}]⚠️ LIQUID RUNWAY: {runway:.1f} DAYS OF CASH ON HAND[/bold {runway_color}]\n"
        f"Liquid Balance: £{profile['gbp_balance']:,.2f}  |  Daily Living Burn: £{profile['daily_burn_rate']:,.2f}/day\n"
        f"[dim]{profile.get('funding_behavior', '')}[/dim]",
        border_style=runway_color,
        title="[bold]Liquidity Stress Gauge[/bold]"
    ))

    tax_info = profile["inferred_tax_profile"]
    t = Table(title="Core Financial & Cash Flow Profile", border_style="blue")
    t.add_column("Attribute", style="cyan")
    t.add_column("Value", style="bold white")
    t.add_column("Fiduciary Significance", style="dim")

    t.add_row(
        "Liquid Cash Balance",
        f"£{profile['gbp_balance']:,.2f}",
        "Available immediately in current accounts"
    )
    t.add_row(
        "Verified 30-Day Living Burn",
        f"£{profile['monthly_burn_estimate']:,.2f}/mo",
        f"£{profile['daily_burn_rate']:,.2f}/day actual living expenses"
    )
    t.add_row(
        "3-Month Emergency Target",
        f"£{profile['emergency_buffer_target']:,.2f}",
        "Calibrated safety buffer (keep in 4.87% Flexible Cash ISA)"
    )
    t.add_row(
        "6-Month Resilience Target",
        f"£{profile.get('six_month_buffer_target', 0.0):,.2f}",
        "Full economic resilience reserve"
    )
    t.add_row(
        "Card Spend (0% Cashback Drag)",
        f"£{tx_summary.get('card_spend_total', 0.0):,.2f}/mo",
        f"Switching to Chase 1% captures +£{profile.get('annual_cashback_potential', 0.0):,.2f}/yr"
    )
    t.add_row(
        "Inferred UK Tax Bracket",
        tax_info["tax_band"],
        f"Marginal tax rate: {int(tax_info['marginal_tax_rate']*100)}%"
    )
    t.add_row(
        "Personal Savings Allowance (PSA)",
        f"£{tax_info['personal_savings_allowance_gbp']:,.2f}/year",
        "Interest beyond this taxed at marginal rate"
    )
    t.add_row(
        "Switch-Eligible Direct Debits",
        f"{profile['switch_eligible_direct_debits_count']} detected",
        "Eligible for £175-£200 bank switch bounties"
    )
    console.print(t)

    # Spending Categories Table
    categories = tx_summary.get("categories", {})
    if categories:
        console.print("\n[bold yellow]30-Day Spending by Category:[/bold yellow]")
        ct = Table(border_style="yellow")
        ct.add_column("Category", style="bold white")
        ct.add_column("Total Spent", style="green", justify="right")
        ct.add_column("% of Outflow", style="cyan", justify="right")
        ct.add_column("Transactions", style="dim", justify="right")
        for cat_name, c_data in categories.items():
            ct.add_row(cat_name, f"£{c_data['total']:,.2f}", f"{c_data['pct_of_outflow']}%", str(c_data['count']))
        console.print(ct)

    # Top Merchants Table
    top_merchants = tx_summary.get("top_merchants", [])
    if top_merchants:
        console.print("\n[bold magenta]Top Merchants & Frequent Venues (Last 30 Days):[/bold magenta]")
        mt = Table(border_style="magenta")
        mt.add_column("Merchant / Venue", style="bold white")
        mt.add_column("Total Spent", style="green", justify="right")
        mt.add_column("Visits", style="cyan", justify="center")
        mt.add_column("Category", style="dim")
        for m in top_merchants:
            mt.add_row(m["name"], f"£{m['total']:,.2f}", str(m["count"]), m["category"])
        console.print(mt)

    # Subscriptions Table
    subscriptions = tx_summary.get("subscriptions", [])
    if subscriptions:
        console.print("\n[bold cyan]Detected Software & Subscriptions:[/bold cyan]")
        st = Table(border_style="cyan")
        st.add_column("Subscription", style="bold white")
        st.add_column("Monthly Cost", style="green", justify="right")
        st.add_column("Last Billed", style="dim")
        for s in subscriptions:
            st.add_row(s["name"], f"£{s['amount']:,.2f}", s["date"])
        console.print(st)

def cmd_scout(args):
    """Scout live UK rates adjusted for personal tax bracket."""
    init_db()
    profiler = TransactionProfiler()
    profile = profiler.profile_finances()
    scout = MarketScout()
    quotes = scout.scout_market(profile)

    console.print(Panel.fit(
        "[bold green]🌐 LIVE UK MARKET BENCHMARKS & AFTER-TAX YIELDS[/bold green]",
        border_style="green"
    ))

    marginal_tax_pct = int(profile["inferred_tax_profile"]["marginal_tax_rate"] * 100)

    # ISAs
    isa_table = Table(title="1. Top Easy-Access Cash ISAs (100% Tax-Free)", border_style="cyan")
    isa_table.add_column("Provider", style="bold white")
    isa_table.add_column("Account", style="white")
    isa_table.add_column("AER Yield", justify="right", style="green bold")
    isa_table.add_column("Flexibility", style="yellow")
    isa_table.add_column("Key Terms", style="dim")

    for isa in quotes["cash_isas"]:
        isa_table.add_row(isa["provider"], isa["product"], f"{isa['gross_aer']:.2f}%", "Flexible" if isa["flexible"] else "Standard", isa["notes"])
    console.print(isa_table)
    console.print("")

    # Taxable
    tax_table = Table(title=f"2. Taxable Savings (Effective Yield After {marginal_tax_pct}% Tax)", border_style="blue")
    tax_table.add_column("Provider", style="bold white")
    tax_table.add_column("Gross AER", justify="right", style="white")
    tax_table.add_column(f"Net AER (After {marginal_tax_pct}% Tax)", justify="right", style="bold yellow")
    tax_table.add_column("Access / Notes", style="dim")

    for ts in quotes["taxable_savings"]:
        tax_table.add_row(ts["provider"], f"{ts['gross_aer']:.2f}%", f"{ts['net_aer_after_tax']:.2f}%", ts.get("notes", ts["access"]))
    console.print(tax_table)
    console.print("")

    # Switches
    sw_table = Table(title="3. Bank Switch Bonuses (Bribes)", border_style="magenta")
    sw_table.add_column("Bank", style="bold white")
    sw_table.add_column("Bounty", justify="right", style="green bold")
    sw_table.add_column("Required DDs", justify="center")
    sw_table.add_column("Status", style="bold")
    sw_table.add_column("Perks & Terms", style="dim")

    for sw in quotes["bank_switches"]:
        status_text = "[green]✓ Qualified[/green]" if sw["eligible"] else f"[red]✗ Needs {sw['required_direct_debits']} DDs[/red]"
        sw_table.add_row(sw["bank"], f"+£{sw['bonus_cash']:,.2f}", str(sw["required_direct_debits"]), status_text, sw["perks"])
    console.print(sw_table)

    # Cashback
    cb_table = Table(title="4. Everyday Debit Card Cashback (0% Risk)", border_style="yellow")
    cb_table.add_column("Provider", style="bold white")
    cb_table.add_column("Product", style="white")
    cb_table.add_column("Cashback Rate", justify="right", style="green bold")
    cb_table.add_column("Linked Saver", style="cyan")
    cb_table.add_column("Key Terms", style="dim")

    for cb in quotes.get("card_cashback_deals", []):
        cb_table.add_row(cb["provider"], cb["product"], cb["cashback_rate"], cb["saver_perk"], cb["notes"])
    console.print("")
    console.print(cb_table)

def cmd_audit(args):
    """Run fiduciary synthesis and AI strategy memo."""
    init_db()
    evaluator = FinancialEvaluator()
    state = evaluator.evaluate_financial_state()
    profiler = TransactionProfiler()
    profile = profiler.profile_finances()
    advisor = FiduciaryAdvisor()
    recommendations = advisor.generate_recommendations(state, profile)

    console.print(Panel.fit(
        "[bold cyan]🛡️ REAL FIDUCIARY CAPITAL ALLOCATION AUDIT[/bold cyan]",
        border_style="cyan"
    ))

    # Accounts Table
    table = Table(title="Your Real Connected Holdings", border_style="blue")
    table.add_column("Institution", style="cyan", no_wrap=True)
    table.add_column("Account Name", style="white")
    table.add_column("Type", style="dim")
    table.add_column("Balance", justify="right", style="green bold")

    for acc in state["accounts_detail"]:
        table.add_row(
            acc.get("institution_name", "Unknown"),
            acc.get("name", "Account"),
            acc.get("account_type", "checking").capitalize(),
            f"{acc.get('current_balance', 0.0):,.2f} {acc.get('currency', 'GBP')}"
        )
    console.print(table)

    runway = profile.get("liquid_runway_days", 1.5)
    runway_color = "red" if runway < 7.0 else "yellow"

    metrics_text = Text()
    metrics_text.append(f"• Total Liquid Capital: £{state['gbp_total_balance']:,.2f}\n", style="bold white")
    metrics_text.append(f"• Verified Daily Living Burn: £{profile['daily_burn_rate']:,.2f}/day (Monthly: £{profile['monthly_burn_estimate']:,.2f}/mo)\n", style="yellow")
    metrics_text.append(f"• Liquid Runway: {runway:.1f} DAYS OF CASH ON HAND\n", style=f"bold {runway_color}")
    metrics_text.append(f"• Calibrated 3-Month Emergency Target: £{profile['emergency_buffer_target']:,.2f}\n", style="cyan")
    metrics_text.append(f"• Debit Card Spend (0% Cashback): £{profile.get('transaction_30d_summary', {}).get('card_spend_total', 0.0):,.2f}/mo (Chase 1% Gain: +£{profile.get('annual_cashback_potential', 0.0):,.2f}/yr)\n", style="bold green")

    console.print(Panel(metrics_text, title="📊 30-Day Fiduciary Diagnosis Summary", border_style="yellow"))

    if recommendations:
        console.print("\n[bold cyan]🎯 FIDUCIARY ACTION PLAN:[/bold cyan]\n")
        for i, rec in enumerate(recommendations, 1):
            color = "green" if rec["priority"] == "HIGH" else "blue"
            gain_str = f"+£{rec['annual_gain_gbp']:,.2f}/yr" if rec["annual_gain_gbp"] > 0 else "Risk Reduction"
            content = (
                f"[bold]{rec['summary']}[/bold]\n\n"
                f"[yellow]Action Steps:[/yellow]\n" +
                "\n".join([f"  • {s}" for s in rec['steps']])
            )
            console.print(Panel(
                content,
                title=f"#{i} [{color} bold][{rec['category']}] {rec['title']} ({gain_str})[/{color} bold]",
                border_style=color
            ))

    # Run AI Advisor Memo
    ai_advisor = AIFiduciaryAdvisor()
    if ai_advisor.is_configured():
        console.print("\n[bold magenta]🤖 GENERATING LIVE AI FIDUCIARY STRATEGY MEMO...[/bold magenta]\n")
        briefing = ai_advisor.generate_live_briefing(state, profile)
        console.print(Panel(
            Markdown(briefing),
            title="[bold magenta]🤖 AI FIDUCIARY STRATEGY MEMO & APPLICATION LINKS[/bold magenta]",
            border_style="magenta"
        ))
    else:
        console.print("\n[dim]💡 Add GEMINI_API_KEY to .env to unlock the AI Strategy Memo.[/dim]\n")

def cmd_ui(args):
    """Launch clean local web dashboard with phone mobile access & QR code."""
    import io

    import qrcode
    import uvicorn

    from fiduciary.agent.llm_client import ensure_gateway_running
    from fiduciary.config import LLM_PROVIDER, PORT, get_local_ip

    init_db()
    if LLM_PROVIDER == "gateway":
        ensure_gateway_running()

    host = getattr(args, "host", None) or "0.0.0.0"
    port = getattr(args, "port", None) or PORT
    local_ip = get_local_ip()
    mobile_url = f"http://{local_ip}:{port}"
    laptop_url = f"http://localhost:{port}"

    # Generate terminal QR code for phone camera scanning
    qr_str = ""
    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(mobile_url)
        qr.make(fit=True)
        f = io.StringIO()
        qr.print_ascii(out=f, invert=True)
        qr_str = f.getvalue()
    except Exception:
        pass

    msg = (
        f"[bold green]🌐 LOCAL FIDUCIARY DASHBOARD ACTIVE[/bold green]\n\n"
        f"💻 [bold white]Laptop Browser:[/bold white] [bold cyan]{laptop_url}[/bold cyan]\n"
        f"📱 [bold white]Phone / Mobile Browser:[/bold white] [bold yellow]{mobile_url}[/bold yellow]\n\n"
        f"[bold cyan]Scan with phone camera to connect & link banking apps:[/bold cyan]\n"
        f"{qr_str}\n"
        f"[dim]Tip: On phone Safari/Chrome, tap 'Share' -> 'Add to Home Screen' to install app.[/dim]\n"
        f"[dim]Press Ctrl+C to stop the server[/dim]"
    )

    console.print(Panel.fit(msg, border_style="green"))
    uvicorn.run("fiduciary.web.app:app", host=host, port=port, log_level="warning")

def cmd_gateway(args):
    """Start or inspect the Enterprise AI Gateway (LiteLLM Proxy)."""
    import shutil
    import subprocess

    from fiduciary.agent.llm_client import LLMClient

    client = LLMClient()
    status = client.get_status()
    if status.get("gateway_server_online") or getattr(args, "status", False):
        if status.get("gateway_server_online"):
            console.print(Panel.fit(
                f"[bold green]🔵 AI GATEWAY IS ONLINE & ACTIVE[/bold green]\n\n"
                f"Endpoint: [bold cyan]{client.gateway_url}[/bold cyan]\n"
                f"Active Model: [bold white]{status.get('gateway_model')}[/bold white]\n"
                f"Privacy: [bold green]100% Private (Metal GPU via Ollama)[/bold green]\n"
                f"Config File: [dim]litellm_config.yaml[/dim]",
                border_style="blue"
            ))
        else:
            console.print(Panel.fit(
                f"[bold yellow]⚠️ AI GATEWAY IS OFFLINE[/bold yellow]\n\n"
                f"Target URL: [bold cyan]{client.gateway_url or 'http://localhost:4000/v1'}[/bold cyan]\n"
                f"Run [bold white]./f gateway[/bold white] to launch the LiteLLM proxy.",
                border_style="yellow"
            ))
        return

    litellm_bin = shutil.which("litellm") or "litellm"
    port = str(getattr(args, "port", 4000))
    console.print(Panel.fit(
        f"[bold blue]🚀 STARTING LITELLM AI GATEWAY PROXY[/bold blue]\n\n"
        f"Binding: [bold cyan]http://127.0.0.1:{port}[/bold cyan]\n"
        f"Upstream: [bold green]Ollama (:11434 / Metal GPU)[/bold green]\n"
        f"Config: [dim]litellm_config.yaml[/dim]\n\n"
        f"[dim]Press Ctrl+C to stop the proxy[/dim]",
        border_style="blue"
    ))
    subprocess.run([
        litellm_bin,
        "--config", "litellm_config.yaml",
        "--port", port,
        "--host", "127.0.0.1"
    ])


def cmd_copilot(args):
    """Interact with the live Fiduciary Copilot."""
    init_db()
    from fiduciary.agent.llm_client import ensure_gateway_running
    from fiduciary.config import LLM_PROVIDER

    if LLM_PROVIDER == "gateway":
        ensure_gateway_running()

    use_react = getattr(args, "react", False)
    query = getattr(args, "query", None)

    if use_react and query:
        from fiduciary.agent.react_agent import ReActFiduciaryAgent
        agent = ReActFiduciaryAgent()
        console.print(f"[bold cyan]🔍 Autonomous ReAct Agent:[/bold cyan] {query}\n")
        with console.status("[bold green]Executing ReAct multi-step reasoning trajectory...[/bold green]"):
            result = agent.run(query)

        for s in result["steps"]:
            act = s.get("action", "")
            dur = s.get("duration_ms", 0)
            console.print(f"[bold yellow]Step {s['step']}:[/bold yellow] [bold]{act}[/bold] ({dur}ms)")
            if s.get("thought"):
                console.print(f"  [dim cyan]Thought:[/dim cyan] {s['thought']}")
            if s.get("observation"):
                obs_prev = s['observation'][:120] + ("..." if len(s['observation']) > 120 else "")
                console.print(f"  [dim green]Observation:[/dim green] {obs_prev}")

        console.print(Panel(Markdown(result["answer"]), title=f"🤖 Fiduciary ReAct Verdict ({result['total_duration_ms']:.0f}ms)", border_style="green"))
        return

    copilot = AICopilotEngine()
    if query:
        console.print(f"[bold cyan]User:[/bold cyan] {query}")
        console.print("[dim]Consulting fiduciary database...[/dim]")
        answer = copilot.process_query(query, use_react=use_react)
        console.print(Panel(Markdown(answer), title="🤖 Fiduciary Copilot", border_style="cyan"))
    else:
        console.print(Panel.fit(
            "[bold cyan]🤖 INTERACTIVE FIDUCIARY COPILOT[/bold cyan]\n"
            "Ask questions about your real cash runway, taxes, or affordability.\n"
            "[dim]Type 'exit' or 'quit' to end session.[/dim]",
            border_style="cyan"
        ))
        while True:
            try:
                user_input = console.input("[bold green]You > [/bold green]").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "q"]:
                    break
                console.print("[dim]Analyzing real accounts...[/dim]")
                ans = copilot.process_query(user_input, use_react=use_react)
                console.print(Panel(Markdown(ans), title="🤖 Fiduciary Copilot", border_style="cyan"))
            except (KeyboardInterrupt, EOFError):
                break


def cmd_rag(args):
    """Local semantic vector RAG search over statutory rules and documents."""
    init_db()
    from fiduciary.agent.vector_rag import get_vector_rag
    query = getattr(args, "query", None)
    if not query:
        console.print("[bold red]Please provide a query for vector search.[/bold red] Example: ./f rag '60 percent tax trap'")
        return

    rag = get_vector_rag()
    limit = getattr(args, "limit", 3) or 3
    results = rag.search(query=query, top_k=int(limit))
    console.print(f"[bold cyan]🔍 Local Semantic Vector RAG Search:[/bold cyan] '{query}'\n")
    if not results:
        console.print("[yellow]No relevant documents matched.[/yellow]")
        return

    for idx, r in enumerate(results, 1):
        console.print(Panel(
            f"[bold]{r['title']}[/bold] [dim]({r['category']})[/dim]  |  Relevance Score: [bold green]{r['score']:.4f}[/bold green]\n\n"
            f"{r['content']}",
            title=f"Match #{idx}: {r['id']}",
            border_style="cyan"
        ))

def cmd_watchdog(args):
    """Run financial watchdog for bills, price hikes, and duplicate charges."""
    init_db()
    watchdog = FinancialWatchdog()
    audit = watchdog.run_full_audit()

    console.print(Panel.fit(
        "[bold red]🚨 FINANCIAL WATCHDOG & RECURRING COMMITMENTS AUDIT[/bold red]",
        border_style="red"
    ))

    # Liquidity Warning
    shortfall = audit.get("liquidity_shortfall_alert")
    if shortfall:
        style_color = "red bold" if shortfall["level"] == "CRITICAL" else "yellow bold"
        console.print(Panel(
            f"[{style_color}]{shortfall['title']}[/{style_color}]\n\n{shortfall['message']}",
            border_style="red" if shortfall["level"] == "CRITICAL" else "yellow"
        ))

    # Price Hikes
    hikes = audit.get("price_hike_alerts", [])
    if hikes:
        ht = Table(title="🚨 Detected Subscription Price Hikes", border_style="red")
        ht.add_column("Merchant", style="bold white")
        ht.add_column("Previous", style="dim")
        ht.add_column("Latest", style="bold yellow")
        ht.add_column("Increase", style="bold red")
        ht.add_column("Detected Date", style="dim")
        for h in hikes:
            ht.add_row(
                h["merchant"],
                f"£{h['previous_amount']:.2f}",
                f"£{h['latest_amount']:.2f}",
                f"+£{h['increase_amount']:.2f} (+{h['percentage_increase']}%)",
                h["date_detected"]
            )
        console.print(ht)
        console.print("")

    # Duplicate charges
    dups = audit.get("duplicate_charge_alerts", [])
    if dups:
        dt = Table(title="⚠️ Suspicious Duplicate Charges (<48h)", border_style="yellow")
        dt.add_column("Merchant", style="bold white")
        dt.add_column("Amount", style="bold yellow")
        dt.add_column("Date 1", style="dim")
        dt.add_column("Date 2", style="dim")
        for d in dups:
            dt.add_row(d["merchant"], f"£{d['amount']:.2f}", d["date_1"], d["date_2"])
        console.print(dt)
        console.print("")

    # Upcoming Bills (Next 14 Days)
    bills_14 = audit.get("upcoming_bills_14d", [])
    bt = Table(title=f"📅 Recurring Bills Due in Next 14 Days ({len(bills_14)} due)", border_style="blue")
    bt.add_column("Due Date", style="cyan")
    bt.add_column("Merchant", style="bold white")
    bt.add_column("Category", style="dim")
    bt.add_column("Expected Amount", style="bold green", justify="right")
    bt.add_column("Days Away", justify="center")

    for b in bills_14:
        bt.add_row(
            b["next_due_date"],
            b["merchant"],
            b["category"],
            f"£{b['expected_amount']:.2f}",
            f"{b['days_away']} days"
        )
    console.print(bt)

def cmd_credit(args):
    """UK underwriter-style credit & affordability audit (offline, cash-flow based)."""
    from fiduciary.analysis.credit_affordability import CreditAffordabilityEngine
    from fiduciary.storage.db import save_credit_bureau_scores

    if any(v is not None for v in (args.experian, args.equifax, args.transunion, args.electoral_roll)):
        er = None if args.electoral_roll is None else args.electoral_roll == "yes"
        save_credit_bureau_scores(args.experian, args.equifax, args.transunion, er)
        console.print("[green]✓ Bureau scores saved locally.[/green]")

    a = CreditAffordabilityEngine.run_full_audit()
    cf = a["cash_flow_affordability"]
    color_map = {"emerald": "green", "blue": "blue", "amber": "yellow", "rose": "red"}
    rich_color = color_map.get(a.get("tier_badge_color"), "green")
    console.print(Panel(
        f"[bold {rich_color}]{a['borrowing_readiness_score']}/100 — {a['underwriter_tier']}[/bold {rich_color}]\n{a['tier_description']}",
        title="🏦 Borrowing Readiness (Underwriter View)", border_style=rich_color))

    t = Table(title="Cash-Flow Affordability", border_style="cyan")
    t.add_column("Metric")
    t.add_column("Value", justify="right")
    t.add_row("Net monthly income", f"£{cf['monthly_net_income']:,.2f}")
    t.add_row("Est. gross annual", f"£{cf['estimated_annual_gross']:,.0f}")
    t.add_row("Fixed needs (housing, bills, essentials)", f"£{cf['monthly_fixed_needs']:,.2f}")
    t.add_row("Contractual debt / BNPL", f"£{cf['monthly_committed_debt']:,.2f}")
    t.add_row("Uncommitted monthly income", f"£{cf['uncommitted_monthly_income_umi']:,.2f} ({cf['umi_surplus_pct']}%)")
    t.add_row("Debt-to-income", f"{cf['contractual_dti_pct']}%")
    console.print(t)

    m = a["mortgage_borrowing_capacity"]
    console.print(Panel(
        f"Max borrowing (4.5x gross less debt): [bold]£{m['net_maximum_borrowing_capacity']:,.0f}[/bold]\n"
        f"Repayment @ {m['indicative_rate_pct']}%: £{m['indicative_monthly_repayment']:,.2f}/mo  |  "
        f"Stress @ {m['stress_tested_rate_pct']}%: £{m['stress_tested_monthly_repayment']:,.2f}/mo",
        title="🏠 Mortgage Capacity (indicative)", border_style="blue"))

    f = a["underwriter_risk_flags"]
    console.print(Panel(
        f"BNPL: {f['bnpl_summary']}\n"
        f"Returned direct debits: {f['bounced_count']}\n"
        f"Overdraft reliance: {'Yes' if f['overdraft_reliance'] else 'No'}\n"
        f"Gambling (30d): £{f['gambling_spend_30d']:,.2f} — {f['gambling_risk']}\n"
        f"Electoral roll: {'Verified' if f['electoral_roll_verified'] else 'NOT registered'}",
        title="🚩 Underwriter Risk Flags", border_style="yellow"))

    r = a["emergency_runway_and_stress"]
    s = Table(title=f"Stress Tests (liquid cash £{r['liquid_cash_gbp']:,.2f})", border_style="magenta")
    s.add_column("Scenario")
    s.add_column("Result")
    sc = r["scenarios"]
    s.add_row(sc[0]["name"], f"{sc[0]['comfortable_months']} mo comfortable / {sc[0]['survival_months']} mo survival — {sc[0]['status']}")
    s.add_row(sc[1]["name"], f"£{sc[1]['remaining_cash']:,.2f} left ({sc[1]['remaining_runway_months']} mo)")
    s.add_row(sc[2]["name"], f"UMI £{sc[2]['new_umi']:,.2f}, DTI {sc[2]['new_dti_pct']}% — {'affordable' if sc[2]['is_affordable'] else 'strained'}")
    console.print(s)

    b = a["bureau_scores"]
    console.print(f"[dim]Bureau scores (self-reported): Experian {b['experian']} | Equifax {b['equifax']} | TransUnion {b['transunion']}[/dim]")
    console.print("\n[bold]Action playbook[/bold]")
    for c in a["action_playbook"]:
        console.print(f"  [{c['priority']}] [bold]{c['title']}[/bold] — {c['action']}")


def cmd_tax(args):
    """Run UK Tax & Wealth Optimization audit."""
    init_db()
    profiler = TransactionProfiler()
    profile = profiler.profile_finances()
    annual_income = getattr(args, "income", None)
    if not annual_income:
        monthly_sal = profile.get("inferred_tax_profile", {}).get("monthly_net_salary_signal", 0.0)
        annual_income = monthly_sal * 12 if monthly_sal > 0 else 60000.0

    liquid_cash = profile.get("gbp_balance", 0.0)
    audit = UKTaxOptimizer.full_tax_wealth_audit(gross_income=annual_income, liquid_cash=liquid_cash)

    console.print(Panel.fit(
        f"[bold cyan]🇬🇧 UK TAX & WEALTH OPTIMIZATION AUDIT (Income: £{annual_income:,.2f})[/bold cyan]",
        border_style="cyan"
    ))

    t = Table(title="Tax Bracket & Allowance Profile", border_style="blue")
    t.add_column("Tax Parameter", style="cyan")
    t.add_column("Status / Limit", style="bold white")
    t.add_column("Significance", style="dim")

    t.add_row("Marginal Tax Band", audit["tax_band"], f"Marginal rate: {audit['marginal_rate_pct']}%")
    t.add_row("Personal Savings Allowance", f"£{audit['psa_limit_gbp']:,.2f}/yr", "Tax-free savings interest cap")
    t.add_row("Annual ISA Allowance", f"£{audit['annual_isa_allowance']:,.2f}/yr", "100% tax-free shelter")
    t.add_row("Pension Annual Allowance", f"£{audit['pension_annual_allowance']:,.2f}/yr", "Up to £60k tax-deductible")
    t.add_row("Capital Gains Exemption", f"£{audit['cgt_exemption']:,.2f}/yr", "Annual tax-free gain limit")
    console.print(t)

    # 60% Trap Audit
    trap = audit["trap_60_percent"]
    color = "red" if trap["is_affected"] else "green"
    console.print(Panel(
        trap["message"],
        title="[bold]60% Personal Allowance Taper Trap Audit[/bold]",
        border_style=color
    ))

    # SIPP Tax Relief Example
    sipp = audit["sipp_relief_example"]
    console.print(Panel(
        f"• For a **£1,000.00** gross contribution into a SIPP:\n"
        f"  - You pay upfront: **£{sipp['upfront_cash_paid']:.2f}**\n"
        f"  - Government automatically tops up (20% at source): **+£{sipp['basic_relief_at_source']:.2f}**\n"
        f"  - Higher/Additional rate relief to reclaim: **£{sipp['higher_relief_to_reclaim']:.2f}**\n"
        f"  - Effective net cost to you: **£{sipp['effective_net_cost']:.2f}** (Instant ROI: **{sipp['effective_roi_instant']}%**)",
        title="[bold green]Pension / SIPP Tax Relief Engine[/bold green]",
        border_style="green"
    ))

def cmd_sweep(args):
    """Run Smart Cash Sweeping & Operating Float analysis."""
    init_db()
    engine = SmartAutomationEngine()
    sweep = engine.audit_sweeping_potential()
    standing_order = engine.generate_standing_order_plan()

    console.print(Panel.fit(
        "[bold green]⚡ SMART CASH SWEEPER & FLOAT ARCHITECT[/bold green]",
        border_style="green"
    ))

    status_color = "green" if sweep["status"] == "SWEEP_RECOMMENDED" else "yellow"
    console.print(Panel(
        f"[bold {status_color}]Status: {sweep['status']}[/bold {status_color}]\n\n"
        f"{sweep['action_memo']}\n\n"
        f"• Current Liquid Cash: £{sweep['current_liquid_cash']:,.2f}\n"
        f"• Calibrated Operating Float: £{sweep['target_operating_float']:,.2f}\n"
        f"• Excess Available to Sweep: £{sweep['excess_cash_to_sweep']:,.2f}",
        title="Smart Cash Sweeping",
        border_style=status_color
    ))

    so_text = Text()
    so_text.append(f"{standing_order['rationale']}\n\n", style="bold white")
    for s in standing_order["instructions"]:
        so_text.append(f"  • {s}\n", style="cyan")
    console.print(Panel(so_text, title="Automated Monthly Standing Order Plan", border_style="blue"))

def cmd_networth(args):
    """View multi-asset net worth balance sheet."""
    init_db()
    nw = get_net_worth_breakdown()
    save_net_worth_snapshot()

    console.print(Panel.fit(
        f"[bold green]💰 TOTAL NET WORTH: £{nw['net_worth']:,.2f}[/bold green]\n"
        f"Total Assets: £{nw['total_assets']:,.2f}  |  Total Liabilities: £{nw['total_liabilities']:,.2f}  |  Liquid Net Worth: £{nw['liquid_net_worth']:,.2f}",
        border_style="green"
    ))

    t = Table(title="Wealth Balance Sheet by Asset Class", border_style="blue")
    t.add_column("Asset Class", style="cyan")
    t.add_column("Total Value", style="bold white", justify="right")
    t.add_column("Accounts / Holdings", style="dim")

    for cls_name, val in nw["breakdown"].items():
        accs = nw["accounts_by_class"].get(cls_name, [])
        acc_names = ", ".join([a.get("name", "Account") for a in accs]) or "None"
        style_color = "red" if cls_name == "liability" else "green"
        val_str = f"-£{val:,.2f}" if cls_name == "liability" else f"£{val:,.2f}"
        t.add_row(cls_name.capitalize(), f"[{style_color}]{val_str}[/{style_color}]", acc_names)

    console.print(t)

def cmd_asset(args):
    """Add or list custom non-Open-Banking assets (property, pension, investment, mortgage)."""
    init_db()
    action = getattr(args, "action", "list")
    if action == "add":
        name = args.name
        asset_class = args.asset_class
        balance = args.balance
        asset_id = f"asset_{name.lower().replace(' ', '_')}"
        upsert_custom_asset(
            asset_id=asset_id,
            name=name,
            asset_class=asset_class,
            account_type=asset_class,
            balance=balance,
            notes=getattr(args, "notes", None)
        )
        save_net_worth_snapshot()
        console.print(f"[bold green]✓ Added {name} (£{balance:,.2f}) as {asset_class}.[/bold green]")
    elif action == "delete":
        del_id = args.id
        if delete_account(del_id):
            console.print(f"[bold yellow]✓ Deleted account {del_id}.[/bold yellow]")
        else:
            console.print(f"[bold red]❌ Account {del_id} not found.[/bold red]")
    else:
        nw = get_net_worth_breakdown()
        for cls_name, accs in nw["accounts_by_class"].items():
            if accs:
                console.print(f"\n[bold cyan]{cls_name.upper()}:[/bold cyan]")
                for a in accs:
                    console.print(f"  • {a['id']}: {a['name']} - £{a['current_balance']:,.2f}")

def cmd_traces(args):
    """Inspect AI agent observability traces, latencies, and grounding scores."""
    from fiduciary.observability.tracer import clear_all_traces, get_observability_metrics, get_recent_traces

    if getattr(args, "clear", False):
        clear_all_traces()
        console.print("[bold yellow]✓ All AI observability traces cleared.[/bold yellow]")
        return

    traces = get_recent_traces(limit=args.limit)
    metrics = get_observability_metrics()

    console.print(Panel(
        f"[bold]Total Invocations:[/bold] {metrics['total_invocations']}   "
        f"[bold]Average Latency:[/bold] {metrics['avg_latency_ms']:.0f} ms   "
        f"[bold]Grounding Pass Rate:[/bold] [bold green]{metrics['grounding_pass_rate_pct']}%[/bold green]   "
        f"[bold]On-Device Local Share:[/bold] {metrics['local_share_pct']}%",
        title="[bold cyan]🔍 AI OBSERVABILITY & GROUNDING AUDITOR[/bold cyan]",
        border_style="cyan"
    ))

    if not traces:
        console.print("[dim]No AI traces recorded yet. Query the copilot or generate an advisor briefing to generate traces.[/dim]")
        return

    if getattr(args, "detail", None):
        target = next((t for t in traces if t["id"] == args.detail), None)
        if not target:
            console.print(f"[bold red]Trace {args.detail} not found.[/bold red]")
            return
        console.print(f"\n[bold cyan]Trace Details ({target['id']}):[/bold cyan]")
        console.print(f"Caller: {target['caller']} | Provider: {target['provider']} | Model: {target['model']} | Latency: {target['latency_ms']:.1f}ms")
        console.print(f"Grounding Status: [bold green]{target['grounding_status']}[/bold green] (Score: {target['grounding_score']})")

        if target.get("tools_used"):
            tools = target["tools_used"]
            tool_rows = []
            for idx, tool in enumerate(tools, 1):
                t_name = tool.get("tool_name", "unknown")
                t_type = tool.get("type", "tool")
                t_src = tool.get("source", "N/A")
                t_lat = f"{tool.get('latency_ms', 0):.1f}ms"
                t_sum = tool.get("summary", "")
                tool_rows.append(
                    f"[bold cyan]{idx}. {t_name}[/bold cyan] ([dim]{t_type}[/dim] • [yellow]{t_lat}[/yellow])\n"
                    f"   [bold]Source / Endpoint:[/bold] {t_src}\n"
                    f"   [bold]Ingested Payload:[/bold] {t_sum}"
                )
            console.print(Panel(
                "\n\n".join(tool_rows),
                title=f"[bold cyan]🛠️ Executed Tools & Data Provenance ({len(tools)} active tools)[/bold cyan]",
                border_style="cyan"
            ))

        if target.get("judge_evaluation"):
            je = target["judge_evaluation"]
            j_style = "bold green" if je.get("verdict") == "PASSED" else ("bold yellow" if je.get("verdict") == "WARNING" else "bold red")
            console.print(Panel(
                f"[bold]Judge Model:[/bold] {je.get('judge_model')} ({je.get('judge_latency_ms', 0):.0f}ms)\n"
                f"[bold]Verdict:[/bold] [{j_style}]{je.get('verdict')}[/{j_style}] (Overall: {je.get('overall_score', 0):.2f})\n"
                f"[bold]Faithfulness:[/bold] {je.get('faithfulness', 0):.2f} | [bold]Relevance:[/bold] {je.get('relevance', 0):.2f} | [bold]Fiduciary Soundness:[/bold] {je.get('fiduciary_soundness', 0):.2f}\n"
                f"[bold]Critique:[/bold] {je.get('reasoning')}",
                title="[bold magenta]⚖️ Independent LLM-as-a-Judge Evaluation[/bold magenta]",
                border_style="magenta"
            ))

        console.print(Panel(target['user_prompt'], title="[bold yellow]User Prompt[/bold yellow]"))
        console.print(Panel(target['response'], title="[bold green]Raw AI Response[/bold green]"))
        return

    table = Table(title="Recent AI Agent Invocations & Grounding Verifications")
    table.add_column("Timestamp", style="dim", width=19)
    table.add_column("Caller", style="bold cyan")
    table.add_column("Provider / Model", style="magenta")
    table.add_column("Latency", justify="right")
    table.add_column("Tools Executed", style="cyan")
    table.add_column("Grounding Status", justify="center")
    table.add_column("LLM Judge Verdict", justify="center")
    table.add_column("Response Snippet", max_width=35)

    for t in traces:
        ts = t["timestamp"][:19].replace("T", " ")
        g_badge = "[bold green]100% Grounded[/bold green]" if t["grounding_status"] == "VERIFIED_GROUNDED" else f"[bold yellow]{t['grounding_status']}[/bold yellow]"
        prov = f"🟢 local ({t['model'][:12]})" if t["provider"] == "local" else f"🟣 {t['provider']}"
        snippet = (t.get("response") or "").replace("\n", " ")[:35] + "..."

        tools_list = t.get("tools_used") or []
        if tools_list:
            tool_names = [tool.get("tool_name", "").replace("fetch_", "").replace("query_", "").replace("_audit", "") for tool in tools_list]
            tools_str = ", ".join(tool_names[:2])
            if len(tool_names) > 2:
                tools_str += f" (+{len(tool_names)-2})"
        else:
            tools_str = "[dim]None[/dim]"

        if t.get("judge_evaluation"):
            je = t["judge_evaluation"]
            v = je.get("verdict", "N/A")
            j_badge = f"[bold green]⚖️ {v} ({je.get('overall_score', 0):.2f})[/bold green]" if v == "PASSED" else f"[bold yellow]⚖️ {v}[/bold yellow]"
        else:
            j_badge = "[dim]Not Judged[/dim]"

        table.add_row(ts, t["caller"], prov, f"{t['latency_ms']:.0f} ms", tools_str, g_badge, j_badge, snippet)

    console.print(table)
    console.print("\n[dim]Tip: Run './f traces --detail <ID>' to view complete prompt, tools & judge analysis, or './f judge' to evaluate with Gemma 7B.[/dim]\n")

def cmd_tools(args):
    """List all available deterministic and live web tools."""
    from fiduciary.agent.web_tools import get_available_tools_catalog
    catalog = get_available_tools_catalog()
    table = Table(title="🛠️ Fiduciary Agent Tools & Data Ingestion Catalog")
    table.add_column("Tool Name", style="bold cyan")
    table.add_column("Category", style="magenta")
    table.add_column("Description")
    table.add_column("Source / Endpoint", style="dim")
    table.add_column("Trigger Keywords", style="green")

    for t in catalog:
        table.add_row(
            t["tool_name"],
            t["category"],
            t["description"],
            t["source"],
            ", ".join(t["trigger_keywords"])
        )
    # Add local DB and engine tools
    table.add_row(
        "query_local_transactions",
        "local_database",
        "Deterministic SQLite query filtering client bank transactions by merchant, account, or limit.",
        "SQLite data/financial.db",
        "revolut, wise, spent, last N"
    )
    table.add_row(
        "financial_watchdog_audit",
        "rule_engine",
        "Computes liquid runway days, 3-month safety buffer, and upcoming recurring bills.",
        "Local Watchdog Profiler",
        "runway, buffer, burn, bills"
    )
    console.print(table)


def cmd_judge(args):
    """Execute independent LLM-as-a-Judge evaluation using local Ollama model."""
    from fiduciary.observability.judge import LLMJudge
    from fiduciary.observability.tracer import get_recent_traces

    req_model = getattr(args, "model", None)
    judge = LLMJudge(default_model=req_model)
    available, provider, model = judge.is_judge_available(requested_model=req_model)
    if not available:
        console.print(f"[bold red]❌ Independent Judge Offline:[/bold red] {model}")
        console.print("[dim]Ensure Ollama is running (`ollama serve`). Recommended: `ollama pull llama3.2:3b`.[/dim]")
        return

    trace_id = getattr(args, "trace_id", None)
    if not trace_id or getattr(args, "latest", False):
        traces = get_recent_traces(limit=1)
        if not traces:
            console.print("[bold yellow]No AI traces recorded to evaluate.[/bold yellow]")
            return
        trace_id = traces[0]["id"]

    console.print(f"[bold cyan]⚖️ Evaluating Trace {trace_id} using Independent Judge ({model})...[/bold cyan]")
    res = judge.evaluate_trace(trace_id, judge_model=req_model)

    if res.get("status") == "ERROR":
        console.print(f"[bold red]❌ Judge Evaluation Error:[/bold red] {res.get('error')}")
        return

    verdict_style = "bold green" if res.get("verdict") == "PASSED" else ("bold yellow" if res.get("verdict") == "WARNING" else "bold red")

    pre_audit = res.get("deterministic_audit", {})
    audit_block = ""
    if pre_audit:
        v_figs = ", ".join(pre_audit.get("verified_figures", [])) or "None"
        uv_figs = ", ".join(pre_audit.get("unverified_figures", [])) or "None (100% grounded)"
        audit_block = f"""
[bold cyan]Deterministic Fact-Checking Pre-Pass:[/bold cyan]
  • Grounding Status: {pre_audit.get('status')} ({pre_audit.get('grounding_score', 1.0) * 100:.0f}% verified)
  • Verified Data Points: {v_figs}
  • Unverified Claims: {uv_figs}
"""

    content = f"""[bold]Trace ID:[/bold] {res.get('trace_id')}
[bold]Judge Model:[/bold] {res.get('judge_model')} ({res.get('judge_latency_ms', 0):.0f} ms)
[bold]Overall Score:[/bold] [{verdict_style}]{res.get('overall_score', 0):.2f} / 1.00[/{verdict_style}]
[bold]Verdict:[/bold] [{verdict_style}]{res.get('verdict')}[/{verdict_style}]
{audit_block}
[bold cyan]Metric Breakdown:[/bold cyan]
  • [bold]Faithfulness / Grounding:[/bold] {res.get('faithfulness', 0):.2f} / 1.00
  • [bold]Relevance & Completeness:[/bold] {res.get('relevance', 0):.2f} / 1.00
  • [bold]Fiduciary Soundness:[/bold]     {res.get('fiduciary_soundness', 0):.2f} / 1.00

[bold cyan]Judge Critique & Reasoning:[/bold cyan]
{res.get('reasoning')}
"""
    console.print(Panel(content, title=f"[{verdict_style}]⚖️ LLM-AS-A-JUDGE VERDICT: {res.get('verdict')}[/{verdict_style}]", border_style="cyan"))

def cmd_seed(args):
    """Populate database with synthetic realistic UK financial data for testing without live banks."""
    from fiduciary.storage.seed import seed_demo_data
    reset = not getattr(args, "keep", False)
    console.print("[cyan]🌱 Generating synthetic UK financial data...[/cyan]")
    res = seed_demo_data(reset=reset)
    console.print(Panel.fit(
        f"[bold green]✓ SYNTHETIC DEMO DATA SEEDED SUCCESSFULLY[/bold green]\n\n"
        f"• Institutions: {res['institutions_seeded']} (NatWest, Revolut, Wise)\n"
        f"• Accounts: {res['accounts_seeded']} (Checking, Savings Vault, Currency)\n"
        f"• Transactions: {res['transactions_seeded']} (60-day history with pubs, groceries, bills, salary)\n"
        f"• Liquid Cash Balance: £{res['liquid_balance_gbp']:,.2f}\n\n"
        f"[dim]Run './f tx', './f spending pubs', or './f profile' to explore.[/dim]",
        border_style="green"
    ))

def cmd_demo(args):
    """Run interactive terminal walkthrough demonstrating all fiduciary capabilities."""
    from fiduciary.demo import run_demo
    run_demo(fast=getattr(args, "fast", False))

def build_parser():
    parser = argparse.ArgumentParser(prog="fiduciary", description="Personal Fiduciary Financial Harness (Live UK Version)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # demo (interactive live walkthrough)
    p_demo = subparsers.add_parser("demo", help="Run interactive live terminal tour demonstrating all fiduciary capabilities")
    p_demo.add_argument("--fast", action="store_true", help="Run without typing delays")
    p_demo.set_defaults(func=cmd_demo)

    # seed (synthetic data generator)
    p_seed = subparsers.add_parser("seed", help="Seed realistic synthetic UK banking data for demo/testing")
    p_seed.add_argument("--keep", action="store_true", help="Keep existing data instead of resetting")
    p_seed.set_defaults(func=cmd_seed)

    # sync
    p_sync = subparsers.add_parser("sync", help="Sync real live bank data from Wise")
    p_sync.add_argument("--clean", action="store_true", help="Clear database before syncing")
    p_sync.add_argument("--token", help="Wise API Token")
    p_sync.set_defaults(func=cmd_sync)

    # copilot (alias: chat, c)
    p_copilot = subparsers.add_parser("copilot", aliases=["chat", "co"], help="Interactive or one-shot AI Fiduciary Copilot")
    p_copilot.add_argument("query", nargs="?", help="Optional prompt to answer directly")
    p_copilot.add_argument("--react", action="store_true", help="Execute in autonomous multi-step ReAct agent mode with step-by-step trace observability")
    p_copilot.set_defaults(func=cmd_copilot)

    # react (autonomous multi-step agent)
    p_react = subparsers.add_parser("react", help="Autonomous multi-step ReAct agent with step-by-step trace observability")
    p_react.add_argument("query", help="Compound prompt to execute with autonomous ReAct trajectory")
    p_react.set_defaults(func=lambda args: (setattr(args, "react", True), cmd_copilot(args)))

    # rag (local semantic vector RAG search)
    p_rag = subparsers.add_parser("rag", help="Local semantic Vector RAG search over statutory rules and underwriter guidelines")
    p_rag.add_argument("query", help="Semantic query to search against vector corpus")
    p_rag.add_argument("--limit", "-n", type=int, default=3, help="Max results to return")
    p_rag.set_defaults(func=cmd_rag)

    # watchdog (alias: guard, wd)
    p_watchdog = subparsers.add_parser("watchdog", aliases=["guard", "wd"], help="Financial Watchdog: Price hikes, duplicate charges, upcoming bills")
    p_watchdog.set_defaults(func=cmd_watchdog)

    # credit (alias: cr)
    p_credit = subparsers.add_parser("credit", aliases=["cr"], help="Underwriter-style credit & affordability audit, mortgage capacity, stress tests")
    p_credit.add_argument("--experian", type=int, help="Record your Experian score (0-999)")
    p_credit.add_argument("--equifax", type=int, help="Record your Equifax score (0-1000)")
    p_credit.add_argument("--transunion", type=int, help="Record your TransUnion score (0-710)")
    p_credit.add_argument("--electoral-roll", choices=["yes", "no"], help="Registered on the electoral roll")
    p_credit.set_defaults(func=cmd_credit)

    # tax (alias: t)
    p_tax = subparsers.add_parser("tax", aliases=["t"], help="UK Tax & Wealth Optimization: 60%% trap audit, SIPP relief, PSA drag")
    p_tax.add_argument("--income", type=float, help="Gross annual income in GBP (optional)")
    p_tax.set_defaults(func=cmd_tax)

    # sweep
    p_sweep = subparsers.add_parser("sweep", help="Smart Cash Sweeper & Automated Standing Order Plan")
    p_sweep.set_defaults(func=cmd_sweep)

    # networth (alias: nw)
    p_nw = subparsers.add_parser("networth", aliases=["nw"], help="View complete multi-asset net worth balance sheet")
    p_nw.set_defaults(func=cmd_networth)

    # asset
    p_asset = subparsers.add_parser("asset", help="Manage custom wealth assets (property, pension, investment, mortgage)")
    p_asset_subs = p_asset.add_subparsers(dest="action", required=True)

    p_a_add = p_asset_subs.add_parser("add", help="Add custom asset")
    p_a_add.add_argument("--name", required=True, help="Asset name (e.g. 'Vanguard S&P 500' or 'Flat in London')")
    p_a_add.add_argument("--asset-class", required=True, choices=["cash", "investment", "pension", "property", "liability"], help="Asset class")
    p_a_add.add_argument("--balance", required=True, type=float, help="Current value / balance in GBP")
    p_a_add.add_argument("--notes", help="Notes")
    p_a_add.set_defaults(func=cmd_asset)

    p_a_list = p_asset_subs.add_parser("list", help="List all assets")
    p_a_list.set_defaults(func=cmd_asset)

    p_a_del = p_asset_subs.add_parser("delete", help="Delete asset by ID")
    p_a_del.add_argument("--id", required=True, help="Account / Asset ID")
    p_a_del.set_defaults(func=cmd_asset)

    # transactions (alias: tx)
    p_tx = subparsers.add_parser("transactions", aliases=["tx"], help="View real transactions with filters by bank, keyword, category, and limit")
    p_tx.add_argument("-a", "--account", "--bank", dest="account", help="Filter by bank/account (e.g. 'revolut', 'natwest', 'wise')")
    p_tx.add_argument("-n", "--limit", type=int, default=50, help="Max transactions to display (default: 50)")
    p_tx.add_argument("-s", "--search", help="Search merchant or category keyword")
    p_tx.add_argument("-c", "--category", help="Filter by category (e.g. 'dining', 'groceries', 'subscriptions')")
    p_tx.add_argument("-d", "--days", type=int, default=None, help="Number of days to look back")
    p_tx.add_argument("--all", action="store_true", help="View all stored transactions across all time")
    p_tx.set_defaults(func=cmd_transactions)

    # spending (alias: spend, sp)
    p_spend = subparsers.add_parser("spending", aliases=["spend", "sp"], help="Spending Insight Engine: Category breakdown, velocity shifts, micro-expenses")
    p_spend.add_argument("query", nargs="?", help="Specific spending query or category (e.g. 'pubs', 'groceries', 'sainsbury')")
    p_spend.add_argument("-d", "--days", type=int, default=None, help="Number of days to look back")
    p_spend.add_argument("-n", "--limit", type=int, default=20, help="Max itemized transactions to display")
    p_spend.set_defaults(func=cmd_spending)

    # connect / truelayer
    p_conn = subparsers.add_parser("connect", aliases=["truelayer"], help="Connect UK banks via TrueLayer (Revolut, Chase, HSBC, etc.)")
    p_conn.set_defaults(func=cmd_connect)

    # profile (alias: p)
    p_prof = subparsers.add_parser("profile", aliases=["p"], help="Profile real transactions (salary, tax band, direct debits, burn rate)")
    p_prof.set_defaults(func=cmd_profile)

    # scout (alias: s)
    p_scout = subparsers.add_parser("scout", aliases=["s"], help="Scout live UK rates (Cash ISAs, after-tax yields, switch deals)")
    p_scout.set_defaults(func=cmd_scout)

    # audit (alias: a)
    p_audit = subparsers.add_parser("audit", aliases=["a"], help="Run fiduciary audit and live AI strategy memo")
    p_audit.set_defaults(func=cmd_audit)

    # ai
    p_ai = subparsers.add_parser("ai", help="Generate live AI Fiduciary Strategy Memo")
    p_ai.set_defaults(func=cmd_audit)

    # ui (alias: w)
    p_ui = subparsers.add_parser("ui", aliases=["w", "dashboard"], help="Launch local web dashboard with mobile access")
    p_ui.add_argument("--host", default="0.0.0.0", help="Host interface (default: 0.0.0.0 for phone access on Wi-Fi)")
    p_ui.add_argument("--port", type=int, default=PORT, help=f"Server port (default: {PORT})")
    p_ui.set_defaults(func=cmd_ui)

    # gateway (alias: gw, proxy)
    p_gw = subparsers.add_parser("gateway", aliases=["gw", "proxy"], help="Start or inspect Enterprise AI Gateway (LiteLLM Proxy)")
    p_gw.add_argument("--status", action="store_true", help="Inspect gateway health and status without starting")
    p_gw.add_argument("--port", type=int, default=4000, help="Proxy port (default: 4000)")
    p_gw.set_defaults(func=cmd_gateway)

    # traces (alias: tr, logs)
    p_traces = subparsers.add_parser("traces", aliases=["tr", "logs"], help="Inspect AI agent observability traces and grounding audits")
    p_traces.add_argument("--limit", type=int, default=15, help="Max traces to show (default: 15)")
    p_traces.add_argument("--detail", help="View full prompt/response for specific trace ID")
    p_traces.add_argument("--clear", action="store_true", help="Purge all trace logs")
    p_traces.set_defaults(func=cmd_traces)

    # judge (alias: eval, j)
    p_judge = subparsers.add_parser("judge", aliases=["eval", "j"], help="Evaluate AI Copilot outputs using independent local model (LLM-as-a-Judge)")
    p_judge.add_argument("trace_id", nargs="?", help="Specific trace ID to evaluate (defaults to latest)")
    p_judge.add_argument("--latest", action="store_true", help="Evaluate the most recent AI trace")
    p_judge.add_argument("--model", "-m", help="Override judge model (e.g. llama3.2:3b, gemma2:2b)")
    p_judge.set_defaults(func=cmd_judge)

    # tools (alias: tl, catalog)
    p_tools = subparsers.add_parser("tools", aliases=["tl", "catalog"], help="Inspect available deterministic & live web tools catalog")
    p_tools.set_defaults(func=cmd_tools)

    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

