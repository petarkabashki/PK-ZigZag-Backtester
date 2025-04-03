# Product Context

## Purpose

This project aims to develop, rigorously backtest, and optimize a quantitative trading strategy based on the ZigZag indicator and Fibonacci levels.

## Problem Solved

Provides a systematic way to evaluate the profitability and robustness of a specific trading idea that combines price pattern recognition (ZigZag pivots) with potential support/resistance levels (Fibonacci retracements/extensions).

## How it Should Work

1.  **Data Acquisition**: Obtain historical price data (OHLCV) for assets (e.g., stocks, crypto).
2.  **Indicator Calculation**:
    *   Calculate ZigZag pivots based on a specified deviation threshold.
    *   Identify significant highs and lows from the ZigZag indicator.
    *   Calculate Fibonacci retracement and extension levels based on the price range between consecutive significant ZigZag pivots.
3.  **Signal Generation**: Define entry and exit rules based on price interacting with the calculated Fibonacci levels relative to the ZigZag pivots.
    *   Example Entry: Buy when price retraces to the 61.8% level after an upward ZigZag move.
    *   Example Exit: Sell at a predefined profit target (e.g., 161.8% extension) or stop-loss level.
4.  **Backtesting**:
    *   Generate boolean buy/sell signal masks based on the rules.
    *   Use the `lib/enumerate_trades.c` module (or a Python wrapper) to convert these masks into a series of trade entry/exit points.
    *   Calculate performance metrics using vectorized log returns (e.g., cumulative returns, Sharpe ratio, drawdown).
5.  **Optimization**: Use Optuna to find the optimal parameters for the ZigZag indicator (e.g., deviation threshold) and Fibonacci levels/rules (e.g., specific retracement level for entry, target/stop levels) that maximize a chosen objective function (e.g., Sharpe ratio).
6.  **Analysis**: Perform sensitivity analysis on the optimized parameters to understand how strategy performance changes with small variations in the parameters.
7.  **Output**: Present the backtest results, optimization process, and sensitivity analysis clearly, potentially using visualizations.