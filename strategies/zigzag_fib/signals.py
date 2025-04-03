#%%
# Signal Generation Functions
# -----------------------------------------------------------------------------------------
import pandas as pd
import numpy as np
from lib.indicators import calculate_zigzag_wrapper, get_zigzag_pivots, add_fib_levels_forward, calculate_fractals # <-- Corrected import

# Updated signature to accept parameters from Streamlit app
def generate_signals(data_df, zigzag_epsilon=0.03, entry_fib=0.618, stop_entry_fib=0.786, wick_lookback=5, fractal_n=2, take_profit_fib=1.618, stop_loss_fib=0.0, exit_type='fractal', trade_direction='long'):
    """Calculates indicators and generates long entry/exit signals."""
    if data_df is None: return None
    # Ensure input DataFrame has uppercase columns before copying
    data_df.rename(columns={
        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
    }, inplace=True, errors='ignore') # Use errors='ignore' in case they are already uppercase
    df = data_df.copy()
    # print(f"DEBUG: generate_signals called with params: epsilon={zigzag_epsilon}, entry_fib={entry_fib}, stop_entry_fib={stop_entry_fib}, wick_lookback={wick_lookback}, fractal_n={fractal_n}, tp_fib={take_profit_fib}, sl_fib={stop_loss_fib}, exit_type={exit_type}, direction={trade_direction}") # DEBUG

    # --- Calculate Zigzag & Fibs ---
    # Use uppercase column names
    markers, _ = calculate_zigzag_wrapper(df['High'], df['Low'], zigzag_epsilon)
    df['zigzag_marker'] = markers
    pivots = get_zigzag_pivots(markers, df) # get_zigzag_pivots already expects uppercase
    # print(f"DEBUG: Number of pivots found: {len(pivots)}") # DEBUG
    if len(pivots) < 2:
        # print("DEBUG: Not enough pivots, returning None.") # DEBUG
        # Return dataframe with expected columns but no signals
        df['buy_signal'] = False
        df['exit_long_signal'] = False
        # Add dummy short signal columns if needed later
        # df['sell_signal'] = False
        # df['exit_short_signal'] = False
        # Use uppercase column names in return
        return df[['Open', 'High', 'Low', 'Close', 'buy_signal', 'exit_long_signal']]


    df = add_fib_levels_forward(df, pivots) # add_fib_levels_forward already expects uppercase

    # --- Calculate Fractals (only if needed for fractal exit) ---
    if exit_type == 'fractal': # Use exit_type parameter
        # Use uppercase column names
        df['fractal_high'], df['fractal_low'] = calculate_fractals(df['High'], df['Low'], n=fractal_n)
    else:
        # Add dummy columns if not using fractals to avoid errors later
        df['fractal_high'] = False
        df['fractal_low'] = False


    # --- Check Fib columns and Fill NaNs ---
    entry_col = f'last_fib_{entry_fib:.3f}'
    stop_entry_col = f'last_fib_{stop_entry_fib:.3f}' # Still needed for wick rejection
    # Add TP/SL fib columns if needed for fib exit (check if add_fib_levels_forward creates them)
    tp_col = f'last_fib_{take_profit_fib:.3f}'
    sl_col = f'last_fib_{stop_loss_fib:.3f}'

    required_fib_cols = [entry_col, stop_entry_col, 'last_segment_direction']
    # Add TP/SL cols to required list if exit_type is 'fib' and they exist
    # if exit_type == 'fib' and tp_col in df.columns: required_fib_cols.append(tp_col)
    # if exit_type == 'fib' and sl_col in df.columns: required_fib_cols.append(sl_col)


    missing_cols = [col for col in required_fib_cols if col not in df.columns]
    if missing_cols:
        print(f"WARN: Missing required Fib columns: {missing_cols}")
        # Return dataframe with expected columns but no signals
        df['buy_signal'] = False
        df['exit_long_signal'] = False
        # Use uppercase column names in return
        return df[['Open', 'High', 'Low', 'Close', 'buy_signal', 'exit_long_signal']]


    # Fill initial NaNs robustly
    for col in required_fib_cols:
         if col in df.columns: # Check if column exists before filling
             df[col] = df[col].ffill().bfill()

    if df[required_fib_cols].isnull().values.any():
        print("WARN: Required Fib columns still contain NaNs after filling.")
        # Return dataframe with expected columns but no signals
        df['buy_signal'] = False
        df['exit_long_signal'] = False
        # Use uppercase column names in return
        return df[['Open', 'High', 'Low', 'Close', 'buy_signal', 'exit_long_signal']]


    # --- Implement Wick Rejection Logic (Long Only for now) ---
    # Checks if price dipped below stop_entry_fib but closed above entry_fib in the lookback period
    # Use uppercase column names
    long_wick_reject = (
        (df['Low'].rolling(wick_lookback).min().shift(1) <= df[stop_entry_col]) &
        (df['Close'].rolling(wick_lookback).max().shift(1) >= df[entry_col])
    ).fillna(False)
    # print(f"DEBUG: Number of long_wick_reject = True: {long_wick_reject.sum()}") # DEBUG

    # --- Generate Entry Signal (Long Only for now) ---
    # Entry: Last segment up, Low hits entry fib, Wick rejection occurred
    cond_segment_up = (df['last_segment_direction'] == 1)
    # Use uppercase column names
    cond_low_hits_fib = (df['Low'] <= df[entry_col])
    # print(f"DEBUG: Number of cond_segment_up = True: {cond_segment_up.sum()}") # DEBUG
    # print(f"DEBUG: Number of cond_low_hits_fib = True: {cond_low_hits_fib.sum()}") # DEBUG

    # Restored wick rejection condition
    long_entry_cond = cond_segment_up & cond_low_hits_fib & long_wick_reject
    df['buy_signal'] = long_entry_cond
    # print(f"DEBUG: Number of final buy_signal = True: {df['buy_signal'].sum()}") # DEBUG

    # --- Generate Exit Signal (Long Only for now) ---
    if exit_type == 'fractal': # Use exit_type parameter
        exit_long_cond = df['fractal_low']
        df['exit_long_signal'] = exit_long_cond
        # print(f"DEBUG: Number of exit_long_signal (Fractal) = True: {df['exit_long_signal'].sum()}") # DEBUG
    elif exit_type == 'fib':
        # Placeholder: Implement Fib-based exit logic using tp_col and sl_col
        # Example: Exit if High hits TP fib OR Low hits SL fib
        # Need to ensure tp_col and sl_col exist from add_fib_levels_forward
        exit_long_cond = pd.Series(False, index=df.index) # Default to False
        # Use uppercase column names if implementing
        # if tp_col in df.columns and sl_col in df.columns:
        #     cond_hit_tp = (df['High'] >= df[tp_col])
        #     cond_hit_sl = (df['Low'] <= df[sl_col])
        #     exit_long_cond = cond_hit_tp | cond_hit_sl
        # else:
        #     print(f"WARN: TP ({tp_col}) or SL ({sl_col}) columns not found for Fib exit.")
        df['exit_long_signal'] = exit_long_cond # Assign placeholder
        # print(f"DEBUG: Number of exit_long_signal (Fib Placeholder) = True: {df['exit_long_signal'].sum()}") # DEBUG
    else:
        # Default case or handle other exit types
        df['exit_long_signal'] = False
        print(f"WARN: Unknown exit_type '{exit_type}'. Defaulting to no exit signal.")


    # Refine: Ensure exit doesn't trigger entry on the same bar
    initial_buys = df['buy_signal'].sum() # DEBUG
    df.loc[df['exit_long_signal'], 'buy_signal'] = False
    refined_buys = df['buy_signal'].sum() # DEBUG
    # if initial_buys != refined_buys: # DEBUG
        # print(f"DEBUG: Buy signals removed due to same-bar exit: {initial_buys - refined_buys}") # DEBUG


    # Return necessary columns (add short signals later if needed)
    # Ensure columns exist even if no signals triggered
    if 'buy_signal' not in df.columns: df['buy_signal'] = False
    if 'exit_long_signal' not in df.columns: df['exit_long_signal'] = False

    # Use uppercase column names in return
    return df[['Open', 'High', 'Low', 'Close', 'buy_signal', 'exit_long_signal']]