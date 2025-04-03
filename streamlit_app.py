#%%
# streamlit_app.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import optuna
from optuna.exceptions import TrialPruned
import logging
import traceback
import os # Keep os import if load_data_optimized needs it, remove if not. Assuming it might.

# %% Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# %% Import project modules (handle potential import errors)
try:
    from lib.util import load_candles # Corrected import
    from strategies.zigzag_fib.signals import generate_signals
    from lib.backtesting import run_backtest
    from lib.metrics import calculate_metrics, get_periods_per_year
    from lib.plotting import plot_backtest_results
    # Assuming run_optimization handles study creation, objective wrapping, and execution
    from lib.optimization import run_optimization, set_optimization_data, analyze_optimization_results # Import necessary functions
except ImportError as e:
    st.error(f"Error importing project modules: {e}. Make sure the project is installed correctly (e.g., `pip install .`) or paths are set.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during module import: {e}")
    logging.error(traceback.format_exc())
    st.stop()

# %% Helper Function to Parse Symbol
def parse_symbol(symbol):
    """Parses a symbol like 'ETHUSDT' into base ('ETH') and quote ('USDT')."""
    # Common quote assets (add more if needed)
    quote_assets = ['USDT', 'BTC', 'ETH', 'USD', 'EUR', 'GBP', 'BUSD', 'USDC']
    for quote in quote_assets:
        if symbol.endswith(quote):
            base = symbol[:-len(quote)]
            return base, quote
    # Fallback or error if no known quote asset is found
    raise ValueError(f"Could not parse symbol '{symbol}'. Unknown quote asset.")


# %% App Title
st.title("ZigZag Fibonacci Strategy Backtester & Optimizer")

# %% Sidebar for Inputs
st.sidebar.header("Configuration")

# %% Data Loading Inputs
st.sidebar.subheader("Data")
symbol = st.sidebar.text_input("Symbol", "ETHUSDT")
timeframe = st.sidebar.text_input("Timeframe", "8h")
exchange = st.sidebar.text_input("Exchange", "kucoin") # Added exchange input

# %% Load Data Function (Optimized) - Keep this definition
# Assuming load_data_optimized is defined elsewhere or needs to be defined here.
# For now, using the corrected load_candles import directly.
@st.cache_data # Cache the data loading
def load_data_optimized(exchange, symbol, timeframe): # Added exchange param
    """Loads candle data, handling potential errors."""
    try:
        # Construct the expected path based on common conventions or config
        # Example: Assumes data is in a 'data/' subdirectory relative to the app
        # data_dir = os.path.join(os.path.dirname(__file__), '..', 'data') # Adjust path as needed
        # file_path = os.path.join(data_dir, f"{symbol}_{timeframe}.csv") # Example filename
        # Or directly use load_candles if it handles path resolution
        base, quote = parse_symbol(symbol) # Parse the symbol
        df = load_candles(exchange, base, quote, timeframe) # Use the imported function with all args

        if df.empty:
            st.warning(f"No data found for {symbol} ({timeframe}). Check data source.")
            return pd.DataFrame() # Return empty DataFrame

        # Basic validation
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
             raise ValueError(f"Data must contain columns: {required_columns}")
        if not isinstance(df.index, pd.DatetimeIndex):
             # Attempt conversion if possible, otherwise raise error
             try:
                 df.index = pd.to_datetime(df.index)
             except Exception:
                 raise ValueError("Data index must be a DatetimeIndex.")
        return df
    except FileNotFoundError:
        st.error(f"Data file not found for {symbol} ({timeframe}). Please ensure data exists in the expected location.")
        return pd.DataFrame() # Return empty DataFrame on error
    except Exception as e:
        st.error(f"Error loading data for {symbol} ({timeframe}): {e}")
        logging.error(f"Data loading error: {traceback.format_exc()}")
        return pd.DataFrame() # Return empty DataFrame on error


# %% Load Data Call
data = None
try:
    data = load_data_optimized(exchange, symbol, timeframe) # Pass exchange
    if not data.empty:
        st.sidebar.success(f"Loaded {len(data)} rows for {symbol} ({timeframe})")
    else:
        st.sidebar.warning("Data loaded but is empty.")
        # Don't stop here, allow app to load but show warnings later
except Exception as e:
    # Error already handled in load_data_optimized, but catch any unexpected ones
    st.error(f"An unexpected error occurred during data loading setup: {e}")
    logging.error(traceback.format_exc())
    st.stop()


if data is None or data.empty:
    st.warning("Could not load data. Please check the symbol/timeframe and ensure data files exist.")
    # Optionally stop if data is absolutely required for the rest of the app layout
    # st.stop()
