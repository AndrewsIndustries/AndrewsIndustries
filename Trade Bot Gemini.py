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
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trade_bot_gemini.log"),
        logging.StreamHandler()
    ]
)

# Authentication configuration
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# Initialize Modern SDK clients
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=("paper" in BASE_URL))
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

SYMBOL = "SPY"
QTY = 10

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
        logging.error(f"Error fetching data for {symbol}: {e}")
        return None

def calculate_strategy(df):
    """
    Defines the trading logic.
    Returns 'BUY' if the short-term trend crosses above the long-term trend,
    'SELL' if it crosses below, and 'HOLD' otherwise.
    """
    if df is None or len(df) < 30:
        return "HOLD"
        
    # Create a copy to avoid SettingWithCopyWarning
    df = df.copy()
    
    # Ensure we are using 'close' column regardless of Index
    close_prices = df['close']
    sma_fast = close_prices.rolling(window=10).mean().dropna()
    sma_slow = close_prices.rolling(window=30).mean().dropna()

    if len(sma_fast) < 2 or len(sma_slow) < 2:
        return "HOLD"
    
    latest_fast, latest_slow = sma_fast.iloc[-1], sma_slow.iloc[-1]
    previous_fast, previous_slow = sma_fast.iloc[-2], sma_slow.iloc[-2]
    
    logging.info(f"SMA Fast: {latest_fast:.2f}, SMA Slow: {latest_slow:.2f}")

    if previous_fast <= previous_slow and latest_fast > latest_slow:
        return "BUY"
    elif previous_fast >= previous_slow and latest_fast < latest_slow:
        return "SELL"
    return "HOLD"

def execute_trade(symbol, signal, quantity):
    """Handles order placement and position checks."""
    try:
        # Check for open orders first to avoid duplicates
        orders = trading_client.get_orders()
        if any(o.symbol == symbol for o in orders):
            logging.info(f"Pending order already exists for {symbol}. Skipping.")
            return

        try:
            pos = trading_client.get_open_position(symbol)
        except APIError:
            # Alpaca returns a 404 APIError if no position exists
            pos = None

        # Check market clock
        clock = trading_client.get_clock()
        if not clock.is_open and signal != "HOLD":
            logging.info("Market is closed. Skipping trade execution.")
            return

        if signal == "BUY" and pos is None:
            logging.info(f"Signal: BUY {quantity} shares of {symbol}")
            req = MarketOrderRequest(
                symbol=symbol, qty=quantity, side=OrderSide.BUY, time_in_force=TimeInForce.GTC
            )
            trading_client.submit_order(req)
        elif signal == "SELL" and pos is not None:
            logging.info(f"Signal: CLOSING position of {pos.qty} in {symbol}")
            trading_client.close_position(symbol)
        else:
            logging.info(f"Signal: HOLD or position condition not met for {symbol}.")
    except Exception as e:
        logging.error(f"Error executing trade: {e}")

def run_bot():
    """Main operational loop."""
    logging.info("Bot initialized. Monitoring market data...")
    while True:
        # Simple loop to pull data and check strategy
        df = get_market_data(SYMBOL)
        signal = calculate_strategy(df)
        execute_trade(SYMBOL, signal, QTY)
        
        # Wait until the start of the next hour
        now = datetime.now()
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=30, microsecond=0)
        sleep_seconds = (next_hour - now).total_seconds()
        
        logging.info(f"Cycle complete. Sleeping {int(sleep_seconds)}s until {next_hour.strftime('%H:%M:%S')}")
        time.sleep(max(sleep_seconds, 60)) # Sleep at least 60s

if __name__ == "__main__":
    run_bot()