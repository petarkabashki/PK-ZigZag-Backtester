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

col1, col2 = st.columns(2)

with col1:
    epsilon = st.slider('Epsilon', min_value=0.01, max_value=0.1, value=0.05, step=0.01) # Moved epsilon slider to main panel
with col2:
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


# Window selection - moved outside the data check to be always active
if data is not None:
    max_start_index_widths = max(0, (len(data) - 100) // 100) # Initial calculation with default window_width=100

    col1_window, col2_window = st.columns(2) # Create columns for window sliders

    with col1_window:
        start_index_widths = st.slider('Start Window', 0, max_start_index_widths, 0, key='start_window') # Slider for window multipliers, default to 0
    with col2_window:
        window_width = st.slider('Window Width', min_value=100, max_value=len(data) if len(data) > 100 else 100, value=100, key='window_width_2') # Adjusted max_value for window_width
    max_start_index_widths = max(0, (len(data) - window_width) // window_width) # Recalculate max_start_index_widths based on current window_width


    ws = start_index_widths * window_width # Calculate window start based on multiplier and width
    ww = window_width


# Put these in a table of 3 columns below the plot. AI!
    st.write("Data Length:", len(data)) # Debugging output
    st.write("Window Width:", window_width) # Debugging output
    st.write("Max Start Index Widths:", max_start_index_widths) # Debugging output
    st.write("Start Index Widths:", start_index_widths) # Debugging output
    st.write("Window Start (ws):", ws) # Debugging output
    st.write("Window End (ww):", ww) # Debugging output


    if ws >= 0 and (ws + ww) <= len(data): # Check if window is within data bounds
        wdata = data.iloc[ws:ws+ww].copy() # Adjusted to be inclusive of window_width
    else:
        st.warning("Selected window is out of data bounds. Please adjust Start Window or Window Width.")
        st.stop() # Stop execution if window is out of bounds
        wdata = pd.DataFrame() # Return empty dataframe to avoid errors

    if not wdata.empty: # Proceed only if wdata is not empty
        whighs = wdata.high.values # Use wdata
        wlows = wdata.low.values # Use wdata

        # Calculate ZigZag on windowed data
        high_low_markers, turning_markers = calculate_zigzag(whighs, wlows, epsilon=epsilon) # Use whighs and wlows
        extreme_points_ix = np.where(high_low_markers != 0)[0]
        extreme_points = high_low_markers[extreme_points_ix]
        turning_points_ix = np.where(turning_markers !=0)[0]

        # Calculate Fibonacci Levels on windowed data
        fhigh_low_markers, fturning_markers = calculate_zigzag(whighs, wlows, epsilon=epsilon * 1) # Use whighs and wlows
        running_highs = pd.Series(np.where(fhigh_low_markers == 1, 1, np.nan) * whighs).ffill().values # Use whighs
        running_lows = pd.Series(np.where(fhigh_low_markers == -1, 1, np.nan) * wlows).ffill().values # Use wlows
        diff = running_highs - running_lows
        fib_matrix = np.outer(diff, fib_levels)
        fib_levels_array = running_lows[:, np.newaxis] + fib_matrix
        df_fibs = pd.DataFrame(fib_levels_array, columns=fib_columns, index=wdata.index) # Use wdata.index


        # --- Chart Display ---
        st.subheader('Price Chart with ZigZag and Fibonacci Levels')


        candlestick_ohlc_args={'width': .6 / np.log(len(wdata)) if len(wdata) > 1 else 0.6} # Avoid log(0) error

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 10), height_ratios=[2, 1])

        wdata['date_num'] = mdates.date2num(wdata.index)
        ohlc = wdata[['date_num', 'open', 'high', 'low', 'close']].values
        candlestick_ohlc(ax1, ohlc, colorup='green', colordown='red', alpha=0.8, **candlestick_ohlc_args)
        ax1.set_ylim(wlows.min()*0.995, whighs.max()*1.005)
        ax1.xaxis_date()
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.set_title(f'{base}/{quote} {timeframe} - ZigZag with Fibonacci Levels')

        wturning_points_ix = turning_points_ix # Use calculated turning_points_ix for wdata
        wextreme_points_ix_window = extreme_points_ix # Use calculated extreme_points_ix for wdata
        wextreme_points = extreme_points # Use calculated extreme_points for wdata
        wextreme_prices = np.where(wextreme_points == 1, whighs[wextreme_points_ix_window], wlows[wextreme_points_ix_window]) # Use whighs and wlows


        ax1.plot(wdata.index[wextreme_points_ix_window], wextreme_prices, color='purple', label='ZigZag Line', lw=1.5) # Use wdata.index
        for ix in wturning_points_ix:
            ax1.axvline(wdata.index.values[ix], color='gray', linestyle='-', alpha=0.2, lw=3) # Use wdata.index

        df_fibs.plot(ax=ax1, linestyle='--', lw=1) # Plot df_fibs calculated for wdata

        st.pyplot(fig)


    # --- Compilation Info (for debugging/info) ---
    cmodule = 'pkindicators'
    compilation_info = f'Compilation command (for reference):\n'
    compilation_info += f'`clear & rm {{cmodule}}.so & gcc -shared -o {{cmodule}}.so -fPIC {{cmodule}}.c -I{{sysconfig.get_path("include")}} -I{{np.get_include()}}`'
    st.sidebar.markdown("---")
    st.sidebar.markdown("##### Compilation Info")
    st.sidebar.code(compilation_info, language='shell')
