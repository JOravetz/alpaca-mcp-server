#!/usr/bin/env python3
"""
Yahoo Finance News Scraper
Scrape latest news for any stock symbol from Yahoo Finance
Supports parallel fetching for up to 20 stocks
"""

import requests
from bs4 import BeautifulSoup
import argparse
import json
import sys
from datetime import datetime
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import warnings
warnings.filterwarnings('ignore')

class YahooFinanceScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def get_stock_info(self, symbol):
        """Get basic stock info and current price"""
        url = f"https://finance.yahoo.com/quote/{symbol}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            info = {}
            
            # Get company name - try multiple selectors
            name_elem = soup.find('h1', class_='D(ib)')
            if not name_elem:
                name_elem = soup.find('h1')
            if not name_elem:
                # Try to find from meta tags
                meta_title = soup.find('meta', property='og:title')
                if meta_title:
                    title_text = meta_title.get('content', '')
                    if '(' in title_text and ')' in title_text:
                        info['company_name'] = title_text.split('(')[0].strip()
            else:
                info['company_name'] = name_elem.text.strip()
            
            # Get current price - try multiple approaches
            price_elem = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})
            if not price_elem:
                # Try alternative selectors
                price_elem = soup.find('span', {'data-field': 'regularMarketPrice'})
            if not price_elem:
                # Look for price in data attributes
                price_elem = soup.find(attrs={'data-symbol': symbol.upper(), 'data-field': 'regularMarketPrice'})
            if not price_elem:
                # Try regex search in page text
                price_match = re.search(r'"regularMarketPrice":\s*{\s*"raw":\s*([0-9.]+)', response.text)
                if price_match:
                    info['current_price'] = price_match.group(1)
            
            if price_elem and not info.get('current_price'):
                info['current_price'] = price_elem.text.strip()
            
            # Get price change
            change_elem = soup.find('fin-streamer', {'data-field': 'regularMarketChange'})
            if not change_elem:
                change_elem = soup.find('span', {'data-field': 'regularMarketChange'})
            if not change_elem:
                change_match = re.search(r'"regularMarketChange":\s*{\s*"raw":\s*([0-9.-]+)', response.text)
                if change_match:
                    change_val = float(change_match.group(1))
                    info['price_change'] = f"{change_val:+.2f}"
            
            if change_elem and not info.get('price_change'):
                info['price_change'] = change_elem.text.strip()
            
            # Get percent change
            percent_elem = soup.find('fin-streamer', {'data-field': 'regularMarketChangePercent'})
            if not percent_elem:
                percent_elem = soup.find('span', {'data-field': 'regularMarketChangePercent'})
            if not percent_elem:
                percent_match = re.search(r'"regularMarketChangePercent":\s*{\s*"raw":\s*([0-9.-]+)', response.text)
                if percent_match:
                    percent_val = float(percent_match.group(1))
                    info['percent_change'] = f"{percent_val:+.2f}%"
            
            if percent_elem and not info.get('percent_change'):
                percent_text = percent_elem.text.strip().replace('(', '').replace(')', '')
                info['percent_change'] = percent_text
            
            return info
        except Exception as e:
            print(f"⚠️  Warning: Could not fetch stock info: {e}")
            return {}
    
    def fetch_article_content(self, url, timeout=5):
        """Fetch the actual article content from a URL"""
        try:
            # Skip non-Yahoo Finance URLs by default to save time
            if 'yahoo.com' not in url and 'finance.yahoo' not in url:
                # For external sites, we'll try but with shorter timeout
                timeout = 3
            
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            content = []
            
            # Yahoo Finance article structure
            if 'yahoo' in url:
                # Method 1: Look for caas-body (common Yahoo article body)
                article_body = soup.find('div', class_='caas-body')
                if article_body:
                    paragraphs = article_body.find_all('p')
                    content = [p.text.strip() for p in paragraphs if p.text.strip()]
                
                # Method 2: Look for article body with different class
                if not content:
                    article_body = soup.find('div', {'class': re.compile('article-wrap|story-body')})
                    if article_body:
                        paragraphs = article_body.find_all('p')
                        content = [p.text.strip() for p in paragraphs if p.text.strip()]
            
            # Generic article extraction for other sites
            if not content:
                # Try common article selectors
                selectors = [
                    'article', 
                    'div[class*="article"]',
                    'div[class*="content"]',
                    'div[class*="story"]',
                    'main'
                ]
                
                for selector in selectors:
                    article_elem = soup.select_one(selector)
                    if article_elem:
                        paragraphs = article_elem.find_all('p')
                        content = [p.text.strip() for p in paragraphs if len(p.text.strip()) > 50]
                        if content:
                            break
            
            # If still no content, get all paragraphs as fallback
            if not content:
                all_p = soup.find_all('p')
                content = [p.text.strip() for p in all_p if len(p.text.strip()) > 100]
            
            # Join and clean content
            if content:
                full_text = ' '.join(content)
                # Remove extra whitespace
                full_text = ' '.join(full_text.split())
                # Limit to reasonable length
                if len(full_text) > 5000:
                    full_text = full_text[:5000] + '...'
                return full_text
            
            return None
            
        except Exception as e:
            # Silent fail - we'll just not have the content
            return None
    
    def scrape_news(self, symbol, fetch_content=False, max_content_fetch=5):
        """Scrape news articles for a given stock symbol
        
        Args:
            symbol: Stock symbol
            fetch_content: Whether to fetch full article content
            max_content_fetch: Maximum number of articles to fetch content for
        """
        # Yahoo Finance news URL
        url = f"https://finance.yahoo.com/quote/{symbol}/news"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching data: {e}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = []
        
        # Find news items - Yahoo Finance uses different structures
        # Try multiple selectors as Yahoo changes their HTML frequently
        news_items = []
        
        # Method 1: Look for news stream items (current structure)
        stream_items = soup.find_all('li', class_=re.compile('js-stream-content|stream-item'))
        news_items.extend(stream_items)
        
        # Method 2: Look for modern Yahoo Finance news structure
        modern_news = soup.find_all('li', class_=re.compile(r'Ov\(h\)|js-content-viewer'))
        news_items.extend(modern_news)
        
        # Method 3: Look for h3 tags with links (common pattern) 
        h3_items = soup.find_all('h3')
        for h3 in h3_items:
            link = h3.find('a', href=True)
            if link and 'news' in link.get('href', '').lower():
                # Only add news-related links, not navigation
                parent = h3.parent or h3
                if parent not in news_items:
                    news_items.append(parent)
        
        # Method 4: Look for article elements
        article_items = soup.find_all('article')
        news_items.extend(article_items)
        
        # Method 5: Look for specific news sections with updated classes
        news_sections = soup.find_all('div', class_=re.compile('StreamMegaItem|Cf|NewsItem|story'))
        news_items.extend(news_sections)
        
        # Method 6: Search for JSON data containing news (fallback)
        if not news_items:
            # Try to extract from JSON-LD or embedded data
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'news' in script.string.lower():
                    # Look for news data patterns
                    news_pattern = r'"title":\s*"([^"]+)".*?"url":\s*"([^"]+)"'
                    matches = re.findall(news_pattern, script.string)
                    for title, url in matches[:5]:  # Limit to first 5 matches
                        if 'finance.yahoo.com' in url or 'news' in url:
                            # Create a fake element structure for consistent processing
                            fake_item = type('obj', (object,), {
                                'find': lambda self, *args, **kwargs: type('obj', (object,), {
                                    'text': title,
                                    'get': lambda self, key: url if key == 'href' else None,
                                    '__getitem__': lambda self, key: url if key == 'href' else None
                                })(),
                                'find_all': lambda self, *args, **kwargs: []
                            })()
                            news_items.append(fake_item)
        
        # Process found items
        seen_titles = set()  # Avoid duplicates
        seen_urls = set()    # Avoid duplicate URLs
        
        for item in news_items:
            article = {}
            
            # Extract title and URL - try multiple approaches
            link = item.find('a', href=True)
            if not link:
                # Try finding any link in the item
                all_links = item.find_all('a', href=True) if hasattr(item, 'find_all') else []
                for potential_link in all_links:
                    if potential_link.text.strip() and len(potential_link.text.strip()) > 10:
                        link = potential_link
                        break
                
                if not link:
                    continue
            
            # Get title from link text or nearby elements
            title = link.text.strip()
            if not title or len(title) < 10:
                # Try to find title in parent elements
                parent = item
                for _ in range(3):  # Check up to 3 levels up
                    if parent and hasattr(parent, 'find'):
                        h_tags = parent.find_all(['h1', 'h2', 'h3', 'h4'])
                        for h_tag in h_tags:
                            if h_tag.text.strip() and len(h_tag.text.strip()) > 10:
                                title = h_tag.text.strip()
                                break
                        if title and len(title) > 10:
                            break
                    parent = getattr(parent, 'parent', None)
            
            # Skip if still no good title or already seen
            if not title or len(title) < 10 or title in seen_titles:
                continue
                
            # Clean up title
            title = re.sub(r'\s+', ' ', title).strip()
            
            # Filter out navigation items
            if any(nav_word in title.lower() for nav_word in ['news', 'life', 'entertainment', 'sport', 'finance', 'yahoo'] if len(title.split()) < 3):
                continue
            
            seen_titles.add(title)
            article['title'] = title
            
            # Build full URL if needed
            href = link.get('href', '') if hasattr(link, 'get') else getattr(link, 'href', '')
            if not href:
                continue
                
            # Skip if URL already seen
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            if href.startswith('/'):
                article['url'] = f"https://finance.yahoo.com{href}"
            elif not href.startswith('http'):
                article['url'] = f"https://finance.yahoo.com/{href}"
            else:
                article['url'] = href
                
            # Skip obviously wrong URLs (navigation, etc.)
            if any(skip_pattern in article['url'].lower() for skip_pattern in [
                '/lifestyle/', '/entertainment/', 'yahoo.com/$', 'yahoo.com/life', 
                'yahoo.com/news/$', 'yahoo.com/finance/$'
            ]):
                continue
            
            # Extract source
            source = None
            source_elem = item.find('div', class_='C(#959595)')
            if source_elem:
                source = source_elem.text.strip()
            else:
                # Try alternative source location
                source_elem = item.find('span', class_='Fz(11px)')
                if source_elem:
                    source = source_elem.text.strip()
            
            if source:
                # Clean up source (remove time if mixed with source)
                source = source.split('•')[0].strip()
                article['source'] = source
            
            # Extract time
            time_elem = item.find('time')
            if time_elem:
                article['time'] = time_elem.text.strip()
            else:
                # Look for relative time text
                time_text = None
                for span in item.find_all('span'):
                    text = span.text.strip()
                    if any(x in text.lower() for x in ['ago', 'yesterday', 'hour', 'minute', 'day']):
                        time_text = text
                        break
                if time_text:
                    article['time'] = time_text
            
            # Extract description/summary if available
            desc_elem = item.find('p')
            if desc_elem:
                article['description'] = desc_elem.text.strip()
            
            # Only add if we have at least title and URL
            if article.get('title') and article.get('url'):
                articles.append(article)
        
        # Fetch actual article content if requested
        if fetch_content and articles:
            print(f"   📄 Fetching article content...")
            content_fetched = 0
            for article in articles[:max_content_fetch]:
                if content_fetched >= max_content_fetch:
                    break
                
                content = self.fetch_article_content(article['url'])
                if content:
                    article['full_content'] = content
                    content_fetched += 1
                    print(f"      ✓ Fetched content for: {article['title'][:50]}...")
        
        return articles
    
    def scrape_analysis(self, symbol):
        """Scrape analyst recommendations and price targets"""
        url = f"https://finance.yahoo.com/quote/{symbol}/analysis"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            analysis = {}
            
            # Look for recommendation trends
            tables = soup.find_all('table')
            for table in tables:
                # Check if this is the recommendation table
                headers = [th.text.strip() for th in table.find_all('th')]
                if 'Strong Buy' in ' '.join(headers):
                    rows = table.find_all('tr')[1:]  # Skip header
                    if rows:
                        latest_row = rows[0]
                        cells = latest_row.find_all('td')
                        if len(cells) >= 5:
                            analysis['recommendations'] = {
                                'strong_buy': cells[0].text.strip(),
                                'buy': cells[1].text.strip(),
                                'hold': cells[2].text.strip(),
                                'sell': cells[3].text.strip(),
                                'strong_sell': cells[4].text.strip()
                            }
                
                # Check for price targets
                if 'Low' in headers and 'Current' in headers:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 3:
                            analysis['price_targets'] = {
                                'low': cells[0].text.strip(),
                                'average': cells[1].text.strip(),
                                'high': cells[2].text.strip()
                            }
                            break
            
            return analysis
        except Exception as e:
            print(f"⚠️  Warning: Could not fetch analysis data: {e}")
            return {}

