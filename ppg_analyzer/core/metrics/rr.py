"""
Respiration Rate (RR) analysis module.

Calculates breathing rate from respiratory-induced amplitude modulation on PPG signal.
"""

import numpy as np
from typing import Dict, Any
from core import filters, peak_detector, artifact_detector
from core.excel_io import SignalData


def analyze_rr(signal_data: SignalData, params_dict: Dict) -> Dict[str, Any]:
    """
    Analyze respiration rate from PPG signal.

    Uses a very low frequency lowpass filter to extract respiratory modulation
    (baseline wander caused by breathing), then finds peaks in this signal.

    Args:
        signal_data: SignalData object
        params_dict: Configuration dict with RR parameters

    Returns:
        Dictionary with keys:
        - rr_breaths_min: float (breaths per minute)
        - peak_indices: np.ndarray
        - peak_intervals_s: np.ndarray
        - filtered_signal: np.ndarray (lowpass filtered)
        - quality: str
        - quality_reason: str
    """
    try:
        # Extract parameters
        lp_cutoff = params_dict.get("rr.lowpass_cutoff", 0.4)  # Hz (very low!)
        lp_order = params_dict.get("rr.lowpass_order", 6)
        peak_min_spacing = params_dict.get("rr.peak_min_spacing", 2.0)  # seconds
        
        fs = signal_data.fs
        ir_signal = signal_data.ir.copy()

        # Apply artifact mask
        artifact_mask = artifact_detector.create_artifact_mask(
            len(ir_signal), signal_data.artifacts
        )
        ir_signal = artifact_detector.apply_artifact_mask(ir_signal, artifact_mask)

        # Step 1: Apply extreme lowpass filter to extract respiratory baseline
        # This kills the heart rate component (1-2 Hz) and keeps only breathing (~0.2-0.3 Hz)
        try:
            b_lp, a_lp = filters.design_iir_lowpass(lp_cutoff, lp_order, fs)
            ir_rr = filters.apply_iir_filter(ir_signal, b_lp, a_lp)
        except Exception as e:
            return {
                "rr_breaths_min": None,
                "peak_indices": np.array([]),
                "peak_intervals_s": np.array([]),
                "filtered_signal": ir_signal,
                "quality": "Poor",
                "quality_reason": f"Bộ lọc thông thấp thất bại: {str(e)}"
            }

        # Step 2: Find peaks in the respiratory signal
        # RR peaks are much further apart than HR peaks (2-6 seconds vs 0.6 seconds)
        min_distance_samples = int(peak_min_spacing * fs)

        try:
            # Find peaks with emphasis on distance constraint
            peak_indices, peak_values = peak_detector.find_peaks_with_prominence(
                ir_rr,
                distance_samples=min_distance_samples,
                height_threshold=0,  # Accept any positive peak
            )
        except Exception as e:
            return {
                "rr_breaths_min": None,
                "peak_indices": np.array([]),
                "peak_intervals_s": np.array([]),
                "filtered_signal": ir_rr,
                "quality": "Poor",
                "quality_reason": f"Phát hiện đỉnh thất bại: {str(e)}"
            }

        # Remove peaks that are too close together (< min_distance)
        if len(peak_indices) > 0:
            intervals = np.diff(peak_indices)
            # Keep only peaks that have proper spacing
            valid_mask = np.concatenate(([True], intervals >= min_distance_samples))
            peak_indices = peak_indices[valid_mask]

        # Remove peaks in artifact regions
        peak_indices = artifact_detector.exclude_artifact_regions_from_peaks(
            peak_indices, artifact_mask
        )

        # Step 3: Calculate RR from peak intervals
        if len(peak_indices) < 2:
            return {
                "rr_breaths_min": None,
                "peak_indices": peak_indices,
                "peak_intervals_s": np.array([]),
                "filtered_signal": ir_rr,
                "quality": "Poor",
                "quality_reason": f"Không đủ đỉnh hô hấp: {len(peak_indices)} < 2"
            }

        peak_times = signal_data.timestamp[peak_indices]
        peak_intervals_s = np.diff(peak_times)
        if not np.all(np.isfinite(peak_intervals_s)):
            return {
                "rr_breaths_min": None,
                "peak_indices": peak_indices,
                "peak_intervals_s": peak_intervals_s,
                "filtered_signal": ir_rr,
                "quality": "Poor",
                "quality_reason": "Khoảng nhịp thở chứa NaN/Inf"
            }

        # Filter intervals to be within physiological range
        # RR range: 8-40 breaths/min → 1.5-7.5 second intervals
        valid_mask = (peak_intervals_s >= 1.5) & (peak_intervals_s <= 7.5)
        valid_intervals = peak_intervals_s[valid_mask]

        if len(valid_intervals) == 0:
            return {
                "rr_breaths_min": None,
                "peak_indices": peak_indices,
                "peak_intervals_s": peak_intervals_s,
                "filtered_signal": ir_rr,
                "quality": "Poor",
                "quality_reason": "Tất cả khoảng thở nằm ngoài dải sinh lý"
            }

        # Calculate mean RR
        # Respiratory rate uses the same period-to-rate conversion as HR:
        # breaths/min = 60 / mean breath interval (seconds).
        mean_interval = np.mean(valid_intervals)
        rr = 60.0 / mean_interval

        # Quality assessment
        if len(peak_indices) < 2:
            quality = "Poor"
            quality_reason = f"Chỉ tìm thấy {len(peak_indices)} đỉnh hô hấp"
        elif rr < 8 or rr > 40:
            quality = "Poor"
            quality_reason = f"RR {rr:.1f} nhịp/phút nằm ngoài dải [8-40]"
        elif len(valid_intervals) < len(peak_intervals_s) * 0.8:
            quality = "Warning"
            quality_reason = f"Một số khoảng hô hấp nằm ngoài dải hợp lệ"
        else:
            quality = "Good"
            quality_reason = f"{len(peak_indices)} đỉnh hô hấp, {rr:.1f} nhịp/phút"

        return {
            "rr_breaths_min": rr,
            "peak_indices": peak_indices,
            "peak_intervals_s": peak_intervals_s,
            "filtered_signal": ir_rr,
            "quality": quality,
            "quality_reason": quality_reason,
            "num_peaks": len(peak_indices),
            "mean_interval_s": mean_interval,
        }

    except Exception as e:
        return {
            "rr_breaths_min": None,
            "peak_indices": np.array([]),
            "peak_intervals_s": np.array([]),
            "filtered_signal": signal_data.ir,
            "quality": "Poor",
            "quality_reason": f"Phân tích RR thất bại: {str(e)}"
        }
