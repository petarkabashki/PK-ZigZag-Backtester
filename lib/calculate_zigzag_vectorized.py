import numpy as np

def calculate_zigzag_vectorized(highs, lows, epsilon=0.5):
    """
    Calculates the ZigZag indicator fully vectorized (no explicit loops).

    Args:
        highs (np.ndarray): A 1D numpy array of high prices.
        lows (np.ndarray): A 1D numpy array of low prices.
        epsilon (float): The percentage change threshold.

    Returns:
        tuple: (high_low_markers, turning_points)
    """

    length = len(highs)
    if length != len(lows):
        raise ValueError("Highs and lows arrays must have the same length.")

    high_low_markers = np.zeros(length, dtype=int)
    turning_points = np.zeros(length, dtype=int)

    # --- Pre-scan Phase (Vectorized) ---
    candidate_low_indices = np.arange(length)
    candidate_high_indices = np.arange(length)
    candidate_lows = np.minimum.accumulate(lows)
    candidate_highs = np.maximum.accumulate(highs)
    uptrend_condition = (highs / candidate_lows - 1) >= epsilon
    downtrend_condition = (candidate_highs / lows - 1) >= epsilon
    trend_condition = uptrend_condition | downtrend_condition
    first_trend_index = np.argmax(trend_condition)

    if not trend_condition[first_trend_index]:
        return high_low_markers, turning_points

    if uptrend_condition[first_trend_index]:
        direction = 1
        initial_turning_point_index = candidate_low_indices[np.argmin(lows[:first_trend_index + 1])]
        high_low_markers[initial_turning_point_index] = -1
        turning_points[first_trend_index] = 1
        last_extreme_index = initial_turning_point_index
        last_extreme_value = lows[last_extreme_index]
    else:
        direction = -1
        initial_turning_point_index = candidate_high_indices[np.argmax(highs[:first_trend_index + 1])]
        high_low_markers[initial_turning_point_index] = 1
        turning_points[initial_turning_point_index] = -1
        last_extreme_index = initial_turning_point_index
        last_extreme_value = highs[last_extreme_index]

    # --- Main Calculation (Fully Vectorized) ---

    # Create arrays to track trend changes and extreme values
    trend_changes = np.zeros(length, dtype=int)
    extreme_indices = np.full(length, -1, dtype=int)
    extreme_values = np.full(length, np.nan)

    # Initialize based on pre-scan
    trend_changes[first_trend_index] = direction
    extreme_indices[first_trend_index] = last_extreme_index
    extreme_values[first_trend_index] = last_extreme_value

    # Calculate rolling highs and lows, starting from the first trend index
    rolling_highs = np.maximum.accumulate(np.where(np.arange(length) >= first_trend_index, highs, -np.inf))
    rolling_lows = np.minimum.accumulate(np.where(np.arange(length) >= first_trend_index, lows, np.inf))

    # Uptrend and Downtrend conditions AFTER the first trend index.  Crucially,
    # we use the rolling highs/lows and compare against the *previous* extreme value.
    uptrend_reversal = (rolling_highs[first_trend_index:] / extreme_values[first_trend_index] - 1) >= epsilon
    downtrend_reversal = (extreme_values[first_trend_index] / rolling_lows[first_trend_index:] - 1) >= epsilon
    
    # Iterate through possible directions: 1 (uptrend) and -1 (downtrend)
    for current_direction in [1, -1]:
        # Select indices where the current direction applies, starting from first_trend_index
        indices = np.arange(first_trend_index, length)
        
        if current_direction == 1: # Uptrend
            relevant_reversal = downtrend_reversal # We check downtrend_reversal during uptrend
        else: # Downtrend
            relevant_reversal = uptrend_reversal  # We check uptrend_reversal during downtrend
            
        # Apply the reversal check only when direction has the expected value.
        cumulative_direction = np.cumsum(trend_changes)
        direction_mask = (cumulative_direction[first_trend_index:] == current_direction)  # Corrected mask
        reversal_mask = relevant_reversal & direction_mask
        
        reversal_indices = indices[reversal_mask]

        # Update trend_changes, extreme_indices, and extreme_values.
        trend_changes[reversal_indices] = -current_direction

        # Correctly update extreme indices:
        if current_direction == 1: # Uptrend
            new_extreme_indices = np.where(reversal_mask)[0] + first_trend_index  # Adjust indices
            extreme_indices[new_extreme_indices] = new_extreme_indices
            extreme_values[new_extreme_indices] = highs[new_extreme_indices]

        else:  #Downtrend
            new_extreme_indices = np.where(reversal_mask)[0] + first_trend_index  # Adjust indices
            extreme_indices[new_extreme_indices] = new_extreme_indices
            extreme_values[new_extreme_indices] = lows[new_extreme_indices]

    # Recompute cumulative direction to use the correctly filled trend_changes.
    cumulative_direction = np.cumsum(trend_changes)
    
    # Update extreme indices based on rolling highs/lows *after* reversal points
    for current_direction in [1,-1]:
        dir_mask = (cumulative_direction == current_direction) & (np.arange(length) > first_trend_index)

        if current_direction == 1: # Uptrend
            updated_extreme_indices = np.where(highs == rolling_highs, np.arange(length), -1)
        else: # Downtrend:
            updated_extreme_indices = np.where(lows == rolling_lows, np.arange(length), -1)

        extreme_indices = np.maximum(extreme_indices, updated_extreme_indices) # Takes the highest index
        
    # Fill extreme_values using the updated extreme_indices.
    valid_indices = extreme_indices != -1
    extreme_values[valid_indices] = np.where(cumulative_direction[valid_indices] == 1, highs[extreme_indices[valid_indices]], lows[extreme_indices[valid_indices]])


    # Build the final output arrays
    high_low_markers = np.where(cumulative_direction == 1, 1, -1)
    high_low_markers[~valid_indices] = 0  # Set non-extreme points to 0

    turning_points = np.diff(cumulative_direction, prepend=0) # prepend the initial 0
    # print(extreme_indices)
    return high_low_markers, turning_points