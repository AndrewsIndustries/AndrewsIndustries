import pandas as pd
import time
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.common.exceptions import APIError
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.common.enums import Sort
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Load environment variables from .env file
load_dotenv()

# Configure logging: Outputs to both a file (trade_bot.log) and the console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trade_bot.log"),
        logging.StreamHandler()
    ]
)

# Authentication configuration
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTQYftjQ9fHLfDzmWIZ7QFdW0SplgDJPVpaaHKirmWkOERgEMNSr2yPcwXUNKRnxSwFRPTTQf8maQjs/pub?gid=134813518&single=true&output=csv"

# Initialize Modern SDK clients
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=("paper" in BASE_URL))
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
QTY_PER_TRADE = 10

def fetch_tickers_from_sheet(url):
    """Fetches tickers from the synchronized CSV endpoint."""
    try:
        df = pd.read_csv(url)
        tickers = [str(t).strip().upper() for t in df.iloc[:, 0].dropna().unique().tolist() 
                   if str(t).strip() and len(str(t).strip()) <= 5]
        logging.info(f"Loaded {len(tickers)} tickers from sheet: {tickers}")
        return tickers
    except Exception as e:
        logging.error(f"Error fetching tickers from spreadsheet: {e}")
        return []

def get_market_data(symbol):
    """Retrieves recent hourly bars for the specified asset."""
    try:
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Hour,
            start=datetime.now() - timedelta(days=7)
        )
        return data_client.get_stock_bars(request_params).df
    except Exception as e:
        logging.error(f"Could not retrieve historical bars for {symbol}: {e}")
        return None

def calculate_strategy(df):
    """
    Shared SMA Crossover Strategy (Matches Gemini Bots).
    Returns 'BUY', 'SELL', or 'HOLD'.
    """
    if df is None or len(df) < 30:
        return "HOLD"
        
    df = df.copy()
    if isinstance(df.index, pd.MultiIndex):
        close_prices = df['close'].reset_index(level=0, drop=True)
    else:
        close_prices = df['close']
    
    sma_fast = close_prices.rolling(window=10).mean().dropna()
    sma_slow = close_prices.rolling(window=30).mean().dropna()

    if len(sma_fast) < 2 or len(sma_slow) < 2:
        return "HOLD"
    
    if sma_fast.iloc[-2] <= sma_slow.iloc[-2] and sma_fast.iloc[-1] > sma_slow.iloc[-1]:
        return "BUY"
    elif sma_fast.iloc[-2] >= sma_slow.iloc[-2] and sma_fast.iloc[-1] < sma_slow.iloc[-1]:
        return "SELL"
    return "HOLD"

def execute_trade(symbol, signal, quantity):
    """Handles order placement and position checks."""
    try:
        pos = None
        try: pos = trading_client.get_open_position(symbol)
        except APIError: pos = None

        if signal == "BUY" and pos is None:
            logging.info(f"[{symbol}] Signal: BUY {quantity} shares.")
            req = MarketOrderRequest(symbol=symbol, qty=quantity, side=OrderSide.BUY, time_in_force=TimeInForce.GTC)
            trading_client.submit_order(req)
        elif signal == "SELL" and pos is not None:
            logging.info(f"[{symbol}] Signal: CLOSING position of {pos.qty} shares.")
            trading_client.close_position(symbol)
        else:
            logging.info(f"[{symbol}] Signal: HOLD / Position requirement not met.")
    except Exception as e:
        logging.error(f"Error executing trade for {symbol}: {e}")

def run_bot():
    """Main operational loop."""
    logging.info("Bot initialized. Scraping sheet tracking targets...")
    while True:
        active_tickers = fetch_tickers_from_sheet(SHEET_CSV_URL)
        
        if active_tickers:
            for symbol in active_tickers:
                logging.info(f"Processing calculations for ticker: {symbol}")
                df = get_market_data(symbol)
                signal = calculate_strategy(df)
                execute_trade(symbol, signal, QTY_PER_TRADE)
                time.sleep(0.5) # Avoid hitting API rate-limits
        else:
            logging.warning("No active tickers found. Retrying in next interval...")
        
        # Wait until the start of the next hour
        now = datetime.now()
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=30, microsecond=0)
        sleep_seconds = (next_hour - now).total_seconds()
        
        logging.info(f"Cycle complete. Sleeping {int(sleep_seconds)}s until {next_hour.strftime('%H:%M:%S')}")
        time.sleep(max(sleep_seconds, 60))

if __name__ == "__main__":
    run_bot()