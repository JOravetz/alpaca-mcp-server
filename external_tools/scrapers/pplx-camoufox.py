#!/usr/bin/env python3
"""
Perplexity Finance Scraper using Camoufox.
Bypasses Cloudflare bot detection to fetch ALL real-time stock data.

Usage:
    uv run pplx-camoufox.py SYMBOL [--json]
    uv run pplx-camoufox.py --market [--json]

Examples:
    uv run pplx-camoufox.py RKLB              # Stock-specific data
    uv run pplx-camoufox.py NVDA --json       # Stock data as JSON
    uv run pplx-camoufox.py --market          # Main finance page overview
    uv run pplx-camoufox.py --market --json   # Market overview as JSON
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


def fetch_market_overview() -> dict:
    """Fetch main Perplexity Finance page data (market overview)."""
    data = {
        "indices": None,
        "market_summary": None,
        "market_sentiment": None,
        "top_movers": None,
        "sectors": None,
        "prediction_markets": None,
        "crypto": None,
        "fixed_income": None,
        "headlines": None,
        "standouts": None,
        "recent_developments": None,
        "error": None,
    }

    try:
        with Camoufox(headless=True) as browser:
            page = browser.new_page()

            # Navigate to main finance page
            page.goto('https://www.perplexity.ai/finance', timeout=60000)
            page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(3)

            # Fetch market indices (futures, VIX)
            data["indices"] = page.evaluate('''async () => {
                try {
                    const resp = await fetch('/rest/finance/top-indices/market?with_history=true&history_period=1d&country=US');
                    return await resp.json();
                } catch(e) {
                    return {"error": e.toString()};
                }
            }''')

            # Fetch market summary (AI-generated overview)
            data["market_summary"] = page.evaluate('''async () => {
                try {
                    const resp = await fetch('/rest/finance/market-summary/market?country=US');
                    return await resp.json();
                } catch(e) {
                    return {"error": e.toString()};
                }
            }''')

            # Fetch market sentiment
            data["market_sentiment"] = page.evaluate('''async () => {
                try {
                    const resp = await fetch('/rest/finance/market-sentiment/market?country=US');
                    return await resp.json();
                } catch(e) {
                    return {"error": e.toString()};
                }
            }''')

            # Fetch top movers (gainers, losers, active)
            data["top_movers"] = page.evaluate('''async () => {
                try {
                    const resp = await fetch('/rest/finance/top-movers/market?country=US');
                    return await resp.json();
                } catch(e) {
                    return {"error": e.toString()};
                }
            }''')

            # Fetch equity sectors
            data["sectors"] = page.evaluate('''async () => {
                try {
                    const resp = await fetch('/rest/finance/equity-sectors');
                    return await resp.json();
                } catch(e) {
                    return {"error": e.toString()};
                }
            }''')

            # Fetch prediction markets
            data["prediction_markets"] = page.evaluate('''async () => {
                try {
                    const resp = await fetch('/rest/finance/prediction-markets/tag/finance?with_commentary=false&page=0&limit=10&version=2.18&source=default');
                    return await resp.json();
                } catch(e) {
                    return {"error": e.toString()};
                }
            }''')

            # Fetch crypto prices
            data["crypto"] = page.evaluate('''async () => {
                try {
                    const resp = await fetch('/rest/finance/top-indices/crypto_sidebar?with_history=true&history_period=1d&country=US');
                    return await resp.json();
                } catch(e) {
                    return {"error": e.toString()};
                }
            }''')

            # Fetch fixed income
            data["fixed_income"] = page.evaluate('''async () => {
                try {
                    const resp = await fetch('/rest/finance/fixed-income');
                    return await resp.json();
                } catch(e) {
                    return {"error": e.toString()};
                }
            }''')

            # Fetch latest headlines (general news)
            data["headlines"] = page.evaluate('''async () => {
                try {
                    const resp = await fetch('/rest/finance/general-news/market?country=US');
                    return await resp.json();
                } catch(e) {
                    return {"error": e.toString()};
                }
            }''')

            # Fetch standouts / significant movers (z-scores) with full details
            data["standouts"] = page.evaluate('''async () => {
                try {
                    // Get z-score symbols first
                    const zResp = await fetch('/rest/finance/top-z-scores/market?country=US');
                    const zScores = await zResp.json();

                    if (!Array.isArray(zScores) || zScores.length === 0) {
                        return zScores;
                    }

                    // Fetch quote and summary for each standout
                    const enriched = await Promise.all(zScores.slice(0, 6).map(async (item) => {
                        const symbol = item.symbol;
                        try {
                            // Get quote data
                            const quoteResp = await fetch(`/rest/finance/quote/${symbol}?with_history=false&with_ui_hints=true`);
                            const quote = await quoteResp.json();

                            // Get significant movement summary
                            const summaryResp = await fetch(`/rest/finance/significant-movement-summary/${symbol}?version=2.18&source=default`);
                            const summary = await summaryResp.json();

                            return {
                                symbol: symbol,
                                z_score: item.z_score,
                                name: quote.name || symbol,
                                price: quote.price || quote.regularMarketPrice || 0,
                                change: quote.change || quote.regularMarketChange || 0,
                                changesPercentage: quote.percentChange || quote.changesPercentage || 0,
                                summary: summary.explanation || summary.summary || summary.text || ""
                            };
                        } catch(e) {
                            return item;
                        }
                    }));

                    return enriched;
                } catch(e) {
                    return {"error": e.toString()};
                }
            }''')

            # Fetch recent developments (market news)
            data["recent_developments"] = page.evaluate('''async () => {
                try {
                    const resp = await fetch('/rest/finance/news/market');
                    return await resp.json();
                } catch(e) {
                    return {"error": e.toString()};
                }
            }''')

    except Exception as e:
        data["error"] = str(e)

    return data


def display_market_overview(data: dict):
    """Display market overview data with Rich formatting."""
    if data.get("error"):
        console.print(f"[red]Error: {data['error']}[/red]")
        return

    console.print()
    console.rule("[bold cyan]PERPLEXITY FINANCE - MARKET OVERVIEW[/bold cyan]", style="cyan")
    console.print()

    # MARKET INDICES (Futures & VIX)
    indices = data.get("indices", {}) or {}
    if indices and "error" not in indices:
        t = Table(title="Market Indices & Futures", box=box.ROUNDED, title_style="bold cyan")
        t.add_column("Index", style="cyan bold")
        t.add_column("Price", justify="right")
        t.add_column("Change", justify="right")
        t.add_column("% Change", justify="right")

        # Handle list of indices
        index_list = indices if isinstance(indices, list) else indices.get("indices", [])
        for idx in (index_list if isinstance(index_list, list) else []):
            symbol = idx.get("symbol", "")
            name = idx.get("name", symbol)
            price = idx.get("price", idx.get("regularMarketPrice", 0))
            change = idx.get("change", idx.get("regularMarketChange", 0))
            pct_change = idx.get("changesPercentage", idx.get("percentChange", idx.get("regularMarketChangePercent", 0)))

            style = "green" if change >= 0 else "red"
            t.add_row(
                name[:20],
                f"{price:,.2f}",
                f"[{style}]{change:+,.2f}[/{style}]",
                f"[{style}]{pct_change:+.2f}%[/{style}]"
            )

        console.print(t)
        console.print()

    # MARKET SENTIMENT
    sentiment = data.get("market_sentiment", {}) or {}
    if sentiment and "error" not in sentiment and "detail" not in sentiment:
        sentiment_val = sentiment.get("sentiment", "neutral")
        market_status = sentiment.get("market_status", "")
        style = "green" if sentiment_val in ("bullish", "upbeat") else "red" if sentiment_val in ("bearish", "fearful") else "yellow"
        console.print(f"[{style}]Market Sentiment: {sentiment_val.upper()}[/{style}] | Status: {market_status}")
        console.print()

    # MARKET SUMMARY
    market_summary = data.get("market_summary", {}) or {}
    if market_summary and "error" not in market_summary and "detail" not in market_summary:
        console.print(Panel("[bold green]Market Summary[/bold green]", box=box.ROUNDED))

        # Handle new structure: data.summary array
        summary_data = market_summary.get("data", {})
        summaries = summary_data.get("summary", []) if isinstance(summary_data, dict) else []
        for item in (summaries if isinstance(summaries, list) else [])[:6]:
            header = item.get("header", item.get("headline", item.get("title", "")))
            detail = item.get("detail", item.get("content", item.get("text", "")))

            if header:
                console.print(f"  [bold]{header}[/bold]")
            if detail:
                if len(detail) > 300:
                    detail = detail[:300] + "..."
                console.print(f"  {detail}")
            console.print()

    # TOP MOVERS
    top_movers = data.get("top_movers", {}) or {}
    if top_movers and "error" not in top_movers:
        # Gainers
        gainers = top_movers.get("gainers", []) if isinstance(top_movers, dict) else []
        if gainers:
            t = Table(title="Top Gainers", box=box.ROUNDED, title_style="bold green")
            t.add_column("Symbol", style="cyan bold")
            t.add_column("Name")
            t.add_column("Price", justify="right")
            t.add_column("Change", justify="right")

            for stock in gainers[:8]:
                symbol = stock.get("symbol", stock.get("ticker", ""))
                name = stock.get("name", "")[:25]
                price = stock.get("price", 0)
                pct = stock.get("changesPercentage", stock.get("percentChange", 0))

                t.add_row(symbol, name, f"${price:.2f}", f"[green]+{pct:.2f}%[/green]")

            console.print(t)
            console.print()

        # Losers
        losers = top_movers.get("losers", []) if isinstance(top_movers, dict) else []
        if losers:
            t = Table(title="Top Losers", box=box.ROUNDED, title_style="bold red")
            t.add_column("Symbol", style="cyan bold")
            t.add_column("Name")
            t.add_column("Price", justify="right")
            t.add_column("Change", justify="right")

            for stock in losers[:5]:
                symbol = stock.get("symbol", stock.get("ticker", ""))
                name = stock.get("name", "")[:25]
                price = stock.get("price", 0)
                pct = stock.get("changesPercentage", stock.get("percentChange", 0))

                t.add_row(symbol, name, f"${price:.2f}", f"[red]{pct:.2f}%[/red]")

            console.print(t)
            console.print()

    # EQUITY SECTORS
    sectors = data.get("sectors", {}) or {}
    if sectors and "error" not in sectors and "detail" not in sectors:
        t = Table(title="Equity Sectors", box=box.ROUNDED, title_style="bold yellow")
        t.add_column("Sector", style="cyan")
        t.add_column("Symbol", style="dim")
        t.add_column("Price", justify="right")
        t.add_column("Change", justify="right")

        sector_list = sectors if isinstance(sectors, list) else sectors.get("sectors", [])
        for sector in (sector_list if isinstance(sector_list, list) else [])[:11]:
            symbol = sector.get("symbol", "")
            name = sector.get("name", sector.get("sector", ""))
            price = sector.get("price", 0)
            pct = sector.get("changesPercentage", sector.get("percentChange", 0))

            style = "green" if pct >= 0 else "red"
            t.add_row(name, symbol, f"${price:.2f}" if price else "-", f"[{style}]{pct:+.2f}%[/{style}]")

        console.print(t)
        console.print()

    # RECENT DEVELOPMENTS
    recent_dev = data.get("recent_developments", {}) or {}
    if recent_dev and "error" not in recent_dev and "detail" not in recent_dev:
        console.print(Panel("[bold yellow]Recent Developments[/bold yellow]", box=box.ROUNDED))

        developments = recent_dev.get("posts", []) if isinstance(recent_dev, dict) else recent_dev
        for dev in (developments if isinstance(developments, list) else [])[:5]:
            headline = dev.get("headline", dev.get("title", ""))
            text = dev.get("text", dev.get("summary", dev.get("content", "")))
            timestamp = dev.get("timestamp", dev.get("date", ""))
            if timestamp:
                timestamp = str(timestamp)[:10]

            if headline:
                console.print(f"  [bold]{headline}[/bold]")
            if timestamp:
                console.print(f"  [dim]{timestamp}[/dim]")
            if text:
                if len(text) > 250:
                    text = text[:250] + "..."
                console.print(f"  {text}")
            console.print()

    # PREDICTION MARKETS
    predictions = data.get("prediction_markets", {}) or {}
    if predictions and "error" not in predictions and "detail" not in predictions:
        console.print(Panel("[bold blue]Prediction Markets[/bold blue]", box=box.ROUNDED))

        pred_list = predictions if isinstance(predictions, list) else predictions.get("markets", predictions.get("predictions", []))
        for pred in (pred_list if isinstance(pred_list, list) else [])[:5]:
            title = pred.get("title", pred.get("question", ""))
            provider = pred.get("provider", "")
            volume = pred.get("volume", 0)
            markets = pred.get("markets", [])

            if title:
                console.print(f"  [bold]{title}[/bold]")
                if provider:
                    console.print(f"    [dim]Source: {provider}[/dim]")

                # Show market outcomes
                for market in markets[:3]:
                    question = market.get("question", "")
                    probability = market.get("probability")

                    if probability is not None:
                        if isinstance(probability, float) and probability <= 1:
                            probability = probability * 100
                        console.print(f"    {question}: [cyan]{probability:.1f}%[/cyan]")

                if volume:
                    vol_str = f"${volume/1e6:.1f}M" if volume >= 1e6 else f"${volume:,.0f}"
                    console.print(f"    [dim]Volume: {vol_str}[/dim]")
                console.print()

    # CRYPTO
    crypto = data.get("crypto", {}) or {}
    if crypto and "error" not in crypto and "detail" not in crypto:
        t = Table(title="Popular Cryptocurrencies", box=box.ROUNDED, title_style="bold magenta")
        t.add_column("Crypto", style="cyan bold")
        t.add_column("Price", justify="right")
        t.add_column("Change", justify="right")

        crypto_list = crypto if isinstance(crypto, list) else crypto.get("quotes", [])
        for q in (crypto_list if isinstance(crypto_list, list) else []):
            symbol = q.get("symbol", "")
            name = q.get("name", symbol)
            price = q.get("price", q.get("regularMarketPrice", 0))
            pct = q.get("changesPercentage", q.get("percentChange", q.get("regularMarketChangePercent", 0)))

            style = "green" if pct >= 0 else "red"
            t.add_row(name, f"${price:,.2f}", f"[{style}]{pct:+.2f}%[/{style}]")

        console.print(t)
        console.print()

    # FIXED INCOME
    fixed_income = data.get("fixed_income", {}) or {}
    if fixed_income and "error" not in fixed_income and "detail" not in fixed_income:
        t = Table(title="Fixed Income", box=box.ROUNDED, title_style="bold white")
        t.add_column("Instrument", style="cyan")
        t.add_column("Symbol", style="dim")
        t.add_column("Price", justify="right")
        t.add_column("Change", justify="right")

        fi_list = fixed_income if isinstance(fixed_income, list) else fixed_income.get("instruments", [])
        for item in (fi_list if isinstance(fi_list, list) else [])[:6]:
            symbol = item.get("symbol", "")
            name = item.get("name", item.get("instrument", ""))
            price = item.get("price", 0)
            pct = item.get("changesPercentage", item.get("percentChange", 0))

            style = "green" if pct >= 0 else "red"
            t.add_row(name, symbol, f"${price:.2f}" if price else "-", f"[{style}]{pct:+.2f}%[/{style}]")

        console.print(t)
        console.print()

    # STANDOUTS (significant z-score movers with details)
    standouts = data.get("standouts", {}) or {}
    if standouts and "error" not in standouts and "detail" not in standouts:
        standout_list = standouts if isinstance(standouts, list) else standouts.get("standouts", standouts.get("stocks", []))
        if standout_list:
            console.print(Panel("[bold cyan]Standout Stocks[/bold cyan]", box=box.ROUNDED))

            for stock in (standout_list if isinstance(standout_list, list) else [])[:6]:
                symbol = stock.get("symbol", stock.get("ticker", ""))
                name = stock.get("name", "")
                price = stock.get("price", 0)
                pct = stock.get("changesPercentage", stock.get("percentChange", 0))
                z_score = stock.get("z_score", 0)
                summary = stock.get("summary", "")

                style = "green" if pct >= 0 else "red"
                z_style = "green" if z_score >= 0 else "red"

                console.print(f"  [bold cyan]{symbol}[/bold cyan] - {name}")
                if price:
                    console.print(f"  [{style}]${price:.2f} ({pct:+.2f}%)[/{style}] | Z-Score: [{z_style}]{z_score:+.2f}[/{z_style}]")
                else:
                    console.print(f"  Z-Score: [{z_style}]{z_score:+.2f}[/{z_style}]")
                if summary:
                    if len(summary) > 250:
                        summary = summary[:250] + "..."
                    console.print(f"  [dim]{summary}[/dim]")
                console.print()

    # LATEST HEADLINES (General News)
    headlines = data.get("headlines", {}) or {}
    if headlines and "error" not in headlines and "detail" not in headlines:
        console.print(Panel("[bold white]Latest Headlines[/bold white]", box=box.ROUNDED))

        headline_list = headlines.get("posts", []) if isinstance(headlines, dict) else headlines
        for item in (headline_list if isinstance(headline_list, list) else [])[:6]:
            title = item.get("headline", item.get("title", ""))
            text = item.get("text", "")
            timestamp = item.get("timestamp", item.get("date", item.get("time", "")))
            if timestamp:
                timestamp = str(timestamp)[:10]

            if title:
                console.print(f"  [bold]{title}[/bold]")
                if timestamp:
                    console.print(f"  [dim]{timestamp}[/dim]")
                if text:
                    if len(text) > 200:
                        text = text[:200] + "..."
                    console.print(f"  {text}")
                console.print()


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
    parser.add_argument("symbol", type=str, nargs="?", help="Stock ticker symbol (e.g., RKLB, NVDA)")
    parser.add_argument("--market", action="store_true", help="Fetch main finance page market overview")
    parser.add_argument("--json", action="store_true", help="Output raw JSON data")
    args = parser.parse_args()

    # Market overview mode
    if args.market:
        if not args.json:
            console.print("[dim]Fetching market overview from Perplexity Finance via Camoufox...[/dim]")

        data = fetch_market_overview()

        if args.json:
            print(json.dumps(data, indent=2, default=str))
        else:
            display_market_overview(data)
        return

    # Stock-specific mode (requires symbol)
    if not args.symbol:
        parser.error("Either provide a SYMBOL or use --market flag")

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
