# Next Session TODO List

**Last Updated:** December 6, 2024

## Pre-Session Setup (5 minutes)

- [ ] Sign up for free Finnhub API key: https://finnhub.io/register
- [ ] Sign up for free Alpha Vantage key: https://www.alphavantage.co/support/#api-key
- [ ] Create `external_tools/scrapers/config/api_keys.env` with keys

## Session 1: Finnhub Real-Time (2-3 hours)

### Implementation Tasks

- [ ] Create `external_tools/scrapers/finnhub-realtime` bash wrapper
- [ ] Implement `--quote TICKER` - Real-time quote
- [ ] Implement `--news TICKER` - Company news (last 24h)
- [ ] Implement `--earnings` - Upcoming earnings calendar
- [ ] Implement `--insider TICKER` - Insider transactions
- [ ] Create `finnhub-format.py` with colored output
- [ ] Add `--json` support for automation
- [ ] Test all modes
- [ ] Update `external_tools/scrapers/README.md`
- [ ] Commit and push

### Bonus: WebSocket Streaming

- [ ] Implement `--stream TICKER` for real-time updates
- [ ] Create async WebSocket handler
- [ ] Test continuous streaming

## Session 2: SEC EDGAR CLI (1-2 hours)

### Implementation Tasks

- [ ] Create `external_tools/scrapers/sec-insider` wrapper
- [ ] Implement insider transaction lookup
- [ ] Create `sec-format.py` formatter
- [ ] Filter options: `--buys-only`, `--sells-only`
- [ ] Add ticker search functionality
- [ ] Test against known insider activity
- [ ] Update README.md
- [ ] Commit and push

## Session 3: Alpha Vantage (1-2 hours)

### Implementation Tasks

- [ ] Create `external_tools/scrapers/alphavantage`
- [ ] Implement `--quote TICKER`
- [ ] Implement `--intraday TICKER`
- [ ] Implement `--sentiment TICKER` (news sentiment)
- [ ] Handle rate limits (25/day free tier)
- [ ] Create formatter
- [ ] Update README.md
- [ ] Commit and push

## Session 4: Integration & Workflows (2 hours)

### Integration Tasks

- [ ] Create `morning_research.sh` comprehensive script
- [ ] Create `pre_trade_check.sh` quick validation
- [ ] Create `live_monitor.sh` continuous monitoring
- [ ] Test all workflows end-to-end
- [ ] Document in README.md
- [ ] Commit and push

## Future Sessions (Optional)

### Polygon.io

- [ ] Sign up for API key
- [ ] Implement `polygon-realtime`
- [ ] Add WebSocket support

### Unusual Whales MCP

- [ ] Check API access
- [ ] Install MCP server
- [ ] Create CLI wrapper

---

## Quick Reference

### API Keys Needed

| Service | URL | Free Tier |
|---------|-----|-----------|
| Finnhub | https://finnhub.io/register | 60 calls/min |
| Alpha Vantage | https://www.alphavantage.co/support/#api-key | 25 calls/day |
| Polygon | https://polygon.io/dashboard/signup | 5 calls/min |

### Commands to Test Existing Scrapers

```bash
stocktwits-sentiment --trending
barchart-options --active
shortsqueeze-scanner --min-si 30
finviz-premarket --gainers
pplx-stock-fast NVDA
```

### Git Commands

```bash
# Start of session
git fetch origin feature/enhanced-market-data-streaming
git checkout feature/enhanced-market-data-streaming
git pull

# After each feature
git add -A
git commit -m "feat: Add [scraper name]"
git push origin feature/enhanced-market-data-streaming:claude/enhance-market-data-streaming-01URquGqRMHkVAzanaWD5zsq
```

---

## Files Created This Session

| File | Purpose |
|------|---------|
| `docs/NEXT_SESSION_ROADMAP.md` | Detailed implementation plan |
| `docs/NEXT_SESSION_TODO.md` | This checklist |
| `docs/FINANCIAL_SCRAPING_RESEARCH.md` | Technology research report |

## Files to Create Next Session

| File | Purpose |
|------|---------|
| `external_tools/scrapers/finnhub-realtime` | Finnhub API wrapper |
| `external_tools/scrapers/finnhub-format.py` | Finnhub formatter |
| `external_tools/scrapers/sec-insider` | SEC insider wrapper |
| `external_tools/scrapers/sec-format.py` | SEC formatter |
| `external_tools/scrapers/config/api_keys.env` | API keys (gitignored) |

---

*Ready for next session!*
