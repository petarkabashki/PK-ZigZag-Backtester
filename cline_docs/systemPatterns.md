# System Patterns

## Architecture Overview

The system follows a modular approach for developing and backtesting a quantitative trading strategy.

1.  **Data Input**: Historical price data (OHLCV) is the primary input.
2.  **Core Logic (Strategy)**:
    *   Located likely within the `strategies/` directory (e.g., `strategies/zigzag_fib/`).
    *   Calculates indicators (ZigZag, Fibonacci) using functions potentially from the `lib/` directory or external libraries.
    *   Generates trading signals (buy/sell masks) based on defined rules.
3.  **Backtesting Engine**:
    *   Uses `lib/enumerate_trades.c` (compiled C extension) to efficiently convert signal masks into discrete trades.
    *   Calculates performance metrics using vectorized log returns (likely functions in `lib/metrics.py`).
4.  **Optimization**: Leverages the Optuna library (`lib/optimization.py` might contain wrappers or helpers) to find optimal strategy parameters.
5.  **Utilities**: The `lib/` directory contains helper functions for various tasks (indicators, plotting, utilities).
6.  **Presentation**: Results might be presented via scripts, notebooks, or potentially a Streamlit app (`streamlit_app.py`).

## Key Technical Decisions

*   **Vectorized Backtesting**: Using boolean masks and vectorized operations (NumPy/Pandas) for signal generation and initial performance calculation is efficient.
*   **C Extension for Trade Enumeration**: `lib/enumerate_trades.c` is used for performance-critical conversion of signals to trades, avoiding slow Python loops.
*   **Modular Libraries**: Separating concerns into different modules (`lib/`, `strategies/`) promotes reusability and maintainability.
*   **Optuna for Optimization**: Using a dedicated library like Optuna simplifies the process of hyperparameter tuning.