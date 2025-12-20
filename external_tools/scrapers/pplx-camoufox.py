#!/usr/bin/env python3
"""
Perplexity Finance Scraper using Camoufox.
Bypasses Cloudflare bot detection to fetch ALL real-time stock data.

Usage:
    uv run pplx-camoufox.py SYMBOL [--json]

Examples:
    uv run pplx-camoufox.py RKLB
    uv run pplx-camoufox.py NVDA --json
"""

import sys
import time
import json
import argparse
from camoufox.sync_api import Camoufox
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


def fetch_perplexity_data(ticker: str) -> dict:
    """Fetch ALL Perplexity Finance data for a ticker using Camoufox."""
    data = {
        "ticker": ticker,
        "quote": None,
        "profile": None,
        "documents": None,
        "overview": None,
        "timeline": None,
        "bulls_vs_bears": None,
        "news": None,
        "peers": None,
        "earnings": None,
        "financials": None,
        "prediction_markets": None,
        "top_movers": None,
        "error": None,
    }

    try:
        with Camoufox(headless=True) as browser:
            page = browser.new_page()

            # Navigate to finance page
            page.goto(f'https://www.perplexity.ai/finance/{ticker}', timeout=60000)
            page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(3)

            # Fetch quote API
            data["quote"] = page.evaluate(f'''async () => {{
                try {{
                    const resp = await fetch('/rest/finance/quote/{ticker}?with_history=false&with_ui_hints=true');
                    return await resp.json();
                }} catch(e) {{
                    return {{"error": e.toString()}};
                }}
            }}''')

            # Fetch profile API
            data["profile"] = page.evaluate(f'''async () => {{
                try {{
                    const resp = await fetch('/rest/finance/profile/{ticker}');
                    return await resp.json();
                }} catch(e) {{
                    return {{"error": e.toString()}};
                }}
            }}''')

            # Fetch documents API (contains research reports)
            data["documents"] = page.evaluate(f'''async () => {{
                try {{
                    const resp = await fetch('/rest/finance/documents/{ticker}');
                    return await resp.json();
                }} catch(e) {{
                    return {{"error": e.toString()}};
                }}
            }}''')

            # Fetch overview API
            data["overview"] = page.evaluate(f'''async () => {{
                try {{
                    const resp = await fetch('/rest/finance/overview/{ticker}');
                    return await resp.json();
                }} catch(e) {{
                    return {{"error": e.toString()}};
                }}
            }}''')

            # Fetch timeline API (THE GOLD - price movements & developments)
            data["timeline"] = page.evaluate(f'''async () => {{
                try {{
                    const resp = await fetch('/rest/finance/timeline/v2/{ticker}');
                    return await resp.json();
                }} catch(e) {{
                    return {{"error": e.toString()}};
                }}
            }}''')

            # Fetch bulls vs bears summary (key issues with bullish/bearish views)
            data["bulls_vs_bears"] = page.evaluate(f'''async () => {{
                try {{
                    const resp = await fetch('/rest/finance/bulls-vs-bears-summary/{ticker}');
                    return await resp.json();
                }} catch(e) {{
                    return {{"error": e.toString()}};
                }}
            }}''')

            # Fetch news API (latest headlines)
            data["news"] = page.evaluate(f'''async () => {{
                try {{
                    const resp = await fetch('/rest/finance/news/{ticker}');
                    return await resp.json();
                }} catch(e) {{
                    return {{"error": e.toString()}};
                }}
            }}''')

            # Fetch peers API
            data["peers"] = page.evaluate(f'''async () => {{
                try {{
                    const resp = await fetch('/rest/finance/peers/{ticker}');
                    return await resp.json();
                }} catch(e) {{
                    return {{"error": e.toString()}};
                }}
            }}''')

            # Fetch earnings API
            data["earnings"] = page.evaluate(f'''async () => {{
                try {{
                    const resp = await fetch('/rest/finance/earnings/{ticker}');
                    return await resp.json();
                }} catch(e) {{
                    return {{"error": e.toString()}};
                }}
            }}''')

            # Fetch financials API
            data["financials"] = page.evaluate(f'''async () => {{
                try {{
                    const resp = await fetch('/rest/finance/financials/{ticker}');
                    return await resp.json();
                }} catch(e) {{
                    return {{"error": e.toString()}};
                }}
            }}''')

            # Fetch prediction markets API
            data["prediction_markets"] = page.evaluate(f'''async () => {{
                try {{
                    const resp = await fetch('/rest/finance/prediction-markets/{ticker}/trending-ticker');
                    return await resp.json();
                }} catch(e) {{
                    return {{"error": e.toString()}};
                }}
            }}''')

            # Fetch top movers API
            data["top_movers"] = page.evaluate('''async () => {
                try {
                    const resp = await fetch('/rest/finance/top-movers/market');
                    return await resp.json();
                } catch(e) {
                    return {"error": e.toString()};
                }
            }''')

    except Exception as e:
        data["error"] = str(e)

    return data


