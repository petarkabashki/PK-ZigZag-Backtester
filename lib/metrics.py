#%%
# Performance Metric Calculation Functions
# -----------------------------------------------------------------------------------------
import pandas as pd
import numpy as np
import logging

def calculate_sharpe_ratio(returns, periods_per_year, risk_free_rate=0):
    """Calculates the annualized Sharpe ratio."""
    if returns is None or len(returns) < 2:
        return -5.0 # Return a low value if insufficient data

    returns = returns[returns != 0] # Exclude periods with zero returns (no position)
    if len(returns) < 2: return -5.0

    mean_return = returns.mean()
    std_dev = returns.std()

    if std_dev == 0 or np.isnan(std_dev):
        # Handle zero standard deviation
        return 10.0 if mean_return > risk_free_rate else -10.0

    # Calculate annualized mean return and standard deviation
    annualized_mean_return = mean_return * periods_per_year
    annualized_std_dev = std_dev * np.sqrt(periods_per_year)

    # Calculate Sharpe Ratio
    sharpe_ratio = (annualized_mean_return - (risk_free_rate * periods_per_year)) / annualized_std_dev

    # Handle potential NaN/inf results from calculation
    if np.isnan(sharpe_ratio) or np.isinf(sharpe_ratio):
        return -5.0 # Return a default low value for invalid results

    return sharpe_ratio

def calculate_sortino_ratio(returns, periods_per_year, target_return=0):
    """Calculates the Sortino ratio."""
    if returns is None or len(returns) < 2:
        return -5.0 # Return a low value if insufficient data

    returns = returns[returns != 0] # Exclude periods with zero returns (no position)
    if len(returns) < 2: return -5.0

    # Calculate downside returns
    downside_returns = returns[returns < target_return]

    # Calculate downside deviation (standard deviation of downside returns)
    downside_deviation = downside_returns.std()

    # Handle zero downside deviation
    if downside_deviation == 0 or np.isnan(downside_deviation):
        # If mean return is positive, Sortino is infinite (good), return large positive
        # If mean return is non-positive, Sortino is undefined or negative (bad), return large negative
        mean_return = returns.mean()
        return 10.0 if mean_return > target_return else -10.0

    # Calculate annualized mean return
    annualized_mean_return = returns.mean() * periods_per_year

    # Calculate annualized downside deviation
    annualized_downside_deviation = downside_deviation * np.sqrt(periods_per_year)

    # Calculate Sortino Ratio
    sortino_ratio = (annualized_mean_return - (target_return * periods_per_year)) / annualized_downside_deviation

    # Handle potential NaN/inf results from calculation
    if np.isnan(sortino_ratio) or np.isinf(sortino_ratio):
        return -5.0 # Return a default low value for invalid results

    return sortino_ratio

