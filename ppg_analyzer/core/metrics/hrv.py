"""
Heart Rate Variability (HRV) analysis module.

Calculates HRV metrics (SDNN, RMSSD) and stress level classification.
"""

import numpy as np
from typing import Dict, Any, Optional
from core import artifact_detector
from core.excel_io import SignalData


def analyze_hrv(
    signal_data: SignalData,
    params_dict: Dict,
    hr_peak_indices: Optional[np.ndarray] = None,
    hr_peak_times: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Analyze heart rate variability from HR peak positions.

    Calculates SDNN (standard deviation of N-N intervals) and RMSSD (root mean square
    of successive differences). Uses these to classify stress level.

    Args:
        signal_data: SignalData object
        params_dict: Configuration dict with HRV parameters
        hr_peak_indices: Array of peak sample indices from HR analysis
        hr_peak_times: Array of peak timestamps from HR analysis

    Returns:
        Dictionary with keys:
        - sdnn_ms: float (standard deviation of N-N intervals)
        - rmssd_ms: float (RMSSD)
        - stress_level: str ("Relaxed", "Normal", "High Stress")
        - quality: str
        - quality_reason: str
        - n_n_intervals_ms: np.ndarray
    """
    try:
        # Extract parameters
        min_segment_length = params_dict.get("hrv.min_segment_length", 120)  # seconds
        stress_sdnn_low = params_dict.get("hrv.stress_sdnn_low", 20)  # ms
        stress_sdnn_high = params_dict.get("hrv.stress_sdnn_high", 50)  # ms

        # Check if HR peaks provided
        if hr_peak_indices is None or len(hr_peak_indices) < 2:
            return {
                "sdnn_ms": None,
                "rmssd_ms": None,
                "stress_level": None,
                "quality": "Poor",
                "quality_reason": "Không có đỉnh HR hợp lệ để phân tích HRV",
                "n_n_intervals_ms": np.array([])
            }

        # Use provided peak times or calculate from indices
        if hr_peak_times is None:
            peak_times = signal_data.timestamp[hr_peak_indices]
        else:
            peak_times = hr_peak_times

        # Check signal duration
        if signal_data.duration < min_segment_length:
            return {
                "sdnn_ms": None,
                "rmssd_ms": None,
                "stress_level": None,
                "quality": "Poor",
                "quality_reason": f"Tín hiệu quá ngắn: {signal_data.duration:.1f}s < {min_segment_length}s",
                "n_n_intervals_ms": np.array([])
            }

        # Remove peaks in artifact regions
        artifact_mask = artifact_detector.create_artifact_mask(
            len(signal_data.ir), signal_data.artifacts
        )
        valid_peak_indices = artifact_detector.exclude_artifact_regions_from_peaks(
            hr_peak_indices, artifact_mask
        )

        if len(valid_peak_indices) < 2:
            return {
                "sdnn_ms": None,
                "rmssd_ms": None,
                "stress_level": None,
                "quality": "Poor",
                "quality_reason": f"Không đủ đỉnh sau khi loại nhiễu: {len(valid_peak_indices)} < 2",
                "n_n_intervals_ms": np.array([])
            }

        # Get timestamps of valid peaks
        valid_peak_times = signal_data.timestamp[valid_peak_indices]

        # Calculate N-N intervals (inter-beat intervals)
        n_n_intervals_s = np.diff(valid_peak_times)
        n_n_intervals_ms = n_n_intervals_s * 1000  # Convert to milliseconds
        if len(n_n_intervals_ms) < 2:
            return {
                "sdnn_ms": None,
                "rmssd_ms": None,
                "stress_level": None,
                "quality": "Poor",
                "quality_reason": "Không đủ khoảng N-N để tính HRV",
                "n_n_intervals_ms": n_n_intervals_ms
            }
        if not np.all(np.isfinite(n_n_intervals_ms)) or np.any(n_n_intervals_ms <= 0):
            return {
                "sdnn_ms": None,
                "rmssd_ms": None,
                "stress_level": None,
                "quality": "Poor",
                "quality_reason": "Khoảng N-N không hợp lệ (NaN/Inf hoặc <= 0)",
                "n_n_intervals_ms": n_n_intervals_ms
            }

        # Step 1: Calculate SDNN (standard deviation of N-N intervals)
        # SDNN captures overall variability spread across the full NN sequence.
        sdnn_ms = np.std(n_n_intervals_ms)

        # Step 2: Calculate RMSSD (root mean square of successive differences)
        # RMSSD emphasizes short-term beat-to-beat variability (parasympathetic activity).
        n_n_diffs = np.diff(n_n_intervals_ms)
        rmssd_ms = np.sqrt(np.mean(n_n_diffs ** 2))

        # Step 3: Classify stress level based on RMSSD
        # Using RMSSD as primary marker (more sensitive to ANS changes than SDNN)
        if rmssd_ms >= stress_sdnn_high:
            stress_level = "Relaxed"
        elif rmssd_ms >= stress_sdnn_low:
            stress_level = "Normal"
        else:
            stress_level = "High Stress"

        # Quality assessment
        if len(valid_peak_indices) < 3:
            quality = "Poor"
            quality_reason = f"Chỉ có {len(valid_peak_indices)} nhịp tim để tính HRV"
        elif np.any(np.isnan(n_n_intervals_ms)) or np.any(np.isnan([sdnn_ms, rmssd_ms])):
            quality = "Poor"
            quality_reason = "Phát hiện giá trị NaN trong khoảng N-N hoặc chỉ số HRV"
        else:
            quality = "Good"
            quality_reason = f"SDNN={sdnn_ms:.1f}ms, RMSSD={rmssd_ms:.1f}ms → {stress_level}"

        return {
            "sdnn_ms": sdnn_ms,
            "rmssd_ms": rmssd_ms,
            "stress_level": stress_level,
            "quality": quality,
            "quality_reason": quality_reason,
            "n_n_intervals_ms": n_n_intervals_ms,
            "num_beats": len(valid_peak_indices),
            "artifacts_excluded": len(hr_peak_indices) - len(valid_peak_indices),
        }

    except Exception as e:
        return {
            "sdnn_ms": None,
            "rmssd_ms": None,
            "stress_level": None,
            "quality": "Poor",
            "quality_reason": f"Phân tích HRV thất bại: {str(e)}",
            "n_n_intervals_ms": np.array([])
        }
