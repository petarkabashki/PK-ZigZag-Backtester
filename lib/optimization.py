#%%
# Optimization Functions (Optuna)
# -----------------------------------------------------------------------------------------
import optuna
import pandas as pd
import numpy as np
import os
from strategies.zigzag_fib.signals import generate_signals # <-- Corrected import
from .backtesting import run_backtest
from .plotting import plot_backtest_results

# Global variable to hold data (consider passing explicitly if preferred)
data_global = None
MAX_DRAWDOWN_CONSTRAINT = 0.60 # Default, can be overridden

def set_optimization_data(data):
    """Sets the global data used by the objective function."""
    global data_global
    data_global = data

def set_max_drawdown_constraint(constraint):
    """Sets the maximum drawdown constraint for the objective function."""
    global MAX_DRAWDOWN_CONSTRAINT
    MAX_DRAWDOWN_CONSTRAINT = constraint

def objective(trial):
    """Optuna objective function for multi-objective optimization with drawdown constraint."""
    global data_global, MAX_DRAWDOWN_CONSTRAINT
    # Define parameter search space
    zigzag_epsilon = trial.suggest_float('zigzag_epsilon', 0.01, 0.15, step=0.005)
    entry_fib = trial.suggest_categorical('entry_fib', [0.382, 0.5, 0.618, 0.786])
    stop_entry_fib = trial.suggest_categorical('stop_entry_fib', [0.618, 0.786, 1.0])
    wick_lookback = trial.suggest_int('wick_lookback', 2, 10)
    fractal_n = trial.suggest_int('fractal_n', 2, 5) # For Fractal Exit

    # Ensure stop_entry_fib is greater than entry_fib
    if stop_entry_fib <= entry_fib:
        # print(f"Trial {trial.number}: Pruning due to stop_entry_fib <= entry_fib ({stop_entry_fib} <= {entry_fib})")
        raise optuna.TrialPruned("stop_entry_fib must be greater than entry_fib")

    # Corrected params dictionary for generate_signals
    params = {
        'zigzag_epsilon': zigzag_epsilon,
        'entry_fib': entry_fib,
        'stop_entry_fib': stop_entry_fib,
        'wick_lookback': wick_lookback,
        'fractal_n': fractal_n,
        'exit_type': 'fractal', # Use exit_type='fractal'
        # 'take_profit_fib', 'stop_loss_fib', 'trade_direction' use defaults
    }

    # Generate signals and run backtest
    if data_global is None:
        print("WARN: Global data not available for optimization trial.")
        return -5.0, 1.0 # Return poor values if data is missing

    signals_df = generate_signals(data_global, **params)
    if signals_df is None:
        # print(f"Trial {trial.number}: Pruning due to signal generation failure.")
        return -5.0, 1.0 # Return poor values if signal generation fails

    # Ensure correct casing for run_backtest input
    backtest_input_df = signals_df.rename(columns={
        'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close'
    }, errors='ignore')

    _, strategy_results, _, _ = run_backtest(backtest_input_df, min_trades_for_stats=10) # Require more trades for optimization stability

    sharpe = strategy_results.get('sharpe_ratio', -5.0)
    max_dd = strategy_results.get('max_drawdown', 1.0)

    # Apply Drawdown Constraint
    if max_dd > MAX_DRAWDOWN_CONSTRAINT:
        # Penalize trials exceeding the drawdown limit by significantly reducing Sharpe
        # The penalty should make it less desirable than valid trials
        # print(f"Trial {trial.number}: Penalizing. Drawdown {max_dd:.4f} > {MAX_DRAWDOWN_CONSTRAINT:.4f}. Original Sharpe: {sharpe:.4f}")
        sharpe = -10.0 - (max_dd - MAX_DRAWDOWN_CONSTRAINT) # Make Sharpe highly negative based on constraint violation
        # We still return the actual drawdown for multi-objective consideration, but the Sharpe penalty guides selection away from these.

    # Optuna aims to minimize objectives by default.
    # For Sharpe (maximize), return its negative.
    # For Max Drawdown (minimize), return its positive value.
    return -sharpe, max_dd # Return negative Sharpe and positive Drawdown