def calculate_max_drawdown(cumulative_returns, debug_log=False):
    """Calculates the Maximum Drawdown percentage from cumulative returns."""
    if debug_log: print("\n--- DEBUG: calculate_max_drawdown ---")
    if cumulative_returns is None or len(cumulative_returns) < 2:
        if debug_log: print("  Insufficient data, returning 1.0")
        return 1.0 # Return 100% drawdown if insufficient data

    if debug_log:
        print(f"  Input cumulative_returns (len={len(cumulative_returns)}):")
        print(cumulative_returns.head())
        print(cumulative_returns.tail())
        print(cumulative_returns.describe())

    # Calculate equity curve (assuming starting capital of 1)
    # Ensure the curve starts at 1 (initial capital)
    # Forward fill NaNs first to handle potential gaps in returns before cumprod
    equity_curve = (1 + cumulative_returns).ffill().fillna(1) # Forward fill NaNs first
    if debug_log:
        print(f"\n  Equity Curve (len={len(equity_curve)}):")
        print(equity_curve.head())
        print(equity_curve.tail())
        print(equity_curve.describe())

    # Prepend the initial capital value (1) before calculating cumulative max
    # This ensures the peak calculation starts correctly from 1
    initial_capital = pd.Series([1.0], index=[equity_curve.index[0] - pd.Timedelta(seconds=1)]) # Create a point just before the start
    equity_curve_with_start = pd.concat([initial_capital, equity_curve])

    # Calculate peak equity using the curve that includes the initial capital
    cumulative_high = equity_curve_with_start.cummax()
    # Remove the prepended initial capital point before calculating drawdown
    cumulative_high = cumulative_high.iloc[1:]

    # Ensure cumulative_high has the same index as equity_curve
    cumulative_high = cumulative_high.reindex(equity_curve.index, method='ffill').fillna(1.0) # Reindex and fill potential NaNs
    if debug_log:
        print(f"\n  Cumulative High (len={len(cumulative_high)}):")
        print(cumulative_high.head())
        print(cumulative_high.tail())
        print(cumulative_high.describe())

    # Calculate drawdown in percentage terms relative to the actual peak
    peak_for_division = cumulative_high.replace(0, np.nan) # Avoid division by zero
    drawdown_percentage = (cumulative_high - equity_curve) / peak_for_division
    drawdown_percentage = drawdown_percentage.fillna(0) # Handle NaNs from division by zero

    if debug_log:
        print(f"\n  Drawdown Percentage Series (len={len(drawdown_percentage)}):")
        print(drawdown_percentage.head())
        print(drawdown_percentage.tail())
        print(drawdown_percentage.describe())
        print(f"  Max value in drawdown_percentage: {drawdown_percentage.max():.6f}")


    max_drawdown_percentage = drawdown_percentage.max()

    # Handle cases where max drawdown is NaN (e.g., flat equity curve)
    if np.isnan(max_drawdown_percentage):
        if debug_log: print("  Max drawdown is NaN, returning 0.0")
        return 0.0

    # Return the raw drawdown percentage
    final_max_dd = max_drawdown_percentage
    if debug_log: print(f"  Final Max Drawdown Returned: {final_max_dd:.6f}")
    return final_max_dd

# Helper function
def get_periods_per_year(timeframe_str):
    """Estimates periods per year based on timeframe string."""
    timeframe_str = str(timeframe_str).lower() # Ensure string and lowercase
    try:
        if 'm' in timeframe_str: # Minutes
            minutes = int(timeframe_str.replace('m', ''))
            if minutes <= 0: return 252 # Avoid division by zero
            # Use 365.25 for slightly more accuracy including leap years
            return (60 / minutes) * 24 * 365.25
        elif 'h' in timeframe_str: # Hours
            hours = int(timeframe_str.replace('h', ''))
            if hours <= 0: return 252
            return (24 / hours) * 365.25
        elif 'd' in timeframe_str: # Days
            days = int(timeframe_str.replace('d', ''))
            if days <= 0: return 252
            return 365.25 / days
        elif 'w' in timeframe_str: # Weeks
            return 52.1775 # 365.25 / 7
        elif 'mo' in timeframe_str: # Months
            return 12
        else:
            # Default to 252 trading days if format is unrecognized or implies trading days
            logging.warning(f"Unrecognized timeframe format '{timeframe_str}', defaulting to 252 periods per year.")
            return 252
    except ValueError:
        logging.warning(f"Could not parse timeframe format '{timeframe_str}', defaulting to 252 periods per year.")
        return 252

