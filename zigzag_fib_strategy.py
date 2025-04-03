#%%
# Zigzag Fibonacci Strategy Runner (Long-Only, Fractal Exit, Multi-Objective Optimized: Sharpe/Drawdown with Constraint)
# -----------------------------------------------------------------------------------------
# This script orchestrates the backtesting and optimization process by importing
# functions from the 'lib' directory.

#%% Step 1: Load necessary libraries & Setup
import matplotlib # Import matplotlib first
matplotlib.use('Agg') # Set non-interactive backend BEFORE importing pyplot
import pandas as pd
import numpy as np
import time
import sys
import matplotlib.pyplot as plt
import seaborn as sns
import optuna
import os
import shutil # Import shutil for directory cleanup

# --- Directory Cleanup ---
output_dir = "optimization_results"
print(f"\n--- Cleaning up directory: {output_dir} ---")
if os.path.isdir(output_dir):
    for filename in os.listdir(output_dir):
        file_path = os.path.join(output_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
                print(f"Deleted file: {file_path}")
            elif os.path.isdir(file_path):
                # Optionally remove subdirectories too, but the request was for files
                # shutil.rmtree(file_path)
                # print(f"Deleted directory: {file_path}")
                print(f"Skipping directory: {file_path}")
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')
else:
    print(f"Directory {output_dir} does not exist, skipping cleanup.")
# --- End Cleanup ---


# Create output directory if it doesn't exist (it might have been deleted if it was empty and cleanup removed it)
os.makedirs(output_dir, exist_ok=True)
print(f"Ensured directory exists: {output_dir}")


sns.set_style('darkgrid')
optuna.logging.set_verbosity(optuna.logging.WARNING) # Reduce Optuna verbosity

# Import functions from the lib package
try:
    from lib.util import load_candles
    from strategies.zigzag_fib.signals import generate_signals # <-- Updated path
    from lib.backtesting import run_backtest
    from lib.plotting import plot_backtest_results
    from lib.optimization import set_optimization_data, set_max_drawdown_constraint, run_optimization, analyze_optimization_results
    # C extensions are imported within their respective modules (indicators, backtesting)
    print("Successfully imported functions from lib package.")
except ImportError as e:
    print(f"Error importing from lib package: {e}")
    print("Ensure the lib directory is structured correctly and __init__.py exists.")
    sys.exit(1) # Exit if core components cannot be imported

#%% Step 2: Load price data
# --- Timeframe is kept at 8h ---
exchange, base, quote, timeframe = 'binance', 'ETH', 'USDT', '8h'
print(f"\n--- Loading Data: {exchange} {base}/{quote} {timeframe} ---")
data_full = load_candles(exchange, base, quote, timeframe)

data_global_for_opt = None # Initialize
if data_full is not None:
    required_cols = ['Open', 'High', 'Low', 'Close'] # Use correct casing
    if all(col in data_full.columns for col in required_cols):
        # Use correct casing when selecting columns
        data_global_for_opt = data_full[['Open', 'High', 'Low', 'Close']].copy() # Prepare data for optimization
        print(f"Data loaded successfully: {len(data_global_for_opt)} rows")
    else:
        print(f"Error: Loaded data missing required columns: {required_cols}")
        data_global_for_opt = None
else:
    print("Failed to load data.")

if data_global_for_opt is None:
    print("Exiting script due to data loading failure.")
    sys.exit(1)

#%% Step 3: Run single backtest with default parameters
# --- Default parameters updated to match generate_signals signature ---
default_params = {
    'zigzag_epsilon': 0.03,
    'entry_fib': 0.618,
    'stop_entry_fib': 0.786,
    'wick_lookback': 5,
    'fractal_n': 2,
    'exit_type': 'fractal', # Use exit_type instead of use_fractal_exit
    # 'take_profit_fib' and 'stop_loss_fib' are not needed for fractal exit, but generate_signals accepts them
    # 'trade_direction' defaults to 'long' in generate_signals
}

print("\n--- Running Single Backtest with Default Parameters ---")
signals_df_default = generate_signals(data_global_for_opt, **default_params)
results_df_default, strategy_res_default, bh_res_default, trades_df_default = None, {}, {}, None # Initialize, added trades_df

if signals_df_default is not None:
    # Pass the correct columns to run_backtest, ensure casing matches DataFrame
    backtest_input_df = signals_df_default.rename(columns={
        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'
    })
    results_df_default, strategy_res_default, bh_res_default, trades_df_default = run_backtest(backtest_input_df, debug_log=False) # Keep debug off for default run, capture trades_df

    if results_df_default is not None:
        print("Default Strategy Results:")
        for key, value in strategy_res_default.items(): print(f"  {key}: {value:.4f}")
        print("\nDefault Buy & Hold Results:")
        for key, value in bh_res_default.items(): print(f"  {key}: {value:.4f}")

        # Plot default results
        plot_filename_default = os.path.join(output_dir, f"default_backtest_results_{base}{quote}_{timeframe}_long_fractalexit_multiobj_sharpe_ddconstraint.png")
        plot_backtest_results(results_df_default, strategy_res_default, bh_res_default,
                              title_suffix=f"Default Params ({base}{quote} {timeframe})",
                              filename=plot_filename_default)
    else:
        print("Default backtest failed to produce results.")
else:
    print("Failed to generate signals with default parameters.")


#%% Step 4: Run Optuna optimization
# --- Optuna settings are kept (n_trials=70, timeout=300) --- # Updated n_trials comment
# --- Multi-objective optimization with constraint ---
N_TRIALS = 70 # <-- Changed from 30 to 70
TIMEOUT = 300 # seconds
MAX_DRAWDOWN_CONSTRAINT = 0.60 # 60%

print(f"\n--- Running Optuna Multi-Objective Optimization (Sharpe Max, Drawdown Min, DD Constraint < {MAX_DRAWDOWN_CONSTRAINT:.0%}) ---")
print(f"Parameters: n_trials={N_TRIALS}, timeout={TIMEOUT}s")

# Set data and constraint for the objective function in the optimization module
set_optimization_data(data_global_for_opt) # Use correct casing
set_max_drawdown_constraint(MAX_DRAWDOWN_CONSTRAINT)

# Use a persistent study name and storage
study_name = f"zigzag_fib_fractal_{base}{quote}_{timeframe}_multiobj_sharpe_ddconstraint" # Unique name
storage_name = f"sqlite:///{output_dir}/{study_name}.db"

# Run the optimization
study = run_optimization(N_TRIALS, TIMEOUT, study_name, storage_name)

#%% Step 5: Analyze Optimization Results
print("\n--- Analyzing Optimization Results ---")
analyze_optimization_results(study, strategy_res_default, bh_res_default, base, quote, timeframe, output_dir, study_name)

print("\n--- Script Finished ---")