def format_output(data, format_type='full', symbol=''):
    """Format and display the scraped data"""
    
    if not data or not data.get('news'):
        print("📭 No news articles found")
        return
    
    # Display stock info if available
    if data.get('info'):
        info = data['info']
        print(f"\n📊 {info.get('company_name', symbol.upper())}")
        if info.get('current_price'):
            price_color = "🟢" if info.get('price_change', '').startswith('+') else "🔴"
            print(f"   Price: ${info['current_price']} {price_color} {info.get('price_change', '')} ({info.get('percent_change', '')})")
        print()
    
    # Display analysis if available
    if data.get('analysis'):
        analysis = data['analysis']
        if analysis.get('recommendations'):
            rec = analysis['recommendations']
            print("📈 Analyst Recommendations:")
            print(f"   Strong Buy: {rec.get('strong_buy', 'N/A')} | Buy: {rec.get('buy', 'N/A')} | Hold: {rec.get('hold', 'N/A')} | Sell: {rec.get('sell', 'N/A')} | Strong Sell: {rec.get('strong_sell', 'N/A')}")
        
        if analysis.get('price_targets'):
            targets = analysis['price_targets']
            print(f"🎯 Price Targets:")
            print(f"   Low: ${targets.get('low', 'N/A')} | Average: ${targets.get('average', 'N/A')} | High: ${targets.get('high', 'N/A')}")
        print()
    
    # Display news
    articles = data['news']
    print(f"📰 Latest News ({len(articles)} articles found)\n")
    
    if format_type == 'compact':
        for i, article in enumerate(articles, 1):
            time_str = article.get('time', '')
            source = article.get('source', 'Unknown')
            title = article['title'][:80]  # Truncate long titles
            has_content = "📄" if article.get('full_content') else ""
            print(f"{i:2d}. [{time_str:12s}] {source:15s} | {title} {has_content}")
    
    elif format_type == 'urls':
        for i, article in enumerate(articles, 1):
            has_content = " [content fetched]" if article.get('full_content') else ""
            print(f"{i}. {article['title']}{has_content}")
            print(f"   {article['url']}\n")
    
    else:  # full
        print("-" * 80)
        for i, article in enumerate(articles, 1):
            print(f"\n{i}. {article['title']}")
            if article.get('source'):
                print(f"   📍 Source: {article['source']}")
            if article.get('time'):
                print(f"   ⏰ Time: {article['time']}")
            if article.get('description'):
                desc = article['description']
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                print(f"   📝 Summary: {desc}")
            
            # Display full content if available
            if article.get('full_content'):
                print(f"   📄 Article Content:")
                content = article['full_content']
                # Show first 500 chars in console, full content is in JSON
                if len(content) > 500:
                    display_content = content[:500] + "..."
                else:
                    display_content = content
                # Indent the content
                for line in display_content.split('\n'):
                    print(f"      {line}")
            
            print(f"   🔗 {article['url']}")
            print("-" * 80)