def run_optimization(n_trials, timeout, study_name, storage_name):
    """Creates or loads an Optuna study and runs the optimization."""
    study = optuna.create_study(
        study_name=study_name,
        storage=storage_name,
        directions=['minimize', 'minimize'], # Minimize (-Sharpe) and Minimize (Drawdown)
        load_if_exists=True # Load previous results if they exist
    )

    # Check if the study already has enough trials
    completed_trials = len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])
    remaining_trials = n_trials - completed_trials

    if remaining_trials > 0:
        print(f"Study '{study_name}' found. Completed trials: {completed_trials}. Running {remaining_trials} more trials.")
        try:
            study.optimize(objective, n_trials=remaining_trials, timeout=timeout)
            print("Optimization finished.")
        except Exception as e:
            print(f"An error occurred during optimization: {e}")
    else:
        print(f"Study '{study_name}' already has {completed_trials} completed trials (target: {n_trials}). Skipping optimization.")

    return study


def analyze_optimization_results(study, strategy_res_default, bh_res_default, base, quote, timeframe, output_dir, study_name):
    """Analyzes Optuna results, runs final backtest, plots, and saves comparison."""
    global data_global, MAX_DRAWDOWN_CONSTRAINT
    if not study.trials:
        print("\nNo trials were run in the study. Cannot analyze results.")
        return

    # Filter out pruned trials and trials that failed constraint (for selecting 'best')
    valid_trials = [
        t for t in study.trials
        if t.state == optuna.trial.TrialState.COMPLETE and t.values[1] <= MAX_DRAWDOWN_CONSTRAINT # Check actual drawdown value
    ]

    if valid_trials:
        # Select the best trial based on MAXIMIZING Sharpe (minimizing negative Sharpe) among valid trials
        best_trial = min(valid_trials, key=lambda t: t.values[0]) # Min negative Sharpe -> Max Sharpe
        best_params = best_trial.params
        best_sharpe = -best_trial.values[0] # Convert back to positive Sharpe
        best_drawdown = best_trial.values[1]

        print(f"\n--- Best Trial Found (Trial {best_trial.number}) ---")
        print(f"  Sharpe Ratio: {best_sharpe:.4f}")
        print(f"  Max Drawdown: {best_drawdown:.4f}")
        print("  Best Parameters:")
        for key, value in best_params.items(): print(f"    {key}: {value}")

        # --- Run Final Backtest with Best Parameters ---
        print("\n--- Running Final Backtest with Optimized Parameters ---")
        final_params = best_params.copy()
        final_params['exit_type'] = 'fractal' # Ensure fractal exit is used, correct key

        signals_df_final = generate_signals(data_global, **final_params)
        if signals_df_final is not None:
            # Ensure correct casing for run_backtest input
            backtest_input_df_final = signals_df_final.rename(columns={
                'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close'
            }, errors='ignore')
            results_df_final, strategy_res_final, bh_res_final, trades_df_final = run_backtest(backtest_input_df_final, debug_log=False) # Keep debug off, capture trades

            if results_df_final is not None:
                print("\nOptimized Strategy Results:")
                for key, value in strategy_res_final.items(): print(f"  {key}: {value:.4f}")

                # Plot final results
                plot_filename_final = os.path.join(output_dir, f"final_backtest_results_{study_name}.png")
                plot_backtest_results(results_df_final, strategy_res_final, bh_res_final,
                                      title_suffix=f"Optimized Params (Trial {best_trial.number}, {base}{quote} {timeframe})",
                                      filename=plot_filename_final)

                # --- Create Comparison Table ---
                comparison_data = {
                    'Metric': ['Total Return', 'Sharpe Ratio', 'Sortino Ratio', 'Max Drawdown', 'Total Trades'],
                    'Default Strategy': [
                        strategy_res_default.get('total_return', np.nan),
                        strategy_res_default.get('sharpe_ratio', np.nan),
                        strategy_res_default.get('sortino_ratio', np.nan),
                        strategy_res_default.get('max_drawdown', np.nan),
                        strategy_res_default.get('total_trades', np.nan)
                    ],
                    'Optimized Strategy': [
                        strategy_res_final.get('total_return', np.nan),
                        strategy_res_final.get('sharpe_ratio', np.nan),
                        strategy_res_final.get('sortino_ratio', np.nan),
                        strategy_res_final.get('max_drawdown', np.nan), # This will now show uncapped value
                        strategy_res_final.get('total_trades', np.nan)
                    ],
                    'Buy & Hold': [
                        bh_res_final.get('bh_total_return', np.nan),
                        bh_res_final.get('bh_sharpe_ratio', np.nan),
                        bh_res_final.get('bh_sortino_ratio', np.nan),
                        bh_res_final.get('bh_max_drawdown', np.nan), # This will now show uncapped value
                        '-'
                    ]
                }
                comparison_df = pd.DataFrame(comparison_data)
                print("\n--- Comparison Table ---")
                # Removed float_format argument from the line below
                print(comparison_df.to_string(index=False))

                # Save comparison table
                comparison_filename = os.path.join(output_dir, f"comparison_table_{study_name}.csv")
                try:
                    comparison_df.to_csv(comparison_filename, index=False, float_format="%.6f") # Keep float format for CSV saving
                    print(f"\nComparison table saved to {comparison_filename}")
                except Exception as e:
                    print(f"Error saving comparison table: {e}")

            else:
                print("Final backtest failed to produce results.")
        else:
            print("Failed to generate signals with optimized parameters.")

        # --- Plot Optimization History and Pareto Front ---
        try:
            # Pareto Front
            fig_pareto = optuna.visualization.plot_pareto_front(study, target_names=["-Sharpe Ratio", "Max Drawdown"])
            pareto_filename = os.path.join(output_dir, f"optuna_pareto_front_{study_name}.png")
            fig_pareto.write_image(pareto_filename)
            print(f"Pareto front plot saved to {pareto_filename}")

            # Parameter Importances (using mean decrease impurity - requires scikit-learn)
            try:
                fig_importance = optuna.visualization.plot_param_importances(study, target=lambda t: t.values[0], target_name="-Sharpe Ratio") # Importance for Sharpe
                importance_filename = os.path.join(output_dir, f"optuna_param_importance_{study_name}.png")
                fig_importance.write_image(importance_filename)
                print(f"Parameter importance plot saved to {importance_filename}")
            except ImportError:
                print("WARN: scikit-learn not installed. Skipping parameter importance plot.")
            except Exception as e_imp:
                 print(f"WARN: Could not generate parameter importance plot: {e_imp}")


        except (ImportError, ValueError) as e_vis:
            print(f"WARN: Could not generate Optuna plots. Ensure 'plotly' and potentially 'scikit-learn' are installed. Error: {e_vis}")
        except Exception as e_plot:
            print(f"An unexpected error occurred during Optuna plot generation: {e_plot}")

    else:
        print("\nNo valid trials found after optimization (all pruned or failed constraint). Cannot determine best parameters or run final backtest.")
        # Still try to plot Pareto front if there are completed trials
        if any(t.state == optuna.trial.TrialState.COMPLETE for t in study.trials):
             try:
                fig_pareto = optuna.visualization.plot_pareto_front(study, target_names=["-Sharpe Ratio", "Max Drawdown"])
                pareto_filename = os.path.join(output_dir, f"optuna_pareto_front_{study_name}.png")
                fig_pareto.write_image(pareto_filename)
                print(f"Pareto front plot saved to {pareto_filename} (may include constraint-violating trials)")
             except Exception as e_pareto_fail:
                 print(f"Could not generate Pareto front plot for failed study: {e_pareto_fail}")