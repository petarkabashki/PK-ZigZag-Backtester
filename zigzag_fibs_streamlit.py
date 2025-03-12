import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pandas.plotting._matplotlib.core")

import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mplfinance.original_flavor import candlestick_ohlc
import sysconfig
from lib.pkindicators import calculate_zigzag
from lib.util import load_json_candles

st.set_page_config(layout="wide")

st.title('ZigZag Fibonacci Levels')

# Sidebar for user inputs
st.sidebar.header('Data Selection')

exchange = st.sidebar.text_input('Exchange', 'binance')
base = st.sidebar.text_input('Base Asset', 'ETH')
quote = st.sidebar.text_input('Quote Asset', 'USDT')
timeframe = st.sidebar.selectbox('Timeframe', ['1d', '4h', '1h', '30m', '15m', '5m', '1m'])


# Load data
@st.cache_data
def load_data(exchange, base, quote, timeframe):
    fname = f'./data/{base}_{quote}-{timeframe}.json'
    try:
        return load_json_candles(fname)
    except FileNotFoundError:
        st.error(f"Data file not found: {fname}. Please make sure to download the data first.")
        return None
    return None # Return None in case of error to handle flow properly


data = None # Initialize data to None

st.header('Parameters') # Moved header to main panel

epsilon = st.slider('Epsilon', min_value=0.01, max_value=0.1, value=0.05, step=0.01) # Moved epsilon slider to main panel
fib_levels_input = st.text_input('Fibonacci Levels (comma separated)', '0.0, 0.236, 0.414, 0.382, 0.5, 0.618, 0.786, 1.0') # Moved fib_levels_input to main panel
fib_levels = np.array([float(f.strip()) for f in fib_levels_input.split(',')])
fib_columns = [f'fib({fib})' for fib in fib_levels]


if st.sidebar.button('Load Data'):
    st.cache_data.clear() # Clear the cache
    data = load_data(exchange, base, quote, timeframe)

if data is not None:
    # Display data stats in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("##### Data Stats")
    st.sidebar.markdown(f"- Rows: {data.shape[0]}")
    st.sidebar.markdown(f"- Start Date: {data.index.min().strftime('%Y-%m-%d %H:%M')}")
    st.sidebar.markdown(f"- End Date: {data.index.max().strftime('%Y-%m-%d %H:%M')}")
    st.sidebar.markdown("---")


    highs = data['high'].values
    lows = data['low'].values

    # Calculate ZigZag
    high_low_markers, turning_markers = calculate_zigzag(highs, lows, epsilon=epsilon)
    extreme_points_ix = np.where(high_low_markers != 0)[0]
    extreme_points = high_low_markers[extreme_points_ix]
    turning_points_ix = np.where(turning_markers !=0)[0]

    # Calculate Fibonacci Levels
    fhigh_low_markers, fturning_markers = calculate_zigzag(highs, lows, epsilon=epsilon * 1)
    running_highs = pd.Series(np.where(fhigh_low_markers == 1, 1, np.nan) * highs).ffill().values
    running_lows = pd.Series(np.where(fhigh_low_markers == -1, 1, np.nan) * lows).ffill().values
    diff = running_highs - running_lows
    fib_matrix = np.outer(diff, fib_levels)
    fib_levels_array = running_lows[:, np.newaxis] + fib_matrix
    df_fibs = pd.DataFrame(fib_levels_array, columns=fib_columns, index=data.index)

    # --- Chart Display ---
    st.subheader('Price Chart with ZigZag and Fibonacci Levels')


    # Window selection
    max_start_index_widths = max(0, (len(data) - 100) // 100) # Initial calculation with default window_width=100
    window_width = st.slider('Window Width', min_value=100, max_value=len(data) if len(data) > 100 else 100, value=100) # Adjusted max_value for window_width
    max_start_index_widths = max(0, (len(data) - window_width) // window_width) # Recalculate max_start_index_widths based on current window_width
    start_index_widths = st.slider('Start Window', 0, max_start_index_widths, 0) # Slider for window multipliers, default to 0
    ws = start_index_widths * window_width # Calculate window start based on multiplier and width
    ww = window_width
    wdata = data.iloc[ws:ws+ww].copy() # Adjusted to be inclusive of window_width

    st.write("Data Length:", len(data)) # Debugging output
    st.write("Window Width:", window_width) # Debugging output
    st.write("Max Start Index Widths:", max_start_index_widths) # Debugging output
    st.write("Start Index Widths:", start_index_widths) # Debugging output
    st.write("Window Start (ws):", ws) # Debugging output
    st.write("Window End (ww):", ww) # Debugging output


    whighs = wdata.high
    wlows = wdata.low
    candlestick_ohlc_args={'width': .6 / np.log(len(wdata)) if len(wdata) > 1 else 0.6} # Avoid log(0) error

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 10), height_ratios=[2, 1])

    wdata['date_num'] = mdates.date2num(wdata.index)
    ohlc = wdata[['date_num', 'open', 'high', 'low', 'close']].values
    candlestick_ohlc(ax1, ohlc, colorup='green', colordown='red', alpha=0.8, **candlestick_ohlc_args)
    ax1.set_ylim(wlows.min()*0.995, whighs.max()*1.005)
    ax1.xaxis_date()
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.set_title(f'{base}/{quote} {timeframe} - ZigZag with Fibonacci Levels')

    wturning_points_ix = turning_points_ix[(turning_points_ix >= ws) & (turning_points_ix < ws + ww)] # Adjusted to be within window
    wextreme_points_ix_window = extreme_points_ix[(extreme_points_ix >= ws) & (extreme_points_ix < ws + ww)] # Filter indices within window
    wextreme_points = extreme_points[(extreme_points_ix >= ws) & (extreme_points_ix < ws + ww)] # Filter extreme_points using the same window condition
    wextreme_prices = np.where(wextreme_points == 1, highs[wextreme_points_ix_window], lows[wextreme_points_ix_window]) # Use the filtered index


    ax1.plot(data.index[wextreme_points_ix_window], wextreme_prices, color='purple', label='ZigZag Line', lw=1.5)
    for ix in wturning_points_ix:
        ax1.axvline(data.index.values[ix], color='gray', linestyle='-', alpha=0.2, lw=3)

    df_fibs.loc[wdata.index][fib_columns].plot(ax=ax1, linestyle='--', lw=1) # Plot only selected fib columns

    st.pyplot(fig)

    # --- Compilation Info (for debugging/info) ---
    cmodule = 'pkindicators'
    compilation_info = f'Compilation command (for reference):\n'
    compilation_info += f'`clear & rm {{cmodule}}.so & gcc -shared -o {{cmodule}}.so -fPIC {{cmodule}}.c -I{{sysconfig.get_path("include")}} -I{{np.get_include()}}`'
    st.sidebar.markdown("---")
    st.sidebar.markdown("##### Compilation Info")
    st.sidebar.code(compilation_info, language='shell')
