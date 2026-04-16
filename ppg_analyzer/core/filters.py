"""
Signal filtering toolkit for PPG analysis.

Provides IIR (Butterworth) and FIR filter designs and application.
All parameters are passed from external configuration - no hardcoding.
"""

import numpy as np
from scipy import signal
from typing import Tuple, Dict, Any


def design_iir_highpass(cutoff_hz: float, order: int, fs: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Design Butterworth IIR highpass filter.

    Args:
        cutoff_hz: Cutoff frequency in Hz
        order: Filter order (1-10)
        fs: Sampling frequency in Hz

    Returns:
        Tuple of (b, a) filter coefficients for scipy.signal.filtfilt()

    Raises:
        ValueError: If parameters are invalid
    """
    if cutoff_hz <= 0 or cutoff_hz >= fs / 2:
        raise ValueError(
            f"Highpass cutoff ({cutoff_hz} Hz) must be > 0 and < Nyquist ({fs/2} Hz)"
        )
    if order < 1 or order > 10:
        raise ValueError(f"Filter order must be 1-10, got {order}")

    # Normalize frequency (0 to 1, where 1 is Nyquist frequency)
    normalized_cutoff = cutoff_hz / (fs / 2)
    
    b, a = signal.butter(order, normalized_cutoff, btype="high", analog=False)
    return b, a


def design_iir_lowpass(cutoff_hz: float, order: int, fs: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Design Butterworth IIR lowpass filter.

    Args:
        cutoff_hz: Cutoff frequency in Hz
        order: Filter order (1-10)
        fs: Sampling frequency in Hz

    Returns:
        Tuple of (b, a) filter coefficients

    Raises:
        ValueError: If parameters are invalid
    """
    if cutoff_hz <= 0 or cutoff_hz >= fs / 2:
        raise ValueError(
            f"Lowpass cutoff ({cutoff_hz} Hz) must be > 0 and < Nyquist ({fs/2} Hz)"
        )
    if order < 1 or order > 10:
        raise ValueError(f"Filter order must be 1-10, got {order}")

    normalized_cutoff = cutoff_hz / (fs / 2)
    b, a = signal.butter(order, normalized_cutoff, btype="low", analog=False)
    return b, a


def design_iir_bandpass(
    low_hz: float, high_hz: float, order: int, fs: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Design Butterworth IIR bandpass filter.

    Args:
        low_hz: Low cutoff frequency in Hz
        high_hz: High cutoff frequency in Hz
        order: Filter order (1-10)
        fs: Sampling frequency in Hz

    Returns:
        Tuple of (b, a) filter coefficients

    Raises:
        ValueError: If parameters are invalid
    """
    if low_hz <= 0 or high_hz >= fs / 2 or low_hz >= high_hz:
        raise ValueError(
            f"Bandpass cutoffs ({low_hz}, {high_hz}) invalid: "
            f"0 < low < high < Nyquist ({fs/2})"
        )
    if order < 1 or order > 10:
        raise ValueError(f"Filter order must be 1-10, got {order}")

    normalized_low = low_hz / (fs / 2)
    normalized_high = high_hz / (fs / 2)
    
    b, a = signal.butter(order, [normalized_low, normalized_high], btype="band", analog=False)
    return b, a


def apply_iir_filter(signal_data: np.ndarray, b: np.ndarray, a: np.ndarray) -> np.ndarray:
    """
    Apply IIR filter using zero-phase filtfilt (forward-backward).

    Args:
        signal_data: Input signal array
        b: Numerator coefficients
        a: Denominator coefficients

    Returns:
        Filtered signal (same shape as input)
    """
    input_len = len(signal_data)
    if input_len == 0:
        return np.asarray(signal_data, dtype=float)

    min_len_for_filtfilt = 3 * max(len(b), len(a))
    if input_len < min_len_for_filtfilt:
        # Preserve shape for short signals by padding, filtering, then trimming exactly
        # back to the original sample count.
        pad_len = max(1, min_len_for_filtfilt - input_len)
        padded = np.pad(signal_data, pad_width=pad_len, mode="edge")
        filtered = signal.filtfilt(b, a, padded)
        return filtered[pad_len : pad_len + input_len]

    return signal.filtfilt(b, a, signal_data)


def design_fir_lowpass(cutoff_hz: float, order: int, fs: float) -> np.ndarray:
    """
    Design FIR lowpass filter using Hamming window.

    Args:
        cutoff_hz: Cutoff frequency in Hz
        order: Filter order (number of taps, typically 50-200 for PPG)
        fs: Sampling frequency in Hz

    Returns:
        FIR filter coefficients (taps)

    Raises:
        ValueError: If parameters are invalid
    """
    if cutoff_hz <= 0 or cutoff_hz >= fs / 2:
        raise ValueError(
            f"Lowpass cutoff ({cutoff_hz} Hz) must be > 0 and < Nyquist ({fs/2} Hz)"
        )
    if order < 3 or order > 500:
        raise ValueError(f"FIR order must be 3-500, got {order}")

    normalized_cutoff = cutoff_hz / (fs / 2)
    h = signal.firwin(order, normalized_cutoff, window="hamming")
    return h


def apply_fir_filter(signal_data: np.ndarray, h: np.ndarray) -> np.ndarray:
    """
    Apply FIR filter (one-pass convolution).

    Args:
        signal_data: Input signal array
        h: FIR filter coefficients (taps)

    Returns:
        Filtered signal (same length as input, with delay compensation)
    """
    # Use 'same' mode to keep output same length as input
    filtered = signal.lfilter(h, 1, signal_data)
    
    # Estimate group delay and circularly shift to compensate
    group_delay = (len(h) - 1) // 2
    filtered = np.roll(filtered, -group_delay)
    
    return filtered


def extract_ac_dc(
    signal_data: np.ndarray, lp_cutoff_hz: float, order: int, fs: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract AC (high-frequency) and DC (low-frequency) components.

    AC component: signal - lowpass(signal)
    DC component: lowpass(signal)

    Args:
        signal_data: Input signal
        lp_cutoff_hz: Lowpass cutoff frequency for DC extraction
        order: Lowpass filter order
        fs: Sampling frequency in Hz

    Returns:
        Tuple of (AC_signal, DC_signal)
    """
    b, a = design_iir_lowpass(lp_cutoff_hz, order, fs)
    dc_component = apply_iir_filter(signal_data, b, a)
    ac_component = signal_data - dc_component
    
    return ac_component, dc_component


def calculate_ac_rms(ac_signal: np.ndarray) -> float:
    """
    Calculate RMS (root mean square) of AC signal component.

    Args:
        ac_signal: AC component signal

    Returns:
        RMS value (float)
    """
    return np.sqrt(np.mean(ac_signal ** 2))


def calculate_ac_peak_to_peak(ac_signal: np.ndarray) -> float:
    """
    Calculate peak-to-peak value of AC signal component.

    Args:
        ac_signal: AC component signal

    Returns:
        Peak-to-peak value (float)
    """
    return np.ptp(ac_signal)


def calculate_dc_mean(dc_signal: np.ndarray) -> float:
    """
    Calculate mean value of DC signal component.

    Args:
        dc_signal: DC component signal

    Returns:
        Mean value (float)
    """
    return np.mean(dc_signal)