def calculate_metrics(strategy_returns, benchmark_returns, trades_df, periods_per_year, risk_free_rate=0, target_return=0, debug_log=False):
    """
    Calculates a standard set of performance metrics for a strategy and benchmark.

    Args:
        strategy_returns (pd.Series): Series of strategy log returns (non-cumulative).
        benchmark_returns (pd.Series): Series of benchmark log returns (non-cumulative).
        trades_df (pd.DataFrame): DataFrame of trades executed by the strategy.
                                   Expected columns might include 'EntryTime', 'ExitTime', etc.
                                   Used primarily to count the number of trades.
        periods_per_year (int): Number of periods in a year (e.g., 252 for daily, 365*24 for hourly).
        risk_free_rate (float): Annual risk-free rate for Sharpe ratio calculation.
        target_return (float): Target return for Sortino ratio calculation.
        debug_log (bool): If True, enable debug prints in max drawdown calculation.

    Returns:
        pd.DataFrame: DataFrame containing calculated metrics.
                      Index: Metric names (e.g., 'Cumulative Return', 'Max Drawdown').
                      Columns: ['Strategy', 'Benchmark'].
    """
    metrics = {}

    # Ensure returns are Series and handle potential Nones/NaNs
    strategy_returns = pd.Series(strategy_returns).fillna(0)
    benchmark_returns = pd.Series(benchmark_returns).fillna(0)

    # --- Cumulative Returns ---
    # Use simple returns derived from log returns for cumulative calculation
    strat_simple_ret = np.exp(strategy_returns) - 1
    bench_simple_ret = np.exp(benchmark_returns) - 1
    strat_cum_ret_pct = (1 + strat_simple_ret).cumprod() - 1
    bench_cum_ret_pct = (1 + bench_simple_ret).cumprod() - 1

    metrics['Cumulative Return'] = {
        'Strategy': strat_cum_ret_pct.iloc[-1] if not strat_cum_ret_pct.empty else 0,
        'Benchmark': bench_cum_ret_pct.iloc[-1] if not bench_cum_ret_pct.empty else 0
    }

    # --- Max Drawdown ---
    # Pass percentage cumulative returns to calculate_max_drawdown
    metrics['Max Drawdown'] = {
        'Strategy': calculate_max_drawdown(strat_cum_ret_pct, debug_log=debug_log),
        'Benchmark': calculate_max_drawdown(bench_cum_ret_pct, debug_log=debug_log)
    }

    # --- Sharpe Ratio (uses log returns) ---
    metrics['Sharpe Ratio'] = {
        'Strategy': calculate_sharpe_ratio(strategy_returns, periods_per_year, risk_free_rate),
        'Benchmark': calculate_sharpe_ratio(benchmark_returns, periods_per_year, risk_free_rate)
    }

    # --- Sortino Ratio (uses log returns) ---
    metrics['Sortino Ratio'] = {
        'Strategy': calculate_sortino_ratio(strategy_returns, periods_per_year, target_return),
        'Benchmark': calculate_sortino_ratio(benchmark_returns, periods_per_year, target_return)
    }

    # --- Total Trades ---
    total_trades = len(trades_df) if trades_df is not None and not trades_df.empty else 0
    metrics['Total Trades'] = {
        'Strategy': total_trades,
        'Benchmark': np.nan # Not applicable for benchmark
    }

    # --- Annualized Return ---
    # Calculate based on total time span and cumulative return
    annualized_ret_strat = 0
    if not strategy_returns.empty and periods_per_year > 0:
        time_span_years = len(strategy_returns) / periods_per_year
        if time_span_years > 0:
            # Ensure base is positive before exponentiation
            base_strat = 1 + metrics['Cumulative Return']['Strategy']
            # Handle potential negative base for fractional exponent
            annualized_ret_strat = (np.sign(base_strat) * (np.abs(base_strat) ** (1 / time_span_years))) - 1
        # else: annualized_ret_strat remains 0

    annualized_ret_bench = 0
    if not benchmark_returns.empty and periods_per_year > 0:
        time_span_years_bench = len(benchmark_returns) / periods_per_year
        if time_span_years_bench > 0:
            base_bench = 1 + metrics['Cumulative Return']['Benchmark']
            annualized_ret_bench = (np.sign(base_bench) * (np.abs(base_bench) ** (1 / time_span_years_bench))) - 1
        # else: annualized_ret_bench remains 0

    metrics['Annualized Return'] = {
        'Strategy': annualized_ret_strat,
        'Benchmark': annualized_ret_bench
    }

    # Convert dictionary to DataFrame
    metrics_df = pd.DataFrame(metrics).T # Transpose to get metrics as index

    # Add Benchmark column if it doesn't exist (e.g., if benchmark_returns was empty)
    if 'Benchmark' not in metrics_df.columns:
        metrics_df['Benchmark'] = np.nan

    # Ensure correct column order
    metrics_df = metrics_df[['Strategy', 'Benchmark']]

    return metrics_df.round(4) # Round for display
