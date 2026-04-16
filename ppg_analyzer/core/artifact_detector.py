"""
Motion artifact detection for PPG signals.

Detects motion-induced artifacts using rolling standard deviation.
Artifacts are excluded from all metrics (HR, SpO2, RR, HRV, PI).
"""

import numpy as np
from typing import List, Tuple


def detect_motion_artifacts(
    signal_data: np.ndarray,
    fs: float,
    threshold_sd: float,
    window_duration_s: float = 2.0,
) -> List[Tuple[int, int]]:
    """
    Detect motion artifacts using rolling standard deviation.

    Motion artifacts appear as sharp spikes or sudden amplitude changes.
    We detect them by finding regions where the local SD exceeds a threshold.

    Args:
        signal_data: Input signal array
        fs: Sampling frequency in Hz
        threshold_sd: Threshold multiplier (e.g., 3 means 3 * mean_sd)
        window_duration_s: Rolling window duration in seconds (default 2s)

    Returns:
        List of (start_idx, end_idx) tuples marking artifact regions
    """
    if len(signal_data) < int(fs * window_duration_s):
        return []

    window_samples = int(fs * window_duration_s)
    if window_samples < 2:
        window_samples = 2

    # Calculate rolling standard deviation
    rolling_std = _rolling_std(signal_data, window_samples)

    # Calculate mean and std of the rolling std
    mean_std = np.mean(rolling_std)
    std_of_std = np.std(rolling_std)

    # Threshold for artifact detection
    # Dynamic threshold: baseline local variability plus N standard deviations.
    # This adapts to each recording instead of using a fixed absolute threshold.
    artifact_threshold = mean_std + (threshold_sd * std_of_std)

    # Find regions where rolling_std exceeds threshold
    artifact_mask = rolling_std > artifact_threshold

    # Convert boolean mask to (start, end) tuples
    artifact_regions = []
    in_artifact = False
    start_idx = 0

    for i, is_artifact in enumerate(artifact_mask):
        if is_artifact and not in_artifact:
            # Start of artifact region
            start_idx = i
            in_artifact = True
        elif not is_artifact and in_artifact:
            # End of artifact region
            end_idx = i + window_samples
            if end_idx > len(signal_data):
                end_idx = len(signal_data)
            artifact_regions.append((start_idx, end_idx))
            in_artifact = False

    # Handle artifact that extends to end of signal
    if in_artifact:
        end_idx = len(signal_data)
        artifact_regions.append((start_idx, end_idx))

    return artifact_regions


def create_artifact_mask(
    signal_length: int, artifact_regions: List[Tuple[int, int]]
) -> np.ndarray:
    """
    Create binary mask for artifact regions.

    Args:
        signal_length: Length of signal
        artifact_regions: List of (start_idx, end_idx) tuples

    Returns:
        Binary array (1 = artifact, 0 = good data)
    """
    mask = np.zeros(signal_length, dtype=int)
    for start_idx, end_idx in artifact_regions:
        mask[start_idx:end_idx] = 1
    return mask


def apply_artifact_mask(
    signal_data: np.ndarray, artifact_mask: np.ndarray, replacement_value: str = "median"
) -> np.ndarray:
    """
    Replace artifact regions in signal with a replacement value.

    Args:
        signal_data: Input signal
        artifact_mask: Binary mask (1 = artifact)
        replacement_value: 'median', 'mean', 'zero', or a numeric value

    Returns:
        Signal with artifacts replaced
    """
    masked_signal = signal_data.copy()

    if len(artifact_mask) == 0 or np.sum(artifact_mask) == 0:
        return masked_signal

    if replacement_value == "median":
        replacement = np.median(signal_data[artifact_mask == 0])
    elif replacement_value == "mean":
        replacement = np.mean(signal_data[artifact_mask == 0])
    elif replacement_value == "zero":
        replacement = 0
    else:
        try:
            replacement = float(replacement_value)
        except (ValueError, TypeError):
            replacement = np.median(signal_data[artifact_mask == 0])

    masked_signal[artifact_mask == 1] = replacement

    return masked_signal


def get_artifact_statistics(artifact_regions: List[Tuple[int, int]], fs: float) -> dict:
    """
    Calculate statistics about detected artifacts.

    Args:
        artifact_regions: List of (start_idx, end_idx) tuples
        fs: Sampling frequency in Hz

    Returns:
        Dictionary with artifact statistics
    """
    if len(artifact_regions) == 0:
        return {
            "num_artifacts": 0,
            "total_duration_s": 0,
            "total_samples": 0,
            "percentile_signal": 0,
        }

    num_artifacts = len(artifact_regions)
    total_samples = sum(end - start for start, end in artifact_regions)
    total_duration_s = total_samples / fs

    return {
        "num_artifacts": num_artifacts,
        "total_duration_s": total_duration_s,
        "total_samples": total_samples,
        "regions": artifact_regions,
    }


def _rolling_std(signal: np.ndarray, window_size: int) -> np.ndarray:
    """
    Calculate rolling standard deviation.

    Args:
        signal: Input signal
        window_size: Window size in samples

    Returns:
        Array of rolling std values (same length as input)
    """
    if len(signal) < window_size:
        return np.zeros(len(signal))

    rolling_std = np.zeros(len(signal))

    for i in range(len(signal)):
        start = max(0, i - window_size // 2)
        end = min(len(signal), i + window_size // 2)
        rolling_std[i] = np.std(signal[start:end])

    return rolling_std


def exclude_artifact_regions_from_peaks(
    peak_indices: np.ndarray, artifact_mask: np.ndarray
) -> np.ndarray:
    """
    Remove peaks that fall within artifact regions.

    Args:
        peak_indices: Array of peak indices
        artifact_mask: Binary mask (1 = artifact)

    Returns:
        Filtered peak indices (excluding those in artifacts)
    """
    if len(peak_indices) == 0:
        return peak_indices

    valid_peaks = peak_indices[artifact_mask[peak_indices] == 0]

    return valid_peaks


def exclude_artifact_regions_from_signal(
    signal_data: np.ndarray, artifact_regions: List[Tuple[int, int]]
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract only the good (non-artifact) portions of signal.

    Args:
        signal_data: Input signal
        artifact_regions: List of (start_idx, end_idx) artifact regions

    Returns:
        Tuple of (good_signal_samples, good_sample_indices)
    """
    artifact_mask = create_artifact_mask(len(signal_data), artifact_regions)
    good_indices = np.where(artifact_mask == 0)[0]
    good_signal = signal_data[good_indices]

    return good_signal, good_indices
