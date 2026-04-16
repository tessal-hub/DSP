"""
Heart Rate (HR/BPM) analysis module.

Calculates beats-per-minute from PPG IR signal using peak detection.
"""

import numpy as np
from typing import Dict, Any
from core import filters, peak_detector, artifact_detector
from core.excel_io import SignalData


def analyze_hr(signal_data: SignalData, params_dict: Dict) -> Dict[str, Any]:
    """
    Analyze heart rate from PPG signal.

    Args:
        signal_data: SignalData object with timestamp, IR, red arrays
        params_dict: Configuration dict with HR parameters

    Returns:
        Dictionary with keys:
        - bpm: int
        - peak_indices: np.ndarray of peak sample indices
        - peak_intervals_s: np.ndarray of beat intervals (seconds)
        - filtered_signal: np.ndarray of processed signal
        - quality: str ("Good", "Warning", "Poor")
        - quality_reason: str
    """
    try:
        # Extract parameters
        hp_cutoff = params_dict.get("hr.highpass_cutoff", 0.5)
        hp_order = params_dict.get("hr.highpass_order", 4)
        lp_cutoff = params_dict.get("hr.lowpass_cutoff", 4.5)
        lp_order = params_dict.get("hr.lowpass_order", 4)
        
        fs = signal_data.fs
        ir_signal = signal_data.ir.copy()

        # Step 1: Apply artifact mask
        artifact_mask = artifact_detector.create_artifact_mask(
            len(ir_signal), signal_data.artifacts
        )
        ir_signal = artifact_detector.apply_artifact_mask(ir_signal, artifact_mask)

        # Step 2: Apply IIR highpass filter (remove baseline wander)
        try:
            b_hp, a_hp = filters.design_iir_highpass(hp_cutoff, hp_order, fs)
            ir_hp = filters.apply_iir_filter(ir_signal, b_hp, a_hp)
        except Exception as e:
            return {
                "bpm": None,
                "peak_indices": np.array([]),
                "peak_intervals_s": np.array([]),
                "filtered_signal": ir_signal,
                "quality": "Poor",
                "quality_reason": f"Bộ lọc thông cao thất bại: {str(e)}"
            }

        # Step 3: Apply IIR lowpass filter (remove noise)
        try:
            b_lp, a_lp = filters.design_iir_lowpass(lp_cutoff, lp_order, fs)
            ir_filtered = filters.apply_iir_filter(ir_hp, b_lp, a_lp)
            if not np.all(np.isfinite(ir_filtered)):
                return {
                    "bpm": None,
                    "peak_indices": np.array([]),
                    "peak_intervals_s": np.array([]),
                    "filtered_signal": ir_hp,
                    "quality": "Poor",
                    "quality_reason": "Tín hiệu sau lọc chứa NaN/Inf"
                }
        except Exception as e:
            return {
                "bpm": None,
                "peak_indices": np.array([]),
                "peak_intervals_s": np.array([]),
                "filtered_signal": ir_hp,
                "quality": "Poor",
                "quality_reason": f"Bộ lọc thông thấp thất bại: {str(e)}"
            }

        # Step 4: Find peaks
        try:
            peak_indices, peak_values = peak_detector.find_peaks_adaptive(
                ir_filtered, params_dict, metric="hr", fs=fs
            )
        except Exception as e:
            return {
                "bpm": None,
                "peak_indices": np.array([]),
                "peak_intervals_s": np.array([]),
                "filtered_signal": ir_filtered,
                "quality": "Poor",
                "quality_reason": f"Phát hiện đỉnh thất bại: {str(e)}"
            }

        # Step 5: Remove peaks in artifact regions
        peak_indices = artifact_detector.exclude_artifact_regions_from_peaks(
            peak_indices, artifact_mask
        )

        # Step 6: Calculate BPM from peak intervals
        if len(peak_indices) < 2:
            return {
                "bpm": None,
                "peak_indices": peak_indices,
                "peak_intervals_s": np.array([]),
                "filtered_signal": ir_filtered,
                "quality": "Poor",
                "quality_reason": f"Không đủ đỉnh: {len(peak_indices)} < 2"
            }

        # Peak timestamps
        peak_times = signal_data.timestamp[peak_indices]
        
        # Calculate inter-beat intervals (seconds)
        beat_intervals_s = np.diff(peak_times)
        if not np.all(np.isfinite(beat_intervals_s)):
            return {
                "bpm": None,
                "peak_indices": peak_indices,
                "peak_intervals_s": beat_intervals_s,
                "filtered_signal": ir_filtered,
                "quality": "Poor",
                "quality_reason": "Khoảng nhịp tim chứa NaN/Inf"
            }
        
        # Remove impossibly short or long intervals (outliers)
        # HR range: 40-200 BPM → intervals 0.3-1.5 s
        valid_mask = (beat_intervals_s >= 0.3) & (beat_intervals_s <= 1.5)
        valid_intervals = beat_intervals_s[valid_mask]

        if len(valid_intervals) == 0:
            return {
                "bpm": None,
                "peak_indices": peak_indices,
                "peak_intervals_s": beat_intervals_s,
                "filtered_signal": ir_filtered,
                "quality": "Poor",
                "quality_reason": f"Tất cả khoảng đỉnh nằm ngoài dải sinh lý"
            }

        # Calculate BPM
        # BPM is inverse of average beat period (seconds -> beats per minute).
        mean_interval = np.mean(valid_intervals)
        bpm = 60.0 / mean_interval
        bpm_int = int(np.round(bpm))

        # Quality assessment
        if len(peak_indices) < 3:
            quality = "Poor"
            quality_reason = f"Chỉ tìm thấy {len(peak_indices)} đỉnh"
        elif not (40 <= bpm_int <= 200):
            quality = "Poor"
            quality_reason = f"BPM {bpm_int} nằm ngoài dải sinh lý [40-200]"
        elif len(valid_intervals) < len(beat_intervals_s) * 0.8:
            quality = "Warning"
            quality_reason = f"{100 - (len(valid_intervals)*100//len(beat_intervals_s))}% khoảng R-R nằm ngoài dải hợp lệ (40–180 BPM)"
        else:
            quality = "Good"
            quality_reason = f"{len(peak_indices)} đỉnh, khoảng trung bình {mean_interval:.2f}s"

        return {
            "bpm": bpm_int,
            "bpm_float": bpm,
            "peak_indices": peak_indices,
            "peak_intervals_s": beat_intervals_s,
            "peak_times": peak_times,
            "filtered_signal": ir_filtered,
            "quality": quality,
            "quality_reason": quality_reason,
            "num_peaks": len(peak_indices),
            "mean_interval_s": mean_interval,
        }

    except Exception as e:
        return {
            "bpm": None,
            "peak_indices": np.array([]),
            "peak_intervals_s": np.array([]),
            "filtered_signal": signal_data.ir,
            "quality": "Poor",
            "quality_reason": f"Phân tích HR thất bại: {str(e)}"
        }
