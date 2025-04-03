# Technical Context

## Technologies Used

*   **Primary Language**: Python 3 (likely 3.11 based on build paths)
*   **Core Libraries**:
    *   `pandas`: Data manipulation and time series analysis.
    *   `numpy`: Numerical computation, array operations.
*   **Visualization**:
    *   `plotly`: Interactive charts and graphs.
    *   `matplotlib`: Static plotting.
    *   `seaborn`: Enhanced statistical visualizations.
*   **Optimization**:
    *   `optuna`: Hyperparameter optimization framework.
*   **Data Acquisition**:
    *   `yfinance`: Downloading historical market data from Yahoo Finance.
*   **Web Framework (Optional/Presentation)**:
    *   `streamlit`: Building interactive web applications for results display (`streamlit_app.py`).
*   **Performance Extensions**:
    *   `C`: Used for performance-critical code (`lib/zigzag.c`, `lib/enumerate_trades.c`). Compiled into a Python extension (`PKZigZagBacktesterExtensions`) likely via `setup.py` and `lib/Makefile`.

## Development Setup

1.  **Environment**: A Python virtual environment is recommended.
2.  **Installation**:
    *   Install Python dependencies: `pip install -r requirements.txt`
    *   Compile and install the C extensions: `python setup.py install` or `pip install .` (This likely requires a C compiler like GCC to be installed).
3.  **Running**:
    *   Scripts can be run directly: `python your_script.py`
    *   The Streamlit app: `streamlit run streamlit_app.py`

## Technical Constraints

*   Requires a C compiler (`gcc`) and Python development headers (`python3-dev` or equivalent) to build the C extensions.
*   Performance of backtesting heavily relies on the compiled C extensions for trade enumeration.
*   Data availability depends on the `yfinance` library and Yahoo Finance API reliability.