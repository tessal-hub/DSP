"""
Peak detection utilities for PPG signal analysis.

Provides wrappers around scipy.signal.find_peaks with parameter configuration.
"""

import numpy as np
from scipy import signal
from typing import Tuple, Dict, Optional


def find_peaks_adaptive(
    signal_data: np.ndarray,
    params_dict: Dict,
    metric: str,
    fs: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Find peaks in signal with parameters from config dictionary.

    Args:
        signal_data: Input signal array
        params_dict: Configuration dict with metric-specific peak parameters
        metric: Metric name ("hr", "rr", or "pi")
        fs: Sampling frequency in Hz

    Returns:
        Tuple of (peak_indices, peak_values)

    Raises:
        KeyError: If required parameters missing from params_dict
        ValueError: If parameters are invalid
    """
    if len(signal_data) == 0:
        return np.array([], dtype=int), np.array([])

    # Get metric-specific parameters
    if metric.lower() == "hr":
        min_distance_s = params_dict.get("hr.peak_min_distance", 0.6)
        min_height_pct = params_dict.get("hr.peak_min_height_pct", 30)
    elif metric.lower() == "rr":
        min_distance_s = params_dict.get("rr.peak_min_spacing", 3.0)
        min_height_pct = 20  # RR peaks: generally lower prominence than HR
    elif metric.lower() == "pi":
        min_distance_s = params_dict.get("hr.peak_min_distance", 0.6)  # Use HR params for IR
        min_height_pct = params_dict.get("hr.peak_min_height_pct", 30)
    else:
        raise ValueError(f"Unknown metric: {metric}")

    # Convert distance from seconds to samples
    distance_samples = int(min_distance_s * fs)
    if distance_samples < 1:
        distance_samples = 1

    # Calculate height threshold (percentage of max amplitude)
    signal_max = np.max(np.abs(signal_data))
    if signal_max == 0:
        return np.array([], dtype=int), np.array([])
    
    height_threshold = (min_height_pct / 100.0) * signal_max

    # Find peaks
    peak_indices, peak_properties = signal.find_peaks(
        signal_data,
        distance=distance_samples,
        height=height_threshold,
    )

    if len(peak_indices) == 0:
        return np.array([], dtype=int), np.array([])

    peak_values = signal_data[peak_indices]

    return peak_indices, peak_values


def find_peaks_with_prominence(
    signal_data: np.ndarray,
    distance_samples: int = None,
    height_threshold: float = None,
    prominence_threshold: float = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Find peaks using prominence criteria (advanced peak detection).

    Args:
        signal_data: Input signal array
        distance_samples: Minimum distance between peaks in samples
        height_threshold: Minimum peak height
        prominence_threshold: Minimum peak prominence

    Returns:
        Tuple of (peak_indices, peak_values)
    """
    if len(signal_data) == 0:
        return np.array([], dtype=int), np.array([])

    kwargs = {}
    if distance_samples is not None:
        kwargs["distance"] = distance_samples
    if height_threshold is not None:
        kwargs["height"] = height_threshold
    if prominence_threshold is not None:
        kwargs["prominence"] = prominence_threshold

    peak_indices, _ = signal.find_peaks(signal_data, **kwargs)

    if len(peak_indices) == 0:
        return np.array([], dtype=int), np.array([])

    peak_values = signal_data[peak_indices]

    return peak_indices, peak_values


def validate_peak_detection_params(
    min_distance_s: float, min_height_pct: float, fs: float
) -> Tuple[bool, str]:
    """
    Validate peak detection parameters.

    Args:
        min_distance_s: Minimum distance between peaks (seconds)
        min_height_pct: Minimum height as percentage of max (0-100)
        fs: Sampling frequency

    Returns:
        Tuple of (is_valid, error_message)
    """
    if min_distance_s <= 0:
        return False, f"Peak min distance must be > 0, got {min_distance_s}"

    if not (0 <= min_height_pct <= 100):
        return False, f"Peak min height must be 0-100%, got {min_height_pct}"

    if fs <= 0:
        return False, f"Sampling frequency must be > 0, got {fs}"

    min_distance_samples = int(min_distance_s * fs)
    if min_distance_samples < 1:
        return False, f"Peak min distance {min_distance_s}s too small for Fs={fs}Hz"

    return True, ""
