# Active Context

## Current Focus

The primary goal is to implement, backtest, optimize, and analyze a trading strategy based on ZigZag indicator pivots and associated Fibonacci levels.

## Recent Changes

-   Initiated the task.
-   Clarified that the backtesting should use `lib/enumerate_trades.c` for trade signal processing and vectorized log returns for performance calculation.
-   Created the `cline_docs/productContext.md` file.

## Next Steps

1.  Create the remaining Memory Bank files:
    *   `cline_docs/systemPatterns.md`
    *   `cline_docs/techContext.md`
    *   `cline_docs/progress.md`
2.  Begin implementing the core strategy logic:
    *   Load price data.
    *   Implement or wrap the ZigZag calculation (potentially using `lib/zigzag.c`).
    *   Implement Fibonacci level calculation based on ZigZag pivots.
    *   Define initial entry/exit rules based on price interaction with Fib levels.
    *   Generate buy/sell signal masks.
3.  Implement the backtesting mechanism using `lib/enumerate_trades.c` and log returns.
4.  Set up the Optuna optimization study.
5.  Perform sensitivity analysis on the optimized parameters.
6.  Ensure the existing `zigzag_fibs.ipynb` notebook is not modified. Development will likely occur in `zigzag_fib_strategy.py` or a new file.