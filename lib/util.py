import pandas as pd
import numpy as np
import json # Import the json module
# from pkindicators import *

# Set base folder to the project's data directory
base_data_folder = './data'

def load_json_candles(fname):
    """Loads candles from a JSON file (list-of-lists OHLCV format)."""
    try:
        # Load the raw JSON data
        with open(fname, 'r') as f:
            raw_data = json.load(f)

        # Convert to DataFrame, specifying column names
        data = pd.DataFrame(raw_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        # Convert timestamp and set as index
        data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
        data.set_index('timestamp', inplace=True)

        # Ensure standard OHLCV casing for compatibility
        data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True) # Ensure correct casing

        # Convert columns to appropriate numeric types
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_cols:
            data[col] = pd.to_numeric(data[col], errors='coerce')

        return data
    except FileNotFoundError:
        print(f"Error: Data file not found at {fname}")
        return None
    except Exception as e:
        print(f"Error loading JSON candles from {fname}: {e}")
        return None

def load_candles(exchange, base, quote, timeframe):
    """Constructs filename and loads candles using load_json_candles."""
    # Corrected filename format as per user feedback
    pair_format = f"{base}_{quote}" # e.g., ETH_USDT
    fname = f'{base_data_folder}/{pair_format}-{timeframe}.json' # e.g., data/ETH_USDT-4h.json
    print(f"Attempting to load: {fname}")
    return load_json_candles(fname)
