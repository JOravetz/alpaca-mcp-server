#!/usr/bin/env python3
"""
Yahoo Finance RSS Feed Fetcher
Get real news from Yahoo Finance RSS feeds for any stock
"""

import feedparser
import argparse
import json
from datetime import datetime
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_stock_rss(symbol, limit=20):
    """Fetch RSS feed for a specific stock"""
    # Yahoo Finance RSS URL for specific stock
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
    
    try:
        # Parse the RSS feed
        feed = feedparser.parse(url)
        
        if feed.bozo:
            print(f"⚠️  Warning: Feed parsing issue for {symbol}")
        
        articles = []
        for entry in feed.entries[:limit]:
            article = {
                'title': entry.get('title', 'No title'),
                'link': entry.get('link', ''),
                'published': entry.get('published', ''),
                'published_parsed': entry.get('published_parsed', None),
                'summary': entry.get('summary', ''),
                'source': entry.get('source', {}).get('title', 'Yahoo Finance'),
                'guid': entry.get('id', '')
            }
            
            # Parse and format the date
            if article['published_parsed']:
                dt = datetime.fromtimestamp(time.mktime(article['published_parsed']))
                article['formatted_date'] = dt.strftime('%Y-%m-%d %H:%M')
                # Calculate how long ago
                now = datetime.now()
                diff = now - dt
                if diff.days > 0:
                    article['time_ago'] = f"{diff.days} days ago"
                elif diff.seconds > 3600:
                    article['time_ago'] = f"{diff.seconds // 3600} hours ago"
                else:
                    article['time_ago'] = f"{diff.seconds // 60} minutes ago"
            else:
                article['formatted_date'] = article['published']
                article['time_ago'] = ''
            
            articles.append(article)
        
        return {
            'symbol': symbol,
            'feed_title': feed.feed.get('title', f'{symbol} News'),
            'feed_link': feed.feed.get('link', ''),
            'articles': articles,
            'count': len(articles),
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"❌ Error fetching RSS for {symbol}: {e}")
        return {
            'symbol': symbol,
            'error': str(e),
            'articles': [],
            'count': 0,
            'timestamp': datetime.now().isoformat()
        }

def fetch_market_rss(feed_type='topstories', limit=20):
    """Fetch general market RSS feeds"""
    
    feed_urls = {
        'topstories': 'https://feeds.finance.yahoo.com/rss/2.0/topstories',
        'market': 'https://feeds.finance.yahoo.com/rss/2.0/market-news',
        'world': 'https://feeds.finance.yahoo.com/rss/2.0/world-news',
        'tech': 'https://feeds.finance.yahoo.com/rss/2.0/tech',
        'politics': 'https://feeds.finance.yahoo.com/rss/2.0/politics'
    }
    
    url = feed_urls.get(feed_type, feed_urls['topstories'])
    
    try:
        feed = feedparser.parse(url)
        articles = []
        
        for entry in feed.entries[:limit]:
            article = {
                'title': entry.get('title', 'No title'),
                'link': entry.get('link', ''),
                'published': entry.get('published', ''),
                'summary': entry.get('summary', ''),
                'source': 'Yahoo Finance'
            }
            articles.append(article)
        
        return {
            'feed_type': feed_type,
            'feed_title': feed.feed.get('title', 'Market News'),
            'articles': articles,
            'count': len(articles),
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"❌ Error fetching {feed_type} RSS: {e}")
        return {
            'feed_type': feed_type,
            'error': str(e),
            'articles': [],
            'count': 0
        }

def fetch_multiple_stocks_parallel(symbols, limit=20):
    """Fetch RSS feeds for multiple stocks in parallel"""
    results = {}
    
    with ThreadPoolExecutor(max_workers=min(5, len(symbols))) as executor:
        future_to_symbol = {
            executor.submit(fetch_stock_rss, symbol, limit): symbol 
            for symbol in symbols
        }
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                data = future.result()
                results[symbol] = data
            except Exception as exc:
                print(f"❌ {symbol} generated an exception: {exc}")
                results[symbol] = {'symbol': symbol, 'error': str(exc), 'articles': []}
    
    # Return in original order
    return [results[symbol] for symbol in symbols if symbol in results]

