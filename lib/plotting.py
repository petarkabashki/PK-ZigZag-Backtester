#%%
# Plotting Functions
# -----------------------------------------------------------------------------------------
import matplotlib.pyplot as plt
import numpy as np
import os

# Ensure non-interactive backend is set if this module is imported early
import matplotlib
matplotlib.use('Agg')

def plot_backtest_results(df, strategy_results, bh_results, title_suffix="", filename="backtest_results.png"):
    """Plots the cumulative returns of the strategy vs Buy & Hold."""
    if df is None or 'cumulative_strategy_returns' not in df.columns or 'cumulative_bh_returns' not in df.columns:
        print("WARN: Cannot plot results, DataFrame is missing required cumulative return columns.")
        return

    plt.figure(figsize=(12, 8))

    # Plot cumulative returns
    plt.plot(df.index, df['cumulative_strategy_returns'] * 100, label=f'Strategy (Long) ({strategy_results.get("sharpe_ratio", np.nan):.2f} Sharpe)', color='blue')
    plt.plot(df.index, df['cumulative_bh_returns'] * 100, label=f'Buy & Hold ({bh_results.get("bh_sharpe_ratio", np.nan):.2f} Sharpe)', color='grey', linestyle='--')

    # Add title and labels
    title = f'Backtest Results: ZigZag+Fib+Wick Entry / Fractal Exit\n{title_suffix}'
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel('Cumulative Return (%)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # Save the plot
    try:
        # Ensure the directory exists if filename includes a path
        dir_name = os.path.dirname(filename)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        plt.savefig(filename)
        print(f"Plot saved to {filename}")
    except Exception as e:
        print(f"Error saving plot: {e}")
    plt.close() # Close the plot to free memory