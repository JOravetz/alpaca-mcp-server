import os
import sqlite3
import argparse
import requests
import pandas as pd
import pandas_market_calendars as mcal
import logging
from typing import List, Dict, Any, Generator
from datetime import datetime
from time import sleep
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class StockDataFetcher:
    def __init__(self, symbols: List[str], ndays: int, drop: bool, api_key: str, api_secret: str):
        if not api_key or not api_secret:
            raise ValueError("API credentials are required")
            
        self.symbols = symbols
        self.ndays = ndays
        self.drop = drop
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Setup market calendar
        self.calendar = mcal.get_calendar('NYSE')
        
        # Get exact list of trading days
        self.trading_days = self._get_trading_days()
        self.start_date = self.trading_days[0]  # Already in YYYY-MM-DD format
        self.end_date = self.trading_days[-1]
        self.formatted_end_date = self.end_date  # Keep for compatibility
        
        # Check if market is open today
        self.market_open_today = self._is_market_open_today()
        
        # Setup API headers
        self.headers = {
            "accept": "application/json",
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
        }
        
        # Initialize database connection
        self.db_path = "stock_data.db"
        self._setup_database()

    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def read_symbols_from_file(file_path: str) -> List[str]:
        try:
            with open(file_path, "r") as file:
                symbols = [line.strip().upper() for line in file if line.strip()]
            logging.info(f"Read {len(symbols)} symbols from file")
            return symbols
        except FileNotFoundError:
            logging.error(f"Symbol file not found: {file_path}")
            raise

    @staticmethod
    def chunk_symbols(symbols: List[str], size: int = 500) -> Generator[List[str], None, None]:
        """Split symbols into chunks for batch processing"""
        return (symbols[i:i + size] for i in range(0, len(symbols), size))

    def _get_trading_days(self) -> List[str]:
        """Get the last n trading days from NYSE calendar"""
        today = pd.Timestamp.today(tz='UTC')
        adjusted_days = self.ndays + 3  # Add buffer for market holidays
        
        # Get schedule with small buffer to ensure we have enough days
        schedule = self.calendar.schedule(
            start_date=today - pd.Timedelta(days=2*adjusted_days),
            end_date=today
        )
        # Get exact list of trading days formatted as YYYY-MM-DD
        return schedule.index[-adjusted_days:].strftime('%Y-%m-%d').tolist()

    def _is_market_open_today(self) -> bool:
        """Check if the market is open today"""
        today = pd.Timestamp.today(tz='UTC')
        schedule = self.calendar.schedule(start_date=today, end_date=today)
        return len(schedule) > 0

    def _setup_database(self) -> None:
        """Initialize database tables"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            if self.drop:
                placeholders = ','.join('?' for _ in self.symbols)
                cursor.execute(f"DELETE FROM daily_bars WHERE symbol IN ({placeholders})", self.symbols)
                logging.info(f"Dropped entries for symbols: {self.symbols}")
                
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_bars (
                    symbol TEXT,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    trades INTEGER,
                    vwap REAL,
                    PRIMARY KEY (symbol, date)
                )
            """)
            conn.commit()

    def _adjust_start_date(self, current_bars: List[Dict], symbol: str) -> str:
        """Calculate adjusted start date based on number of missing bars"""
        if not current_bars:
            return self.start_date
            
        missing_bars = self.ndays - len(current_bars)
        if missing_bars <= 0:
            return self.start_date
            
        # Get the earliest date from current bars
        earliest_date = current_bars[0]['t'].split('T')[0]
        
        # Calculate new start date using market calendar
        schedule = self.calendar.schedule(
            start_date=pd.Timestamp(earliest_date) - pd.Timedelta(days=missing_bars * 2),
            end_date=pd.Timestamp(earliest_date) - pd.Timedelta(days=1)
        )
        
        if len(schedule) >= missing_bars:
            new_start = schedule.index[-missing_bars].strftime('%Y-%m-%d')
            logging.info(f"Adjusting start date for {symbol} to {new_start} to fetch missing {missing_bars} bars")
            return new_start
        return self.start_date

    def fetch_data(self, symbol_list: str, max_retries: int = 3) -> Dict[str, Any]:
        """Fetch stock data with retry logic"""
        base_url = "https://data.alpaca.markets/v2/stocks/bars"
        params = {
            'symbols': symbol_list,
            'timeframe': '1Day',
            'start': self.start_date,
            'limit': 10000,
            'adjustment': 'split',
            'feed': 'sip',
            'sort': 'asc'
        }
        
        all_data = {}
        page_token = None
        
        while True:
            if page_token:
                params['page_token'] = page_token
                
            for attempt in range(max_retries):
                try:
                    response = requests.get(base_url, headers=self.headers, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    for symbol, bars in data.get('bars', {}).items():
                        all_data.setdefault(symbol, []).extend(bars)
                        
                    page_token = data.get('next_page_token')
                    if not page_token:
                        return all_data
                    break
                    
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        logging.error(f"Failed to fetch data after {max_retries} attempts for {symbol_list}: {str(e)}")
                        raise
                    sleep_time = 2 ** attempt
                    logging.warning(f"Attempt {attempt + 1} failed. Retrying in {sleep_time}s...")
                    sleep(sleep_time)
                    
        return all_data

    def process_data(self) -> None:
        """Process data in parallel with proper error handling"""
        symbol_chunks = list(self.chunk_symbols(self.symbols))
        processed_count = 0
        error_count = 0
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_symbols = {
                executor.submit(self.fetch_data, ",".join(chunk)): chunk 
                for chunk in symbol_chunks
            }
            
            for future in as_completed(future_to_symbols):
                symbol_chunk = future_to_symbols[future]
                try:
                    data = future.result()
                    with self.get_db_connection() as conn:
                        cursor = conn.cursor()
                        for symbol, bars in data.items():
                            try:
                                self._store_bars(cursor, symbol, bars)
                                processed_count += 1
                            except sqlite3.Error as e:
                                logging.error(f"Database error for {symbol}: {e}")
                                error_count += 1
                                continue
                        conn.commit()
                except Exception as e:
                    logging.error(f"Error processing chunk {symbol_chunk}: {e}")
                    error_count += len(symbol_chunk)

        logging.info(f"Processing complete. Processed: {processed_count}, Errors: {error_count}")

    def _store_bars(self, cursor: sqlite3.Cursor, symbol: str, bars: List[Dict[str, Any]]) -> None:
        """Store bar data efficiently using executemany"""
        data = [
            (
                symbol,
                bar['t'].split("T")[0],
                bar['o'],
                bar['h'],
                bar['l'],
                bar['c'],
                bar['v'],
                bar['n'],
                bar['vw']
            )
            for bar in bars
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO daily_bars 
            (symbol, date, open, high, low, close, volume, trades, vwap)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)

    def _fetch_latest_chunk(self, symbol_chunk: List[str], max_retries: int = 3) -> Dict[str, Any]:
        """Fetch latest data for a chunk of symbols with retry logic"""
        url = "https://data.alpaca.markets/v2/stocks/bars/latest"
        params = {'symbols': ','.join(symbol_chunk), 'feed': 'sip'}
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.json().get('bars', {})
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    logging.error(f"Failed to fetch latest data after {max_retries} attempts for chunk: {str(e)}")
                    raise
                sleep_time = 2 ** attempt
                logging.warning(f"Attempt {attempt + 1} failed. Retrying in {sleep_time}s...")
                sleep(sleep_time)
        
        return {}

    def update_latest_data(self) -> None:
        """Update database with latest market data using concurrent processing"""
        if not self.market_open_today:
            logging.info("Market is not open today. Skipping latest data update.")
            return
            
        try:
            # Split symbols into chunks of 500 (API limit)
            symbol_chunks = list(self.chunk_symbols(self.symbols, size=500))
            processed_count = 0
            error_count = 0
            
            with ThreadPoolExecutor(max_workers=8) as executor:
                future_to_symbols = {
                    executor.submit(self._fetch_latest_chunk, chunk): chunk 
                    for chunk in symbol_chunks
                }
                
                with self.get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    for future in as_completed(future_to_symbols):
                        symbol_chunk = future_to_symbols[future]
                        try:
                            latest_data = future.result()
                            
                            for symbol, latest_bar in latest_data.items():
                                try:
                                    self._update_latest_bar(cursor, symbol, latest_bar)
                                    processed_count += 1
                                except sqlite3.Error as e:
                                    logging.error(f"Database error updating latest data for {symbol}: {e}")
                                    error_count += 1
                                    continue
                            
                            conn.commit()  # Commit after each chunk is processed
                            
                        except Exception as e:
                            logging.error(f"Error processing latest data chunk {symbol_chunk}: {e}")
                            error_count += len(symbol_chunk)
            
            logging.info(f"Latest data update complete. Processed: {processed_count}, Errors: {error_count}")
                
        except Exception as e:
            logging.error(f"Failed to update latest data: {e}")
            raise

    def _update_latest_bar(self, cursor: sqlite3.Cursor, symbol: str, latest_bar: Dict[str, Any]) -> None:
        """Update a single symbol's latest data"""
        latest_date = latest_bar['t'].split("T")[0]
        
        cursor.execute(
            "SELECT date, close FROM daily_bars WHERE symbol = ? ORDER BY date DESC LIMIT 1",
            (symbol,)
        )
        last_entry = cursor.fetchone()

        if not last_entry or last_entry[0] < latest_date:
            self._store_bars(cursor, symbol, [latest_bar])
            logging.info(f"Updated {symbol} with new data for {latest_date}")
        elif last_entry[0] == latest_date and last_entry[1] != latest_bar['c']:
            cursor.execute(
                "UPDATE daily_bars SET close = ? WHERE symbol = ? AND date = ?",
                (latest_bar['c'], symbol, latest_date)
            )
            logging.info(f"Updated {symbol} close price for {latest_date}")

def setup_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch historical bar data for specified symbols",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--symbols", "-s", type=str, help="Comma-separated list of stock symbols")
    group.add_argument("--list", "-l", type=str, help="File path containing stock symbols, one per line")
    
    parser.add_argument("--ndays", "-n", type=int, default=504, 
                       help="Number of trading days to fetch")
    parser.add_argument("--drop", action="store_true",
                       help="Drop existing data before fetching new data")
    
    return parser.parse_args()

def main():
    try:
        args = setup_args()
        
        api_key = os.getenv("APCA_API_KEY_ID")
        api_secret = os.getenv("APCA_API_SECRET_KEY")
        
        if not api_key or not api_secret:
            raise ValueError("Missing API credentials. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables.")
        
        symbols = (StockDataFetcher.read_symbols_from_file(args.list) 
                  if args.list 
                  else args.symbols.split(","))
        
        fetcher = StockDataFetcher(symbols, args.ndays, args.drop, api_key, api_secret)
        fetcher.process_data()
        fetcher.update_latest_data()
        
    except Exception as e:
        logging.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    main()
