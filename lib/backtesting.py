#%%
# Backtesting Functions
# -----------------------------------------------------------------------------------------
import pandas as pd
import numpy as np
from .metrics import calculate_sharpe_ratio, calculate_sortino_ratio, calculate_max_drawdown

# Import the compiled C extensions or dummies
try:
    from . import position_tools # Use relative import within the lib package
    print("Successfully imported C position_tools extension in backtesting.py.")
except ImportError as e:
    print(f"Error importing C position_tools extension in backtesting.py: {e}")
    # Define dummy functions if import fails
    class DummyPositionTools:
        def enumerate_trades(self, entry_mask, exit_mask, skip_first=0):
            print("WARN: Using dummy enumerate_trades in backtesting.py")
            entry_indices = np.where(entry_mask)[0]
            exit_indices = np.where(exit_mask)[0]
            entries = []
            exits = []
            in_trade = False
            entry_idx = -1
            for i in range(len(entry_mask)):
                if not in_trade and entry_mask[i]:
                    entries.append(i)
                    in_trade = True
                    entry_idx = i
                elif in_trade and exit_mask[i] and i > entry_idx:
                    exits.append(i)
                    in_trade = False
            min_len = min(len(entries), len(exits))
            return entries[:min_len], exits[:min_len]
    position_tools = DummyPositionTools()