def display_data(data: dict):
    """Display ALL extracted data with Rich formatting."""
    ticker = data["ticker"]
    quote = data.get("quote", {}) or {}
    profile = data.get("profile", {}) or {}
    documents = data.get("documents", {}) or {}
    overview = data.get("overview", {}) or {}
    timeline = data.get("timeline", {}) or {}
    bulls_vs_bears = data.get("bulls_vs_bears", {}) or {}
    news = data.get("news", {}) or {}
    peers = data.get("peers", {}) or {}
    earnings = data.get("earnings", {}) or {}
    prediction_markets = data.get("prediction_markets", {}) or {}

    if data.get("error"):
        console.print(f"[red]Error: {data['error']}[/red]")
        return

    # Header
    name = profile.get("name", "") or quote.get("name", ticker)
    console.print(f"\n[bold cyan]{'=' * 20} {ticker} - {name} {'=' * 20}[/bold cyan]\n", justify="center")

    # Quote Summary
    if quote and "error" not in quote:
        t = Table(title="Quote Summary", box=box.ROUNDED, title_style="bold cyan")
        t.add_column("Metric", style="cyan")
        t.add_column("Value", justify="right", style="white bold")
        t.add_column("Metric", style="cyan")
        t.add_column("Value", justify="right", style="white bold")

        price = quote.get("price", quote.get("regularMarketPrice", "-"))
        change = quote.get("change", quote.get("regularMarketChange", 0))
        change_pct = quote.get("percentChange", quote.get("regularMarketChangePercent", 0))

        # Color based on change
        if change and float(change) >= 0:
            price_style = "green"
            change_str = f"+${change:.2f} (+{change_pct:.2f}%)"
        else:
            price_style = "red"
            change_str = f"${change:.2f} ({change_pct:.2f}%)"

        t.add_row("Price", f"[{price_style}]${price}[/{price_style}]", "Change", f"[{price_style}]{change_str}[/{price_style}]")

        # After hours
        ah_price = quote.get("afterHoursPrice")
        ah_change = quote.get("afterHoursPercentChange")
        if ah_price:
            ah_style = "green" if ah_change and ah_change >= 0 else "red"
            t.add_row("After Hours", f"[{ah_style}]${ah_price:.2f}[/{ah_style}]", "AH Change", f"[{ah_style}]{ah_change:+.2f}%[/{ah_style}]")

        prev_close = quote.get("previousClose", "-")
        open_price = quote.get("open", "-")
        t.add_row("Prev Close", f"${prev_close}", "Open", f"${open_price}")

        day_low = quote.get("dayLow", "-")
        day_high = quote.get("dayHigh", "-")
        vol = quote.get('volume')
        vol_str = f"{vol:,}" if isinstance(vol, (int, float)) else "-"
        t.add_row("Day Range", f"${day_low} - ${day_high}", "Volume", vol_str)

        market_cap = quote.get("marketCap", 0)
        if market_cap:
            if market_cap >= 1e12:
                mc_str = f"${market_cap/1e12:.2f}T"
            elif market_cap >= 1e9:
                mc_str = f"${market_cap/1e9:.2f}B"
            else:
                mc_str = f"${market_cap/1e6:.2f}M"
        else:
            mc_str = "-"

        pe = quote.get("peRatio", quote.get("trailingPE", "-"))
        t.add_row("Market Cap", mc_str, "P/E Ratio", str(pe) if pe else "-")

        console.print(t)
        console.print()

    # LATEST PRICE MOVEMENT (THE GOLD from timeline API)
    timeline_data = timeline.get("data", []) if isinstance(timeline, dict) else []
    if timeline_data:
        console.print(Panel("[bold green]Latest Price Movement[/bold green]", box=box.ROUNDED))
        for entry in timeline_data[:3]:  # Show latest 3 movements
            desc = entry.get("description", "")
            price_movement = entry.get("price_movement")
            price = entry.get("price")
            timestamp = entry.get("timestamp", "")[:10] if entry.get("timestamp") else ""

            if price_movement:
                if price_movement >= 0:
                    style = "green"
                    icon = "^"
                else:
                    style = "red"
                    icon = "v"
                console.print(f"  [{style}]{icon} {price_movement:+.2f}%[/{style}] @ ${price:.2f} ({timestamp})")

            if desc:
                # Truncate long descriptions
                if len(desc) > 400:
                    desc = desc[:400] + "..."
                console.print(f"  [white]{desc}[/white]")
            console.print()

    # RECENT DEVELOPMENTS (from news API)
    news_posts = news.get("posts", []) if isinstance(news, dict) else []
    if news_posts:
        console.print(Panel("[bold yellow]Recent Developments / Headlines[/bold yellow]", box=box.ROUNDED))
        for post in news_posts[:5]:  # Show latest 5 headlines
            headline = post.get("headline", "")
            text = post.get("text", "")
            timestamp = post.get("timestamp", "")[:10] if post.get("timestamp") else ""
            sources = post.get("sources", [])

            if headline:
                console.print(f"  [bold]{headline}[/bold]")
            if timestamp:
                source_names = [s.get("name", "") for s in sources[:2]] if sources else []
                source_str = " | ".join(source_names) if source_names else ""
                console.print(f"  [dim]{timestamp} - {source_str}[/dim]")
            if text:
                if len(text) > 300:
                    text = text[:300] + "..."
                console.print(f"  {text}")
            console.print()

    # KEY ISSUES - BULLISH vs BEARISH (from bulls_vs_bears API)
    issues = bulls_vs_bears.get("controversial_issues", []) if isinstance(bulls_vs_bears, dict) else []
    if issues:
        console.print(Panel("[bold magenta]Key Issues - Bullish vs Bearish Views[/bold magenta]", box=box.ROUNDED))
        for issue in issues[:5]:
            issue_topic = issue.get("issue", "")
            positive = issue.get("positive_view", {})
            negative = issue.get("negative_view", {})

            if issue_topic:
                console.print(f"  [bold cyan]{issue_topic}[/bold cyan]")

            pos_desc = positive.get("description", "") if positive else ""
            neg_desc = negative.get("description", "") if negative else ""

            if pos_desc:
                if len(pos_desc) > 200:
                    pos_desc = pos_desc[:200] + "..."
                console.print(f"    [green]BULL:[/green] {pos_desc}")
            if neg_desc:
                if len(neg_desc) > 200:
                    neg_desc = neg_desc[:200] + "..."
                console.print(f"    [red]BEAR:[/red] {neg_desc}")
            console.print()

    # Company Profile
    if profile and "error" not in profile:
        t = Table(title="Company Profile", box=box.ROUNDED)
        t.add_column("Field", style="cyan")
        t.add_column("Value", justify="right")
        t.add_column("Field", style="cyan")
        t.add_column("Value", justify="right")

        ceo = profile.get("ceo", "-")
        employees = profile.get("fullTimeEmployees", "-")
        if isinstance(employees, (int, float)):
            employees = f"{employees:,}"

        t.add_row("CEO", ceo, "Employees", str(employees))
        t.add_row("Sector", profile.get("sector", "-"), "Industry", profile.get("industry", "-"))
        t.add_row("Exchange", profile.get("exchange", "-"), "Country", profile.get("country", "-"))

        console.print(t)
        console.print()

    # PEERS - API returns array directly, not nested
    peers_list = peers if isinstance(peers, list) else (peers.get("peers", []) if isinstance(peers, dict) else [])
    if peers_list:
        t = Table(title="Sector Peers", box=box.ROUNDED)
        t.add_column("Ticker", style="cyan bold")
        t.add_column("Name")
        t.add_column("Price", justify="right")
        t.add_column("Change", justify="right")
        t.add_column("Market Cap", justify="right")

        for peer in peers_list[:10]:
            peer_ticker = peer.get("symbol", peer.get("ticker", ""))
            peer_name = peer.get("name", "")[:30]
            peer_price = peer.get("price", 0)
            peer_change = peer.get("changesPercentage", peer.get("percentChange", 0))
            peer_mcap = peer.get("marketCap", 0)

            change_style = "green" if peer_change >= 0 else "red"
            change_str = f"{peer_change:+.2f}%"

            if peer_mcap >= 1e12:
                mcap_str = f"${peer_mcap/1e12:.1f}T"
            elif peer_mcap >= 1e9:
                mcap_str = f"${peer_mcap/1e9:.1f}B"
            elif peer_mcap >= 1e6:
                mcap_str = f"${peer_mcap/1e6:.1f}M"
            else:
                mcap_str = "-"

            t.add_row(
                peer_ticker,
                peer_name,
                f"${peer_price:.2f}" if peer_price else "-",
                f"[{change_style}]{change_str}[/{change_style}]",
                mcap_str
            )

        console.print(t)
        console.print()

    # PREDICTION MARKETS - API returns array directly
    predictions = prediction_markets if isinstance(prediction_markets, list) else []
    if predictions:
        console.print(Panel("[bold blue]Prediction Markets[/bold blue]", box=box.ROUNDED))
        for pred in predictions[:5]:
            title = pred.get("title", "")
            provider = pred.get("provider", "")
            markets = pred.get("markets", [])

            if title:
                console.print(f"  [bold]{title}[/bold]")
                console.print(f"    [dim]Provider: {provider}[/dim]")

                for market in markets[:2]:
                    question = market.get("question", "")
                    probability = market.get("probability")
                    outcomes = market.get("outcomes", [])

                    if probability is not None:
                        prob_str = f"{probability*100:.1f}%"
                        outcome_str = f"{outcomes[0]}" if outcomes else "Yes"
                        console.print(f"    {outcome_str}: [cyan]{prob_str}[/cyan]")
                console.print()

    # EARNINGS - API returns array directly
    earnings_data = earnings if isinstance(earnings, list) else (earnings.get("earnings", []) if isinstance(earnings, dict) else [])
    # Filter to only show earnings with actual results (not future estimates)
    past_earnings = [e for e in earnings_data if e.get("actualEps") is not None or e.get("actualRevenue")]
    if past_earnings:
        t = Table(title="Earnings History", box=box.ROUNDED)
        t.add_column("Period", style="cyan")
        t.add_column("EPS Actual", justify="right")
        t.add_column("EPS Est", justify="right")
        t.add_column("Revenue", justify="right")
        t.add_column("Beat/Miss", justify="right")

        for earn in past_earnings[:4]:
            period = f"{earn.get('fiscalPeriod', '')} {earn.get('fiscalYear', '')}"
            eps_actual = earn.get("actualEps")
            eps_estimate = earn.get("estimatedEps")
            revenue = earn.get("actualRevenue", 0)

            eps_actual_str = f"${eps_actual:.2f}" if eps_actual is not None else "-"
            eps_est_str = f"${eps_estimate:.2f}" if eps_estimate is not None else "-"

            # Calculate beat/miss
            if eps_actual is not None and eps_estimate is not None and eps_estimate != 0:
                beat = eps_actual - eps_estimate
                if beat >= 0:
                    beat_str = f"[green]+${beat:.2f}[/green]"
                else:
                    beat_str = f"[red]${beat:.2f}[/red]"
            else:
                beat_str = "-"

            if revenue and revenue >= 1e9:
                rev_str = f"${revenue/1e9:.2f}B"
            elif revenue and revenue >= 1e6:
                rev_str = f"${revenue/1e6:.1f}M"
            else:
                rev_str = "-"

            t.add_row(period, eps_actual_str, eps_est_str, rev_str, beat_str)

        console.print(t)
        console.print()

    # Upcoming earnings
    future_earnings = [e for e in earnings_data if e.get("actualEps") is None and e.get("estimatedEps") is not None]
    if future_earnings:
        next_earn = future_earnings[0]
        date = next_earn.get("date", "")[:10] if next_earn.get("date") else "-"
        period = f"{next_earn.get('fiscalPeriod', '')} {next_earn.get('fiscalYear', '')}"
        est_eps = next_earn.get("estimatedEps")
        console.print(f"[dim]Next Earnings: {date} ({period}) - Est EPS: ${est_eps:.2f}[/dim]")
        console.print()

    # Research Reports from documents API
    sourced_reports = documents.get("sourced_reports", []) if isinstance(documents, dict) else []
    if sourced_reports:
        console.print(Panel("[bold green]Research Reports & Analysis[/bold green]", box=box.ROUNDED))

        for report in sourced_reports[:5]:
            outlook = report.get("outlook", "neutral")
            if outlook in ("bullish", "upbeat"):
                outlook_text = f"[green]BULL {outlook.upper()}[/green]"
            elif outlook in ("bearish", "cautious"):
                outlook_text = f"[red]BEAR {outlook.upper()}[/red]"
            else:
                outlook_text = f"[yellow]-- {outlook.upper()}[/yellow]"

            title = report.get("title", "")
            provider = report.get("provider", "")
            date = report.get("date", "")[:10] if report.get("date") else ""
            summary = report.get("summary", "")

            console.print(f"  {outlook_text} [bold]{title}[/bold]")
            console.print(f"    [dim]{provider} | {date}[/dim]")
            if summary:
                # Truncate long summaries
                if len(summary) > 300:
                    summary = summary[:300] + "..."
                console.print(f"    {summary}")
            console.print()

    # Overview sections (additional price movements, developments)
    if overview and "error" not in overview:
        sections = overview.get("sections", [])
        for section in sections:
            section_type = section.get("type", "")
            title = section.get("title", section_type)
            content = section.get("content", "")

            if content and section_type not in ["price_movement"]:  # Skip if already shown from timeline
                if section_type == "developments" or "development" in title.lower():
                    console.print(Panel(f"[bold yellow]{title}[/bold yellow]", box=box.ROUNDED))
                    if len(content) > 500:
                        content = content[:500] + "..."
                    console.print(f"  {content}")
                    console.print()


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Perplexity Finance data using Camoufox (bypasses Cloudflare)",
    )
    parser.add_argument("symbol", type=str, help="Stock ticker symbol (e.g., RKLB, NVDA)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON data")
    args = parser.parse_args()

    ticker = args.symbol.upper()

    if not args.json:
        console.print(f"[dim]Fetching {ticker} from Perplexity Finance via Camoufox...[/dim]")

    data = fetch_perplexity_data(ticker)

    if args.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        display_data(data)


if __name__ == "__main__":
    main()
