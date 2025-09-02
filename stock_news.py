#!/usr/bin/env python3
"""
Simple NewsAPI Stock News CLI
Fetch stock news using your NewsAPI key from the command line
"""

import requests
from datetime import datetime, timedelta
import json
import argparse
import os
import sys

def search_stock_news(api_key, query, days_back=7, sort_by='relevancy'):
    """
    Search for stock news using NewsAPI
    
    Args:
        api_key: Your NewsAPI key
        query: Stock symbol or company name (e.g., "AAPL" or "Apple")
        days_back: How many days back to search (max 30 for free tier)
        sort_by: Sort order - 'relevancy', 'popularity', or 'publishedAt'
    """
    
    # NewsAPI endpoint
    url = "https://newsapi.org/v2/everything"
    
    # Calculate date range
    to_date = datetime.now()
    from_date = to_date - timedelta(days=min(days_back, 30))
    
    # Parameters for the API call
    params = {
        'q': query,
        'from': from_date.strftime('%Y-%m-%d'),
        'to': to_date.strftime('%Y-%m-%d'),
        'sortBy': sort_by,
        'language': 'en',
        'pageSize': 100,  # Max for free tier
        'apiKey': api_key
    }
    
    # Make the request
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

def get_market_headlines(api_key, country='us'):
    """
    Get top business headlines
    
    Args:
        api_key: Your NewsAPI key
        country: Country code (us, gb, ca, etc.)
    """
    
    url = "https://newsapi.org/v2/top-headlines"
    
    params = {
        'category': 'business',
        'country': country,
        'pageSize': 100,
        'apiKey': api_key
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Error: {response.status_code}")
        return None

def format_articles(data, limit=10, format_type='full'):
    """
    Format and display articles nicely
    
    Args:
        data: API response data
        limit: Number of articles to show
        format_type: 'full', 'compact', or 'urls'
    """
    if not data or data.get('status') != 'ok':
        print("❌ No data available")
        return
    
    articles = data.get('articles', [])
    total = data.get('totalResults', 0)
    
    if total == 0:
        print("📭 No articles found for your search query")
        return
    
    print(f"\n📰 Found {total} articles (showing top {min(limit, len(articles))})\n")
    
    if format_type == 'urls':
        # Just show titles and URLs
        for i, article in enumerate(articles[:limit], 1):
            print(f"{i}. {article.get('title', 'No title')}")
            print(f"   {article.get('url', 'No URL')}\n")
    
    elif format_type == 'compact':
        # Compact format
        for i, article in enumerate(articles[:limit], 1):
            date = article.get('publishedAt', '')[:10]  # Just date, no time
            source = article.get('source', {}).get('name', 'Unknown')
            title = article.get('title', 'No title')[:80]  # Truncate long titles
            print(f"{i:2d}. [{date}] {source:20s} | {title}")
    
    else:  # full
        print("-" * 80)
        for i, article in enumerate(articles[:limit], 1):
            print(f"\n{i}. {article.get('title', 'No title')}")
            print(f"   📍 Source: {article.get('source', {}).get('name', 'Unknown')}")
            print(f"   📅 Date: {article.get('publishedAt', 'Unknown date')}")
            
            desc = article.get('description', 'No description')
            if desc and desc != 'No description':
                # Truncate long descriptions
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                print(f"   📝 Description: {desc}")
            
            print(f"   🔗 URL: {article.get('url', 'No URL')}")
            print("-" * 80)

def save_to_file(data, filename):
    """Save results to JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"💾 Results saved to {filename}")

def main():
    parser = argparse.ArgumentParser(
        description='Search stock news using NewsAPI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for Apple news
  python %(prog)s AAPL
  
  # Search with company name
  python %(prog)s "Tesla stock"
  
  # Search multiple stocks
  python %(prog)s '"MSFT" OR "GOOGL" OR "META"'
  
  # Get today's news only
  python %(prog)s NVDA -d 1
  
  # Get latest news sorted by time
  python %(prog)s SPY -s publishedAt
  
  # Show compact format
  python %(prog)s TSLA -f compact
  
  # Save results to file
  python %(prog)s AMD -o amd_news.json
  
  # Get market headlines
  python %(prog)s --headlines
  
  # Search for trading signals
  python %(prog)s "upgraded OR downgraded" -d 1
        """
    )
    
    # Arguments
    parser.add_argument('query', nargs='?', help='Stock symbol or search term (e.g., AAPL, "Tesla", "earnings report")')
    parser.add_argument('-k', '--api-key', help='NewsAPI key (or set NEWS_API_KEY env variable)')
    parser.add_argument('-d', '--days', type=int, default=7, help='Days to look back (default: 7, max: 30)')
    parser.add_argument('-n', '--number', type=int, default=10, help='Number of articles to show (default: 10)')
    parser.add_argument('-s', '--sort', choices=['relevancy', 'popularity', 'publishedAt'], 
                       default='relevancy', help='Sort order (default: relevancy)')
    parser.add_argument('-f', '--format', choices=['full', 'compact', 'urls'], 
                       default='full', help='Output format (default: full)')
    parser.add_argument('-o', '--output', help='Save results to JSON file')
    parser.add_argument('--headlines', action='store_true', help='Get top business headlines instead of search')
    parser.add_argument('-c', '--country', default='us', help='Country for headlines (default: us)')
    
    args = parser.parse_args()
    
    # Get API key from argument or environment
    api_key = args.api_key or os.getenv('NEWS_API_KEY')
    
    if not api_key:
        print("❌ Error: No API key provided!")
        print("\nPlease provide your NewsAPI key using one of these methods:")
        print("  1. Set environment variable: export NEWS_API_KEY='your_key_here'")
        print("  2. Pass as argument: python script.py AAPL -k your_key_here")
        print("\nGet your free API key at: https://newsapi.org/register")
        sys.exit(1)
    
    # Check if we need a query
    if not args.headlines and not args.query:
        print("❌ Error: Please provide a search query or use --headlines")
        print("Example: python script.py AAPL")
        print("Or: python script.py --headlines")
        sys.exit(1)
    
    # Fetch data
    if args.headlines:
        print(f"📊 Fetching top business headlines for {args.country.upper()}...")
        data = get_market_headlines(api_key, args.country)
    else:
        print(f"🔍 Searching for: {args.query}")
        print(f"📅 Time period: Last {args.days} days")
        print(f"📈 Sort by: {args.sort}")
        data = search_stock_news(api_key, args.query, args.days, args.sort)
    
    if data:
        # Display results
        format_articles(data, args.number, args.format)
        
        # Save to file if requested
        if args.output:
            save_to_file(data, args.output)
    else:
        print("❌ Failed to fetch data")
        sys.exit(1)

if __name__ == "__main__":
    main()
