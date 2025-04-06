# PK ZigZag Backtester

## Overview

This project provides a framework for developing, backtesting, and optimizing quantitative trading strategies, with an initial focus on a strategy combining the ZigZag indicator and Fibonacci levels. It aims to provide a systematic way to evaluate the profitability and robustness of trading ideas using historical market data.

## Features

*   **Modular Design**: Code is organized into reusable libraries (`lib/`) and strategy-specific modules (`strategies/`).
*   **Vectorized Backtesting**: Utilizes NumPy and Pandas for efficient signal generation and preliminary calculations.
*   **High-Performance Trade Enumeration**: Employs compiled C extensions (`lib/enumerate_trades.c`, `lib/zigzag.c`) for performance-critical operations, significantly speeding up backtests compared to pure Python loops.
*   **Strategy Optimization**: Integrates with the Optuna library for hyperparameter tuning to find optimal strategy parameters.
*   **Data Handling**: Includes utilities for downloading data (e.g., `yfinance`).
*   **Visualization**: Supports plotting results using Plotly, Matplotlib, and Seaborn.
*   **Interactive Dashboard**: Includes a Streamlit application (`streamlit_app.py`) for visualizing backtest results and analysis.

## Architecture

The system follows a modular structure:

```mermaid
graph LR
    A[Data Input (CSV/yfinance)] --> B(Strategy Logic);
    B -- Signals --> C{Backtesting Engine};
    D[lib/indicators.py] --> B;
    E[lib/zigzag.c] --> B;
    F[lib/enumerate_trades.c] --> C;
    G[lib/metrics.py] --> C;
    C -- Results --> H(Analysis / Visualization);
    I[Optuna / lib/optimization.py] --> B;
    J[streamlit_app.py] --> H;
    K[Plotting Libs] --> H;

    subgraph Core Libraries
        D
        G
        I
        K
    end

    subgraph C Extensions
        E
        F
    end

    subgraph Presentation
        J
    end
```

*   **`lib/`**: Contains core functionalities like metrics calculation, plotting utilities, optimization helpers, C extension source code, and the Makefile.
*   **`strategies/`**: Houses the implementation of specific trading strategies (e.g., `zigzag_fib`).
*   **`setup.py`**: Manages the compilation and installation of the C extensions.
*   **`streamlit_app.py`**: An interactive web application for displaying results.
*   **`requirements.txt`**: Lists Python dependencies.

## Installation

1.  **Prerequisites**:
    *   Python 3 (e.g., 3.10+)
    *   A C compiler (like GCC on Linux/macOS, or MSVC build tools on Windows)
    *   Python Development Headers (`python3-dev` on Debian/Ubuntu, `python3-devel` on Fedora/CentOS, included with Python installer on Windows)

2.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd PK-ZigZag-Backtester
    ```

3.  **Create and activate a virtual environment** (Recommended):
    ```bash
    python -m venv venv
    # On Linux/macOS:
    source venv/bin/activate
    # On Windows:
    .\venv\Scripts\activate
    ```

4.  **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Compile and install the C extensions**:
    ```bash
    python setup.py install
    # Or alternatively:
    # pip install .
    ```
    This command compiles the `.c` files in `lib/` and makes them available as a Python package (`PKZigZagBacktesterExtensions`).

## Usage

### Running a Strategy Backtest

Execute the main strategy script. For the ZigZag Fibonacci strategy:

```bash
python zigzag_fib_strategy.py
```

*(Note: Adapt the command if the main execution script is different)*

### Running the Streamlit Dashboard

To view results and potentially interact with the backtester via the web interface:

```bash
streamlit run streamlit_app.py
```

## Extending the Framework

### Adding a New Strategy

1.  Create a new directory under `strategies/`, e.g., `strategies/my_new_strategy/`.
2.  Implement your signal generation logic, potentially in a `signals.py` file within the new directory. This should output buy/sell boolean masks compatible with the backtesting engine.
3.  Create a main script (e.g., `my_new_strategy.py` in the root or strategy directory) that:
    *   Loads data.
    *   Calls your signal generation function.
    *   Uses the backtesting engine (`lib/backtesting.py` or similar) to run the backtest using the generated signals.
    *   Integrates with `lib/optimization.py` if parameter optimization is desired.
    *   Outputs or visualizes the results.

### Modifying C Extensions

1.  Edit the `.c` files in the `lib/` directory.
2.  Recompile and reinstall the extensions using:
    ```bash
    python setup.py install --force
    # Or:
    # pip install . --upgrade --force-reinstall
    ```

## Dependencies

Key Python libraries are listed in `requirements.txt`. Core dependencies include:

*   `pandas`
*   `numpy`
*   `plotly`
*   `matplotlib`
*   `seaborn`
*   `optuna`
*   `streamlit`
*   `yfinance`

The C extensions introduce a dependency on a C compiler and Python development headers during installation.