def display_results(data, format_type='full'):
    """Display RSS feed results"""
    
    if isinstance(data, list):
        # Multiple stocks
        for stock_data in data:
            display_single_stock(stock_data, format_type)
            if format_type == 'full':
                print("\n" + "="*80 + "\n")
    else:
        # Single stock or market feed
        if 'symbol' in data:
            display_single_stock(data, format_type)
        else:
            display_market_feed(data, format_type)

def display_single_stock(data, format_type='full'):
    """Display results for a single stock"""
    
    symbol = data.get('symbol', 'Unknown')
    articles = data.get('articles', [])
    
    if data.get('error'):
        print(f"❌ Error for {symbol}: {data['error']}")
        return
    
    print(f"📊 {symbol} - RSS Feed News")
    print(f"📰 Found {len(articles)} articles\n")
    
    if format_type == 'compact':
        for i, article in enumerate(articles, 1):
            time_ago = article.get('time_ago', article.get('published', ''))
            title = article['title'][:80]
            print(f"{i:2d}. [{time_ago:15s}] {title}")
    
    elif format_type == 'urls':
        for i, article in enumerate(articles, 1):
            print(f"{i}. {article['title']}")
            print(f"   {article['link']}\n")
    
    else:  # full
        for i, article in enumerate(articles, 1):
            print(f"{i}. {article['title']}")
            if article.get('time_ago'):
                print(f"   ⏰ {article['time_ago']} ({article.get('formatted_date', '')})")
            elif article.get('published'):
                print(f"   📅 {article['published']}")
            
            if article.get('summary'):
                # Clean up HTML from summary
                summary = article['summary'].replace('<p>', '').replace('</p>', '')
                summary = summary.replace('<b>', '').replace('</b>', '')
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                print(f"   📝 {summary}")
            
            print(f"   🔗 {article['link']}")
            print("-" * 80)

def display_market_feed(data, format_type='full'):
    """Display market/general feed results"""
    
    feed_type = data.get('feed_type', 'Market')
    articles = data.get('articles', [])
    
    print(f"📈 {feed_type.upper()} News Feed")
    print(f"📰 {len(articles)} articles\n")
    
    for i, article in enumerate(articles[:20], 1):
        if format_type == 'compact':
            print(f"{i:2d}. {article['title'][:80]}")
        else:
            print(f"{i}. {article['title']}")
            if article.get('published'):
                print(f"   📅 {article['published']}")
            if format_type == 'full' and article.get('summary'):
                summary = article['summary'][:200] + "..." if len(article['summary']) > 200 else article['summary']
                print(f"   📝 {summary}")
            print(f"   🔗 {article['link']}\n")

def read_symbols_from_file(filepath):
    """Read stock symbols from a file, one per line or comma-separated"""
    symbols = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):  # Skip empty lines and comments
                    if ',' in line:
                        # Handle comma-separated values
                        symbols.extend([s.strip().upper() for s in line.split(',') if s.strip()])
                    else:
                        # Single symbol per line
                        symbols.append(line.upper())
        return list(dict.fromkeys(symbols))  # Remove duplicates while preserving order
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading file {filepath}: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Fetch Yahoo Finance RSS feeds for stocks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single stock RSS feed
  python %(prog)s AAPL
  
  # Multiple stocks
  python %(prog)s AAPL MSFT GOOGL
  
  # Your watchlist
  python %(prog)s IMG KAVL AVAH LZMH SKYT
  
  # Read symbols from file
  python %(prog)s -i watchlist.txt
  python %(prog)s --input-file symbols.txt -n 10
  
  # Combine file input with command-line symbols
  python %(prog)s AAPL -i more_symbols.txt
  
  # Compact format
  python %(prog)s TSLA -f compact
  
  # Limit articles
  python %(prog)s NVDA -n 10
  
  # Market news feeds
  python %(prog)s --market topstories
  python %(prog)s --market market
  python %(prog)s --market tech
  
  # Save to JSON
  python %(prog)s AAPL MSFT -o tech_rss.json
  
  # Combine stocks and market news
  python %(prog)s SPY QQQ --market topstories
  
