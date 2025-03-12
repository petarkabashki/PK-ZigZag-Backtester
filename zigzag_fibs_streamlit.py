import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mplfinance.original_flavor import candlestick_ohlc
import sysconfig
from lib.pkindicators import calculate_zigzag
from lib.util import load_json_candles

st.set_page_config(layout="wide", theme={"base":"dark"})

st.title('ZigZag Fibonacci Levels')

# Sidebar for user inputs
st.sidebar.header('Parameters')

exchange = st.sidebar.text_input('Exchange', 'binance')
base = st.sidebar.text_input('Base Asset', 'ETH')
quote = st.sidebar.text_input('Quote Asset', 'USDT')
timeframe = st.sidebar.selectbox('Timeframe', ['1d', '4h', '1h', '30m', '15m', '5m', '1m'])
epsilon = st.sidebar.slider('Epsilon', min_value=0.01, max_value=0.1, value=0.05, step=0.01)

fib_levels_input = st.sidebar.text_input('Fibonacci Levels (comma separated)', '0.0, 0.236, 0.414, 0.382, 0.5, 0.618, 0.786, 1.0')
fib_levels = np.array([float(f.strip()) for f in fib_levels_input.split(',')])
fib_columns = [f'fib({fib})' for fib in fib_levels]


# Load data
@st.cache_data
def load_data(exchange, base, quote, timeframe):
    fname = f'./data/{base}_{quote}-{timeframe}.json'
    try:
        return load_json_candles(fname)
    except FileNotFoundError:
        st.error(f"Data file not found: {fname}. Please make sure to download the data first.")
        return None

data = load_data(exchange, base, quote, timeframe)

if data is not None:
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
    start_index = st.slider('Start Index', 0, len(data) - 1, max(0, len(data) - 1000))
    window_width = st.slider('Window Width', min_value=100, max_value=len(data) - start_index, value=min(200, len(data) - start_index))
    ws = start_index
    ww = window_width
    wdata = data.iloc[ws:ws+ww].copy() # Adjusted to be inclusive of window_width

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
