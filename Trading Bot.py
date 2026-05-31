import os
import datetime
import json
import asyncio
import pandas as pd
import logging
import websockets
from dotenv import load_dotenv
from typing import List, Optional
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import (
    StockBarsRequest, 
    StockSnapshotRequest, 
    StockQuotesRequest, 
    StockTradesRequest
)
from alpaca.data.enums import DataFeed, Adjustment
from alpaca.common.enums import Sort
from alpaca.data.timeframe import TimeFrame

# Load environment variables
load_dotenv()

# Unified Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_bot_core.log"),
        logging.StreamHandler()
    ]
)

# --- ALPACA CLIENT CONFIGURATION ---
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

if not API_KEY or not SECRET_KEY:
    logging.error("ALPACA_API_KEY or ALPACA_SECRET_KEY is missing in .env file.")
    # We don't exit here so the Tester can still load the module without crashing the UI

# Initialize clients; Paper trading is active for the simulation environment
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=("paper" in BASE_URL))
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

# --- DEALER CONNECTION CONFIG ---
DEALER_URI = "ws://127.0.0.1:8765"

# --- SIMULATION & STRATEGY CONSTANTS ---
# The CSV URL sourced from instructions (formatted for Pandas CSV consumption)
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTQYftjQ9fHLfDzmWIZ7QFdW0SplgDJPVpaaHKirmWkOERgEMNSr2yPcwXUNKRnxSwFRPTTQf8maQjs/pub?gid=134813518&single=true&output=csv"

# Global Strategy Parameters referenced by the Tester's execution engine
INITIAL_PORTFOLIO_VALUE = 5000.00
RISK_PER_TRADE = 0.02    # Risk 2% of total equity per trade
STOP_LOSS_PCT = 0.05     # 5% Stop Loss
TAKE_PROFIT_PCT = 0.10   # 10% Take Profit

def initialize_lookback(symbols: List[str]):
    """
    Lookback Initialization: Uses StockBarsRequest to gather historical candles.
    Matches strict Alpaca-py documentation parameter specifications.
    """
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=7)

    request_params = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Hour,
        start=start_date,
        end=end_date,
        limit=None,
        adjustment=Adjustment.ALL,
        feed=DataFeed.IEX,
        sort=Sort.ASC
    )
    
    return data_client.get_stock_bars(request_params)

def get_realtime_snapshot(symbols: List[str]):
    """
    Real-Time Data Pulse: Uses StockSnapshotRequest for high-frequency pulse.
    Utilized inside the loop to grab the instant state of a ticker.
    """
    request_params = StockSnapshotRequest(
        symbol_or_symbols=symbols,
        feed=DataFeed.IEX
    )
    
    return data_client.get_stock_snapshot(request_params)

def fetch_order_book_data(symbol: str):
    """
    Order Book & Order Execution: Demonstrates StockQuotesRequest and StockTradesRequest.
    Used for historical back-references or detailed volume analysis.
    """
    now = datetime.datetime.now()
    start = now - datetime.timedelta(minutes=10)

    quotes_request = StockQuotesRequest(
        symbol_or_symbols=symbol,
        start=start,
        end=now,
        limit=5,
        feed=DataFeed.IEX,
        sort=Sort.DESC
    )

    trades_request = StockTradesRequest(
        symbol_or_symbols=symbol,
        start=start,
        end=now,
        limit=5,
        feed=DataFeed.IEX,
        sort=Sort.ASC
    )

    return data_client.get_stock_quotes(quotes_request), data_client.get_stock_trades(trades_request)

def calculate_strategy(df):
    """
    Shared SMA Crossover Strategy (Matches Gemini Bots).
    Returns 'BUY', 'SELL', or 'HOLD'.
    """
    if df is None or len(df) < 30:
        return "HOLD"
        
    # Handle potential MultiIndex from Alpaca-py
    if isinstance(df.index, pd.MultiIndex):
        close_prices = df['close'].reset_index(level=0, drop=True)
    else:
        close_prices = df['close']

    sma_fast = close_prices.rolling(window=10).mean().dropna()
    sma_slow = close_prices.rolling(window=30).mean().dropna()

    if len(sma_fast) < 2 or len(sma_slow) < 2:
        return "HOLD"

    latest_fast, latest_slow = sma_fast.iloc[-1], sma_slow.iloc[-1]
    previous_fast, previous_slow = sma_fast.iloc[-2], sma_slow.iloc[-2]
    
    if previous_fast <= previous_slow and latest_fast > latest_slow:
        return "BUY"
    elif previous_fast >= previous_slow and latest_fast < latest_slow:
        return "SELL"
    return "HOLD"

async def execute_decision_loop(target_symbols: List[str]):
    """
    Execution Logic: Frame-by-frame loop evaluating asset conditions.
    Now connects to the Trade Bot Tester 'Dealer' to receive synchronized ticks.
    """
    data_buffers = {} # Internal storage for incoming ticks

    logging.info(f"Bot initialized. Targeting: {target_symbols}")

    while True:
        try:
            async with websockets.connect(DEALER_URI) as websocket:
                logging.info("Handshake Complete: Connected to Arena Dealer.")
                
                async for message in websocket:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "TICK":
                        # Individual asset pulse (e.g., BTC/USD)
                        asset = data.get("asset")
                        price = data.get("price")
                        ts = data.get("timestamp")
                        # Logic: Fetch snapshot or history here if asset matches target

                    elif msg_type == "ARENA_TICKS":
                        # Data received from the Tester UI
                        ticks = data.get("data", [])
                        for tick in ticks:
                            symbol = tick.get('asset')
                            price = tick.get('price')

                            if symbol not in data_buffers:
                                data_buffers[symbol] = []

                            # Append tick and keep last 50 for SMA calculation
                            data_buffers[symbol].append({'close': price})
                            if len(data_buffers[symbol]) > 50:
                                data_buffers[symbol].pop(0)

                            logging.info(f"Arena Update: {symbol} is currently at {price}")

                            # If we have enough data, evaluate the strategy
                            if len(data_buffers[symbol]) >= 30:
                                df = pd.DataFrame(data_buffers[symbol])
                                signal = calculate_strategy(df)
                                if signal != "HOLD":
                                    logging.info(f"STRATEGY SIGNAL for {symbol}: {signal}")
                        
                    elif msg_type == "MARKET_STATUS":
                        status = data.get("status")
                        logging.info(f"Market Notification: {status}")

        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError):
            logging.error("Dealer connection failed. Is Trade Bot Tester.py running?")
            await asyncio.sleep(2)
        except Exception as e:
            logging.error(f"Unexpected Bot Error: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    # Shared Ticker Initialization: Syncs with the Arena Watchlist
    try:
        df_symbols = pd.read_csv(SHEET_CSV_URL)
        symbols = [str(t).strip() for t in df_symbols.iloc[:, 0].dropna().unique().tolist() 
                   if str(t).strip() and str(t).lower() != 'nan']
    except Exception:
        symbols = ["AAPL", "TSLA", "MSFT"]

    asyncio.run(execute_decision_loop(symbols))