else:
    # %% Strategy Parameter Inputs (Only if data loaded)
    st.sidebar.subheader("Strategy Parameters")

    # Default parameters from optimization results mentioned in the task
    default_params = {
        'zigzag_epsilon': 0.125,
        'entry_fib': 0.5,
        'stop_entry_fib': 0.786,
        'wick_lookback': 9,
        'fractal_n': 3,
        'take_profit_fib': 1.618, # Reasonable default
        'stop_loss_fib': 0.0,     # Reasonable default (stop at entry pivot)
        'exit_type': 'fractal',   # Based on optimization results filenames
        'trade_direction': 'long' # Common default
    }

    params = {}
    params['zigzag_epsilon'] = st.sidebar.slider("ZigZag Epsilon", 0.01, 0.2, default_params['zigzag_epsilon'], 0.001, format="%.3f")
    params['entry_fib'] = st.sidebar.slider("Entry Fib Level", 0.236, 0.786, default_params['entry_fib'], 0.001, format="%.3f")
    params['stop_entry_fib'] = st.sidebar.slider("Stop Entry Fib Level", 0.618, 1.0, default_params['stop_entry_fib'], 0.001, format="%.3f")
    params['wick_lookback'] = st.sidebar.number_input("Wick Lookback", 1, 20, default_params['wick_lookback'], 1)
    params['fractal_n'] = st.sidebar.number_input("Fractal N", 2, 10, default_params['fractal_n'], 1)
    params['take_profit_fib'] = st.sidebar.slider("Take Profit Fib Level", 1.0, 2.618, default_params['take_profit_fib'], 0.001, format="%.3f")
    params['stop_loss_fib'] = st.sidebar.slider("Stop Loss Fib Level", 0.0, 1.0, default_params['stop_loss_fib'], 0.001, format="%.3f")
    params['exit_type'] = st.sidebar.selectbox("Exit Type", ['fib', 'fractal'], index=['fib', 'fractal'].index(default_params['exit_type']))
    params['trade_direction'] = st.sidebar.selectbox("Trade Direction", ['long', 'short', 'both'], index=['long', 'short', 'both'].index(default_params['trade_direction']))

    # %% Manual Backtest Section (Only if data loaded)
    st.sidebar.subheader("Manual Backtest")
    run_backtest_button = st.sidebar.button("Run Backtest with Current Parameters")

    if run_backtest_button:
        st.header("Manual Backtest Results")
        try:
            with st.spinner("Running backtest..."):
                # 1. Generate Signals (Call function directly)
                signals_df = generate_signals(data.copy(), **params) # Pass params dict

                signals_df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume' # Rename volume too for consistency if needed elsewhere
                }, inplace=True)

                # Ensure required columns exist after renaming (adjust as needed for run_backtest)
                # Example check - modify required_cols_for_backtest based on actual run_backtest input needs
                required_cols_for_backtest = ['Open', 'High', 'Low', 'Close'] # Basic OHLC check
                if 'entry_long' in params.get('trade_direction', 'long'): required_cols_for_backtest.extend(['entry_long', 'exit_long'])
                if 'entry_short' in params.get('trade_direction', 'long'): required_cols_for_backtest.extend(['entry_short', 'exit_short'])

                missing_cols = [col for col in required_cols_for_backtest if col not in signals_df.columns and col in ['Open', 'High', 'Low', 'Close']]
                # Check for signal columns only if they are expected by run_backtest based on its signature or internal logic
                # Assuming run_backtest needs the signal columns passed in the call signature

                if missing_cols:
                    st.error(f"Internal Error: Missing required OHLC columns after renaming for backtest: {missing_cols}")
                    # Consider stopping or handling gracefully
                    # st.stop()
                elif not all(sc in signals_df.columns for sc in ['entry_long', 'exit_long', 'entry_short', 'exit_short']):
                     st.warning(f"Signal columns might be missing, check generate_signals output and run_backtest requirements.")


                # 3. Run Backtest
                # Unpack all four return values
                backtest_df, strategy_results, bh_results, trades_df_raw = run_backtest(signals_df)

                # 4. Calculate Metrics
                periods = get_periods_per_year(timeframe)
                # Use the unpacked DataFrame and trades_df for metrics
                metrics_df = calculate_metrics(backtest_df['strategy_log_return'], backtest_df['log_return'], trades_df_raw, periods)

                # 5. Plot Results
                fig = plot_backtest_results(
                    results['cumulative_returns'],
                    results['benchmark_cumulative_returns'],
                    results['trades'],
                    signals_df # Pass the dataframe with price data for plotting
                )

            # Display Results
            st.subheader("Performance Metrics")
            st.dataframe(metrics_df)

            st.subheader("Equity Curve & Trades")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Trades List")
            st.dataframe(results['trades'])

        except Exception as e:
            st.error(f"Error during manual backtest: {e}")
            logging.error(traceback.format_exc())

    # %% Optimization Section (Only if data loaded)
    st.sidebar.subheader("Optimization")
    n_trials = st.sidebar.number_input("Number of Trials", min_value=10, value=70, step=10)
    run_optimization_button = st.sidebar.button("Run Optimization")

    if run_optimization_button:
        st.header("Optimization Results")

        # Define the objective function for Optuna within this scope to capture data
        # Need to define objective_decorator or remove it if not used
        # Assuming objective_decorator is defined elsewhere or we adapt
        # For now, let's define a simple objective directly
        def objective(trial, data_df): # Removed decorator for simplicity, pass data directly
            # Define search space for parameters
            opt_params = {
                'zigzag_epsilon': trial.suggest_float('zigzag_epsilon', 0.01, 0.2),
                'entry_fib': trial.suggest_float('entry_fib', 0.236, 0.786),
                'stop_entry_fib': trial.suggest_float('stop_entry_fib', 0.618, 1.0),
                'wick_lookback': trial.suggest_int('wick_lookback', 1, 20),
                'fractal_n': trial.suggest_int('fractal_n', 2, 10),
                'take_profit_fib': trial.suggest_float('take_profit_fib', 1.0, 2.618),
                'stop_loss_fib': trial.suggest_float('stop_loss_fib', 0.0, 1.0),
                'exit_type': trial.suggest_categorical('exit_type', ['fib', 'fractal']),
                'trade_direction': trial.suggest_categorical('trade_direction', ['long', 'short', 'both'])
            }

            try:
                # Generate Signals
                # Assuming generate_signals can accept the data and params
                signals_df = generate_signals(data_df.copy(), **opt_params) # Use data passed to objective

                # Run Backtest
                results = run_backtest(signals_df)
                # Calculate Metrics
                periods = get_periods_per_year(timeframe) # Use timeframe from outer scope
                metrics_df = calculate_metrics(results['returns'], results['benchmark_returns'], results['trades'], periods)

                # Define the objective value (e.g., Sharpe Ratio)
                objective_value = metrics_df.loc['Sharpe Ratio', 'Strategy']
                if pd.isna(objective_value) or not isinstance(objective_value, (int, float)):
                     logging.warning(f"Trial {trial.number} resulted in invalid Sharpe Ratio ({objective_value}). Pruning.")
                     raise TrialPruned()

                # Optional: Add constraint (e.g., minimum number of trades)
                min_trades = 5
                if metrics_df.loc['Total Trades', 'Strategy'] < min_trades:
                     logging.warning(f"Trial {trial.number} resulted in {metrics_df.loc['Total Trades', 'Strategy']} trades (less than {min_trades}). Pruning.")
                     raise TrialPruned()

                return objective_value

            except TrialPruned:
                 raise # Re-raise TrialPruned
            except Exception as e:
                logging.error(f"Error in trial {trial.number}: {e}\n{traceback.format_exc()}")
                return -float('inf') # Return a very low value


        try:
            with st.spinner(f"Running Optuna optimization for {n_trials} trials..."):
                # Pass data to the objective function using a lambda or functools.partial
                from functools import partial
                objective_with_data = partial(objective, data_df=data.copy())

                study = run_optimization(
                    objective_func=objective_with_data, # Use the function with data bound
                    n_trials=n_trials,
                    direction='maximize', # Maximize Sharpe Ratio
                    study_name=f"streamlit_opt_{symbol}_{timeframe}", # Optional: Name the study
                    storage=None # Use in-memory storage for simplicity in Streamlit
                )

            st.subheader("Optimization Summary")
            st.write(f"Optimization finished after {len(study.trials)} trials.")
            st.write("Best Parameters:")
            st.json(study.best_params)
            st.write("Best Value (Sharpe Ratio):")
            st.write(study.best_value)

            # Display Optuna plots
            st.subheader("Optimization Analysis")
            try:
                fig_history = optuna.visualization.plot_optimization_history(study)
                st.plotly_chart(fig_history, use_container_width=True)

                fig_importance = optuna.visualization.plot_param_importances(study)
                st.plotly_chart(fig_importance, use_container_width=True)

                # Pareto front is for multi-objective, plot if applicable
                if study.directions and len(study.directions) > 1:
                     fig_pareto = optuna.visualization.plot_pareto_front(study)
                     st.plotly_chart(fig_pareto, use_container_width=True)

            except Exception as plot_error:
                st.warning(f"Could not generate all optimization plots: {plot_error}")
                logging.warning(f"Plotting error: {plot_error}\n{traceback.format_exc()}")


        except ImportError as ie:
             st.error(f"Optuna visualization failed. Ensure necessary libraries are installed: {ie}")
             logging.error(traceback.format_exc())
        except Exception as e:
            st.error(f"Error during optimization: {e}")
            logging.error(traceback.format_exc())

# %% Footer or additional info
st.sidebar.markdown("---")
st.sidebar.info("Developed using the PK-ZigZag-Backtester framework.")