File Format:
  The input file can contain symbols in these formats:
  - One symbol per line
  - Comma-separated symbols on a line
  - Lines starting with # are treated as comments
  
  Example file:
    # Tech stocks
    AAPL
    MSFT, GOOGL
    NVDA
    # Energy
    XOM
    CVX
        """
    )
    
    parser.add_argument('symbols', nargs='*', help='Stock symbol(s)')
    parser.add_argument('-i', '--input-file', dest='input_file', 
                       help='Read symbols from file (one per line or comma-separated)')
    parser.add_argument('-n', '--number', type=int, default=20, 
                       help='Number of articles to fetch (default: 20)')
    parser.add_argument('-f', '--format', choices=['full', 'compact', 'urls'], 
                       default='full', help='Output format')
    parser.add_argument('-o', '--output', help='Save to JSON file')
    parser.add_argument('--market', choices=['topstories', 'market', 'world', 'tech', 'politics'],
                       help='Fetch market/category news instead of stock-specific')
    
    args = parser.parse_args()
    
    # Collect symbols from both file and command line
    all_symbols = []
    
    # Read from file if provided
    if args.input_file:
        file_symbols = read_symbols_from_file(args.input_file)
        all_symbols.extend(file_symbols)
        print(f"📂 Read {len(file_symbols)} symbols from {args.input_file}")
    
    # Add command-line symbols
    if args.symbols:
        for symbol_arg in args.symbols:
            if ',' in symbol_arg:
                all_symbols.extend([s.strip().upper() for s in symbol_arg.split(',') if s.strip()])
            else:
                all_symbols.append(symbol_arg.strip().upper())
    
    # Remove duplicates while preserving order
    all_symbols = list(dict.fromkeys(all_symbols))
    
    # Validate input
    if not all_symbols and not args.market:
        print("❌ Please provide stock symbols (via command line or file) or use --market option")
        parser.print_help()
        sys.exit(1)
    
    results = []
    
    # Fetch market news if requested
    if args.market:
        print(f"📡 Fetching {args.market} RSS feed...")
        market_data = fetch_market_rss(args.market, args.number)
        results.append(market_data)
        display_results(market_data, args.format)
    
    # Fetch stock-specific news
    if all_symbols:
        if len(all_symbols) == 1:
            print(f"📡 Fetching RSS feed for {all_symbols[0]}...")
            data = fetch_stock_rss(all_symbols[0], args.number)
            results.append(data)
            display_results(data, args.format)
        else:
            print(f"📡 Fetching RSS feeds for {len(all_symbols)} stocks...")
            print(f"   Stocks: {', '.join(all_symbols)}\n")
            stock_results = fetch_multiple_stocks_parallel(all_symbols, args.number)
            results.extend(stock_results)
            display_results(stock_results, args.format)
    
    # Save to file if requested
    if args.output:
        save_data = {
            'timestamp': datetime.now().isoformat(),
            'query': {
                'symbols': all_symbols or [],
                'market': args.market
            },
            'results': results
        }
        
        with open(args.output, 'w') as f:
            json.dump(save_data, f, indent=2)
        print(f"\n💾 Results saved to {args.output}")
    
    # Summary
    total_articles = sum(r.get('count', 0) for r in results)
    print(f"\n✅ Total: {total_articles} articles fetched")

if __name__ == "__main__":
    main()
