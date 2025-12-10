---
description: Fetch Perplexity Finance AI analysis for a stock (pre-market research)
arguments:
  - name: ticker
    description: Stock symbol (e.g., NVDA, AAPL)
    required: true
---

Fetch comprehensive AI-powered stock analysis from Perplexity Finance for $ARGUMENTS.

Run this command to get the data:
```bash
uv run python external_tools/perplexity_finance.py $ARGUMENTS --browser
```

After getting the data, analyze it for day-trading opportunities:
1. **Key Levels**: Identify support/resistance from price movement history
2. **Momentum**: Check recent % moves and volume ratios
3. **Catalysts**: Note any news that could drive intraday volatility
4. **Risk Assessment**: Review bull/bear cases
5. **Entry Strategy**: Recommend entry at resistance (shorts) or support (longs)