def fetch_stock_data(scraper, symbol, args):
    """Fetch data for a single stock (used for parallel processing)"""
    try:
        print(f"🔍 Fetching {symbol}...")
        
        data = {'symbol': symbol, 'timestamp': datetime.now().isoformat()}
        
        # Get stock info
        data['info'] = scraper.get_stock_info(symbol)
        
        # Get news with content if requested
        news = scraper.scrape_news(symbol, 
                                  fetch_content=args.content, 
                                  max_content_fetch=args.max_content)
        
        if news is None:
            print(f"⚠️  Warning: Failed to fetch news for {symbol}")
            data['news'] = []
            data['error'] = 'Failed to fetch news'
        else:
            # Limit number of articles
            if news and args.number:
                news = news[:args.number]
            data['news'] = news
        
        # Get analysis if requested
        if args.analysis:
            data['analysis'] = scraper.scrape_analysis(symbol)
        
        return data
    except Exception as e:
        print(f"❌ Error processing {symbol}: {e}")
        return {
            'symbol': symbol, 
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'news': []
        }

def process_parallel(symbols, args):
    """Process multiple stocks in parallel"""
    scraper = YahooFinanceScraper()
    all_data = []
    
    # Limit to 20 stocks maximum for parallel processing
    if len(symbols) > 20:
        print(f"⚠️  Warning: Processing only first 20 stocks out of {len(symbols)} provided")
        symbols = symbols[:20]
    
    print(f"⚡ Fetching data for {len(symbols)} stocks in parallel...")
    print(f"   Stocks: {', '.join(symbols)}\n")
    
    # Use ThreadPoolExecutor for parallel fetching
    # Max 5 workers to be respectful to Yahoo's servers
    max_workers = min(5, len(symbols))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_symbol = {
            executor.submit(fetch_stock_data, YahooFinanceScraper(), symbol, args): symbol 
            for symbol in symbols
        }
        
        # Collect results as they complete
        results = {}
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                data = future.result()
                results[symbol] = data
                
                # Quick status update
                news_count = len(data.get('news', []))
                if data.get('error'):
                    print(f"   ❌ {symbol}: Error - {data.get('error')}")
                else:
                    print(f"   ✅ {symbol}: {news_count} articles found")
            except Exception as exc:
                print(f"   ❌ {symbol}: Exception - {exc}")
                results[symbol] = {
                    'symbol': symbol,
                    'timestamp': datetime.now().isoformat(),
                    'error': str(exc),
                    'news': []
                }
    
    # Sort results to maintain original order
    for symbol in symbols:
        if symbol in results:
            all_data.append(results[symbol])
    
    return all_data