def run_backtest(data_df, min_trades_for_stats=5, debug_log=False):
    """Runs the long-only backtest using Fractal Exit."""
    if debug_log: print("\n--- DEBUG: run_backtest ---")
    required_cols_backtest = ['buy_signal', 'exit_long_signal', 'Close', 'Low', 'High'] # Removed stop_loss_level
    if data_df is None or not all(s in data_df.columns for s in required_cols_backtest):
        print("WARN: Backtest input missing required columns.")
        default_results = {
            'total_return': -1, 'sharpe_ratio': -5, 'sortino_ratio': -5, 'max_drawdown': 1.0,
            'total_trades': 0, 'long_trades': 0
        }
        bh_results = {'bh_total_return': -1, 'bh_sharpe_ratio': -5, 'bh_sortino_ratio': -5, 'bh_max_drawdown': 1.0}
        return None, default_results, bh_results

    df = data_df.copy()
    df['buy_signal'] = df['buy_signal'].fillna(False)
    df['exit_long_signal'] = df['exit_long_signal'].fillna(False)

    # --- Enumerate Trades ---
    buy_mask = df['buy_signal'].values
    exit_long_mask = df['exit_long_signal'].values
    if debug_log:
        buy_indices_input = np.where(buy_mask)[0]
        exit_indices_input = np.where(exit_long_mask)[0]
        print(f"  Input to enumerate_trades - Buy mask sum: {buy_mask.sum()}, indices (first 50): {buy_indices_input[:50]}")
        print(f"  Input to enumerate_trades - Exit mask sum: {exit_long_mask.sum()}, indices (first 50): {exit_indices_input[:50]}")

    # Use the C function for enumerating trades - Includes fix for missing argument
    entry_indices, exit_indices = position_tools.enumerate_trades(buy_mask, exit_long_mask, 0)
    if debug_log:
        print(f"  Output from enumerate_trades - Entries: {len(entry_indices)}, Exits: {len(exit_indices)}")
        if len(entry_indices) > 0: print(f"    First 50 entry indices: {entry_indices[:50]}")
        if len(exit_indices) > 0: print(f"    First 50 exit indices: {exit_indices[:50]}")

    total_trades = len(entry_indices)
    long_trades = total_trades # Only long trades in this strategy

    # --- Create Trades DataFrame ---
    trades_list = []
    if total_trades > 0:
        entry_times = df.index[entry_indices]
        exit_times = df.index[exit_indices]
        entry_prices = df['Close'].values[entry_indices]
        exit_prices = df['Close'].values[exit_indices]

        for i in range(total_trades):
            trades_list.append({
                'EntryIndex': entry_indices[i],
                'ExitIndex': exit_indices[i],
                'EntryTime': entry_times[i],
                'ExitTime': exit_times[i],
                'EntryPrice': entry_prices[i],
                'ExitPrice': exit_prices[i]
            })
    trades_df = pd.DataFrame(trades_list)
    # Ensure correct dtypes if list was empty
    if trades_df.empty:
        trades_df = pd.DataFrame(columns=['EntryIndex', 'ExitIndex', 'EntryTime', 'ExitTime', 'EntryPrice', 'ExitPrice'])
        trades_df = trades_df.astype({'EntryIndex': int, 'ExitIndex': int, 'EntryTime': 'datetime64[ns]', 'ExitTime': 'datetime64[ns]', 'EntryPrice': float, 'ExitPrice': float})
    else:
        trades_df['EntryTime'] = pd.to_datetime(trades_df['EntryTime'])
        trades_df['ExitTime'] = pd.to_datetime(trades_df['ExitTime'])

    # --- Calculate Returns ---
    df['log_return'] = np.log(df['Close'] / df['Close'].shift(1))
    df['strategy_log_return'] = 0.0

    if total_trades > 0:
        # Create a position mask: 1 when in a trade, 0 otherwise
        position_mask = np.zeros(len(df), dtype=int)
        for entry_idx, exit_idx in zip(entry_indices, exit_indices):
            if entry_idx < exit_idx: # Ensure entry is before exit
                position_mask[entry_idx+1 : exit_idx+1] = 1 # Hold position from bar AFTER entry until bar OF exit
        df['position'] = position_mask
        df['strategy_log_return'] = df['log_return'] * df['position'].shift(1).fillna(0) # Apply position from previous bar
    else:
        df['position'] = 0

    df['cumulative_strategy_returns'] = df['strategy_log_return'].cumsum()
    df['cumulative_bh_returns'] = df['log_return'].cumsum()

    # --- Calculate Metrics ---
    total_return = df['cumulative_strategy_returns'].iloc[-1] if not df['cumulative_strategy_returns'].empty else 0
    bh_total_return = df['cumulative_bh_returns'].iloc[-1] if not df['cumulative_bh_returns'].empty else 0

    # Calculate periods per year based on timeframe
    time_diff = df.index.to_series().diff().median()
    if pd.isna(time_diff):
        periods_per_year = 252 # Default to daily if cannot determine
    else:
        periods_per_year = pd.Timedelta(days=365) / time_diff

    if total_trades >= min_trades_for_stats:
        sharpe_ratio = calculate_sharpe_ratio(df['strategy_log_return'], periods_per_year)
        sortino_ratio = calculate_sortino_ratio(df['strategy_log_return'], periods_per_year)
        max_drawdown = calculate_max_drawdown(df['cumulative_strategy_returns'], debug_log=debug_log) # Pass debug_log
    else:
        sharpe_ratio = -5.0
        sortino_ratio = -5.0
        max_drawdown = 1.0

    bh_sharpe_ratio = calculate_sharpe_ratio(df['log_return'], periods_per_year)
    bh_sortino_ratio = calculate_sortino_ratio(df['log_return'], periods_per_year)
    bh_max_drawdown = calculate_max_drawdown(df['cumulative_bh_returns'], debug_log=debug_log) # Pass debug_log

    strategy_results = {
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'total_trades': total_trades,
        'long_trades': long_trades
    }
    bh_results = {
        'bh_total_return': bh_total_return,
        'bh_sharpe_ratio': bh_sharpe_ratio,
        'bh_sortino_ratio': bh_sortino_ratio,
        'bh_max_drawdown': bh_max_drawdown
    }

    if debug_log:
        print("  --- Backtest Results ---")
        print(f"  Strategy: Return={total_return:.4f}, Sharpe={sharpe_ratio:.4f}, Sortino={sortino_ratio:.4f}, MaxDD={max_drawdown:.4f}, Trades={total_trades}")
        print(f"  Buy&Hold: Return={bh_total_return:.4f}, Sharpe={bh_sharpe_ratio:.4f}, Sortino={bh_sortino_ratio:.4f}, MaxDD={bh_max_drawdown:.4f}")
        print("  --- End Backtest Results ---")

    return df, strategy_results, bh_results, trades_df