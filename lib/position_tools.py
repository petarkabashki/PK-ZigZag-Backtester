import numpy as np

def enumerate_trades_vectorized(entry_mask, exit_mask, skip_first=0):
    """
    Calculates trades (entry and exit indices) in a vectorized manner.

    Args:
        entry_mask (np.ndarray): Boolean array indicating entry signals.
        exit_mask (np.ndarray): Boolean array indicating exit signals.
        skip_first (int): Number of initial elements to skip.

    Returns:
        tuple: A tuple containing two lists: entry indices and exit indices.
    """

    if len(entry_mask) != len(exit_mask):
        raise ValueError("All input arrays must have the same length")

    if skip_first >= len(entry_mask) or skip_first < 0:
        raise ValueError("skip_first must be a non-negative integer less than the length of the arrays")

    # Convert boolean arrays to integer arrays (0 and 1) for cumsum to work correctly.
    entry_mask = entry_mask.astype(int)
    exit_mask = exit_mask.astype(int)
    
    # Use cumsum to track the 'position' state.  entry_mask increases the count,
    # exit_mask *after* an entry decreases it.
    position_changes = np.zeros_like(entry_mask)
    position_changes[skip_first:] = entry_mask[skip_first:] - exit_mask[skip_first:]
    position = np.cumsum(position_changes)

    # Find where the position changes from 0 to 1 (entry) and from 1 to 0 (exit)
    # We pad with a zero at the beginning for diff to work correctly.
    entry_indices = np.where(np.diff(np.concatenate(([0], (position > 0).astype(int)))) == 1)[0]
    exit_indices = np.where(np.diff(np.concatenate(([0], (position > 0).astype(int)))) == -1)[0]


    # Handle the case where the last entry doesn't have a corresponding exit.
    if len(entry_indices) > len(exit_indices):
        exit_indices = np.append(exit_indices, len(entry_mask) - 1)

    return list(entry_indices), list(exit_indices)