def process_sequential(symbols, args):
    """Process stocks sequentially (fallback or when --sequential is used)"""
    scraper = YahooFinanceScraper()
    all_data = []
    
    for idx, symbol in enumerate(symbols):
        # Add separator for multiple stocks
        if idx > 0 and (args.separator or len(symbols) > 1):
            print("\n" + "=" * 80 + "\n")
        
        print(f"🔍 [{idx+1}/{len(symbols)}] Fetching news for {symbol} from Yahoo Finance...")
        
        data = fetch_stock_data(scraper, symbol, args)
        all_data.append(data)
        
        # Display results
        format_output(data, args.format, symbol)
        
        # Summary for this stock
        news = data.get('news', [])
        if news:
            print(f"\n✅ Found {len(news)} news articles for {symbol}")
        else:
            print(f"\n📭 No news found for {symbol}")
        
        # Small delay between requests to be respectful
        if idx < len(symbols) - 1:
            time.sleep(0.5)
    
    return all_data

def save_to_file(data, filename):
    """Save results to JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"💾 Results saved to {filename}")

def main():
    parser = argparse.ArgumentParser(
        description='Scrape latest news from Yahoo Finance with optional full article content',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get Apple news (headlines only)
  python %(prog)s AAPL
  
  # Get news WITH full article content
  python %(prog)s AAPL -c
  
  # Get multiple stocks with content (fetches 3 articles per stock)
  python %(prog)s AAPL MSFT GOOGL -c --max-content 3
  
  # Your watchlist with full content
  python %(prog)s IMG KAVL AVAH LZMH SKYT -c
  
  # Compact format with content indicators
  python %(prog)s IMG KAVL -f compact -c
  
  # Save everything including article content
  python %(prog)s AAPL -c -o apple_full.json
  
  # Get content for top 5 articles only
  python %(prog)s TSLA -c --max-content 5 -n 10
        """
    )
    
    parser.add_argument('symbols', nargs='+', help='Stock symbol(s) - space or comma separated (max 20 for parallel)')
    parser.add_argument('-n', '--number', type=int, default=20, help='Maximum number of articles per stock (default: 20)')
    parser.add_argument('-f', '--format', choices=['full', 'compact', 'urls'], default='full', 
                       help='Output format (default: full)')
    parser.add_argument('-o', '--output', help='Save results to JSON file')
    parser.add_argument('-a', '--analysis', action='store_true', 
                       help='Include analyst recommendations and price targets')
    parser.add_argument('-c', '--content', action='store_true',
                       help='Fetch full article content (slower but gets actual article text)')
    parser.add_argument('--max-content', type=int, default=5,
                       help='Maximum articles to fetch content for per stock (default: 5)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-s', '--separator', action='store_true', 
                       help='Add separator between multiple stocks')
    parser.add_argument('--sequential', action='store_true',
                       help='Process stocks sequentially instead of in parallel')
    
    args = parser.parse_args()
    
    # Parse symbols - handle both space and comma separated
    symbols = []
    for symbol_arg in args.symbols:
        # Split by comma if present
        if ',' in symbol_arg:
            symbols.extend([s.strip().upper() for s in symbol_arg.split(',') if s.strip()])
        else:
            symbols.append(symbol_arg.strip().upper())
    
    # Remove duplicates while preserving order
    seen = set()
    symbols = [s for s in symbols if not (s in seen or seen.add(s))]
    
    if not symbols:
        print("❌ No valid symbols provided")
        sys.exit(1)
    
    # Warn if fetching content for many stocks
    if args.content and len(symbols) > 3:
        print(f"⚠️  Note: Fetching article content for {len(symbols)} stocks may take a while...")
        print(f"   (Fetching up to {args.max_content} articles per stock)\n")
    
    # Start timing
    start_time = time.time()
    
    # Process stocks
    if len(symbols) == 1:
        # Single stock - always sequential
        all_data = process_sequential(symbols, args)
    elif args.sequential or (args.content and len(symbols) > 5):
        # Force sequential if fetching content for many stocks
        print(f"📋 Processing {len(symbols)} stocks sequentially...")
        if args.content:
            print("   (Sequential mode auto-enabled for content fetching with 5+ stocks)")
        all_data = process_sequential(symbols, args)
    else:
        # Multiple stocks - use parallel processing
        all_data = process_parallel(symbols, args)
        
        # Display results after parallel fetch
        print("\n" + "=" * 80 + "\n")
        print("📊 DETAILED RESULTS\n")
        for data in all_data:
            print("=" * 80)
            format_output(data, args.format, data['symbol'])
    
    # Save all data if requested
    if args.output:
        if len(symbols) == 1:
            save_to_file(all_data[0], args.output)
        else:
            # Save as array of results for multiple symbols
            save_data = {
                'symbols': symbols,
                'timestamp': datetime.now().isoformat(),
                'total_stocks': len(symbols),
                'content_fetched': args.content,
                'results': all_data
            }
            save_to_file(save_data, args.output)
    
    # Final summary
    elapsed_time = time.time() - start_time
    
    if len(symbols) > 1:
        print("\n" + "=" * 80)
        print(f"\n📊 SUMMARY: Processed {len(symbols)} stocks in {elapsed_time:.1f} seconds")
        
        total_articles = 0
        total_with_content = 0
        for data in all_data:
            symbol = data['symbol']
            news_count = len(data.get('news', []))
            content_count = sum(1 for article in data.get('news', []) if article.get('full_content'))
            total_articles += news_count
            total_with_content += content_count
            
            if data.get('error'):
                print(f"   {symbol}: ❌ Error - {data.get('error')}")
            else:
                # Add price info if available
                info = data.get('info', {})
                price_str = ""
                if info.get('current_price'):
                    price_str = f" - ${info['current_price']}"
                    if info.get('percent_change'):
                        price_str += f" ({info['percent_change']})"
                
                content_str = f" [{content_count} with content]" if args.content else ""
                print(f"   {symbol}: {news_count} articles{content_str}{price_str}")
        
        print(f"\n   Total: {total_articles} articles across {len(symbols)} stocks")
        if args.content:
            print(f"   Content fetched: {total_with_content} articles")
        print(f"   Speed: {elapsed_time/len(symbols):.1f} seconds per stock (average)")
    else:
        content_count = sum(1 for article in all_data[0].get('news', []) if article.get('full_content'))
        if args.content and content_count > 0:
            print(f"\n📄 Fetched full content for {content_count} articles")
        print(f"\n⏱️  Completed in {elapsed_time:.1f} seconds")

if __name__ == "__main__":
    main()
