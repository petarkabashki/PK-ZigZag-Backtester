#%%
# Indicator Calculation Functions
# -----------------------------------------------------------------------------------------
import pandas as pd
import numpy as np
import time

# Import the compiled C extensions or dummies
try:
    from . import zigzag as zz # Use relative import within the lib package
    print("Successfully imported C zigzag extension in indicators.py.")
except ImportError as e:
    print(f"Error importing C zigzag extension in indicators.py: {e}")
    # Define dummy functions if import fails
    class DummyZigzag:
        def calculate_zigzag(self, *args, **kwargs):
            print("WARN: Using dummy calculate_zigzag in indicators.py")
            highs = kwargs.get('highs')
            if highs is None:
                 print("WARN: Dummy calculate_zigzag called without 'highs' keyword argument.")
                 return np.array([], dtype=int), np.array([], dtype=int)
            length = len(highs)
            return np.zeros(length, dtype=int), np.zeros(length, dtype=int)
    zz = DummyZigzag()


def calculate_zigzag_wrapper(highs, lows, epsilon):
    """ Wrapper for the C implementation of ZigZag. """
    start_time = time.time()
    highs_np = np.array(highs, dtype=np.double)
    lows_np = np.array(lows, dtype=np.double)
    if np.isnan(highs_np).any() or np.isnan(lows_np).any() or \
       np.isinf(highs_np).any() or np.isinf(lows_np).any():
        length = len(highs_np)
        print("WARN: NaNs or Infs found in highs/lows for ZigZag, returning zeros.")
        return np.zeros(length, dtype=int), np.zeros(length, dtype=int)
    markers, turning_points = zz.calculate_zigzag(highs=highs_np, lows=lows_np, epsilon=epsilon)
    # print(f"Zigzag calculation took: {time.time() - start_time:.4f} seconds")
    return markers, turning_points

def get_zigzag_pivots(markers, data):
    """ Extracts pivot points (location, timestamp, type, price). """
    pivot_indices_loc = np.where(markers != 0)[0]
    pivots = []
    for idx_loc in pivot_indices_loc:
        timestamp = data.index[idx_loc]
        pivot_type = markers[idx_loc]
        price = data['High'].iloc[idx_loc] if pivot_type == 1 else data['Low'].iloc[idx_loc]
        pivots.append({'loc': idx_loc, 'timestamp': timestamp, 'type': pivot_type, 'price': price})
    return pivots

def add_fib_levels_forward(data, pivots):
    """ Calculates Fib levels for each completed segment and forward fills them. """
    # Keep relevant Fib levels for entry/stop logic
    fib_ratios = sorted(list(set([0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0])))

    data['last_pivot_loc'] = np.nan
    data['last_pivot_type'] = np.nan
    data['last_pivot_price'] = np.nan
    data['last_segment_start_price'] = np.nan
    data['last_segment_end_price'] = np.nan
    data['last_segment_direction'] = np.nan
    for ratio in fib_ratios: data[f'last_fib_{ratio:.3f}'] = np.nan

    if len(pivots) < 2: return data

    for i in range(len(pivots) - 1):
        start_pivot = pivots[i]; end_pivot = pivots[i+1]
        start_loc, end_loc = start_pivot['loc'], end_pivot['loc']
        start_price, end_price = start_pivot['price'], end_pivot['price']
        segment_direction = end_pivot['type']

        if start_loc >= end_loc: continue
        price_diff = end_price - start_price
        if price_diff == 0: continue

        segment_fibs = {f'last_fib_{r:.3f}': start_price + price_diff * r for r in fib_ratios}
        fill_start_loc = end_loc + 1
        fill_end_loc = pivots[i+2]['loc'] if i + 2 < len(pivots) else len(data)

        if fill_start_loc < fill_end_loc:
            fill_slice = slice(fill_start_loc, fill_end_loc)
            data.iloc[fill_slice, data.columns.get_loc('last_pivot_loc')] = end_loc
            data.iloc[fill_slice, data.columns.get_loc('last_pivot_type')] = end_pivot['type']
            data.iloc[fill_slice, data.columns.get_loc('last_pivot_price')] = end_pivot['price']
            data.iloc[fill_slice, data.columns.get_loc('last_segment_start_price')] = start_price
            data.iloc[fill_slice, data.columns.get_loc('last_segment_end_price')] = end_price
            data.iloc[fill_slice, data.columns.get_loc('last_segment_direction')] = segment_direction
            for ratio in fib_ratios:
                col_name = f'last_fib_{ratio:.3f}'
                if col_name in data.columns:
                    data.iloc[fill_slice, data.columns.get_loc(col_name)] = segment_fibs[col_name]

    data = data.ffill() # Use DataFrame ffill
    return data

def calculate_fractals(highs, lows, n=2):
    """
    Calculates William Fractals using pandas rolling operations.
    A fractal high occurs at index i if highs[i] > highs[i-n]...highs[i-1] AND highs[i] > highs[i+1]...highs[i+n].
    A fractal low occurs at index i if lows[i] < lows[i-n]...lows[i-1] AND lows[i] < lows[i+1]...lows[i+n].
    Args:
        highs (pd.Series): Series of high prices.
        lows (pd.Series): Series of low prices.
        n (int): Number of bars to check on each side.
    Returns:
        tuple: (pd.Series[bool], pd.Series[bool]) - fractal_high, fractal_low
    """
    if not isinstance(highs, pd.Series) or not isinstance(lows, pd.Series):
        raise TypeError("highs and lows must be pandas Series")
    if len(highs) != len(lows):
        raise ValueError("highs and lows must have the same length")
    if n < 1:
        raise ValueError("n must be at least 1")

    # Shift highs and lows to compare with the center point
    shifted_highs = [highs.shift(i) for i in range(-n, n + 1)]
    shifted_lows = [lows.shift(i) for i in range(-n, n + 1)]

    # Check high fractal condition: center high is the max of the window 2n+1
    high_max = pd.concat(shifted_highs, axis=1).max(axis=1)
    fractal_high = (highs == high_max) & (highs > highs.shift(1)) # Break ties favoring later bar

    # Check low fractal condition: center low is the min of the window 2n+1
    low_min = pd.concat(shifted_lows, axis=1).min(axis=1)
    fractal_low = (lows == low_min) & (lows < lows.shift(1)) # Break ties favoring later bar

    # Fill NaNs at edges resulting from shifts/rolling
    fractal_high = fractal_high.fillna(False)
    fractal_low = fractal_low.fillna(False)

    return fractal_high, fractal_low