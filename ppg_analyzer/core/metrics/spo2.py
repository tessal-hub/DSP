"""
Blood Oxygen Saturation (SpO2) analysis module.

Calculates SpO2 from PPG Red and IR signals using AC/DC ratio method.
"""

import numpy as np
from typing import Dict, Any
from core import filters, artifact_detector
from core.excel_io import SignalData


def analyze_spo2(signal_data: SignalData, params_dict: Dict) -> Dict[str, Any]:
    """
    Analyze blood oxygen saturation (SpO2) from PPG signal.

    Args:
        signal_data: SignalData object
        params_dict: Configuration dict with SpO2 parameters

    Returns:
        Dictionary with keys:
        - spo2_pct: float (SpO2 percentage)
        - r_ratio: float (AC/DC ratio)
        - ac_red, dc_red, ac_ir, dc_ir: float values
        - quality: str
        - quality_reason: str
    """
    try:
        # Extract parameters
        bp_low = params_dict.get("spo2.bandpass_low", 0.8)
        bp_high = params_dict.get("spo2.bandpass_high", 4.0)
        bp_order = params_dict.get("spo2.bandpass_order", 4)
        r_ratio_min = params_dict.get("spo2.r_ratio_min", 0.4)
        r_ratio_max = params_dict.get("spo2.r_ratio_max", 3.4)
        coeff_a = params_dict.get("spo2.coeff_a", 104.0)
        coeff_b = params_dict.get("spo2.coeff_b", 17.0)
        
        fs = signal_data.fs
        red_signal = signal_data.red.copy()
        ir_signal = signal_data.ir.copy()

        # Apply artifact mask
        artifact_mask = artifact_detector.create_artifact_mask(
            len(ir_signal), signal_data.artifacts
        )
        red_signal = artifact_detector.apply_artifact_mask(red_signal, artifact_mask)
        ir_signal = artifact_detector.apply_artifact_mask(ir_signal, artifact_mask)

        # Step 1: Apply bandpass filter to both channels (to extract AC)
        try:
            b_bp, a_bp = filters.design_iir_bandpass(bp_low, bp_high, bp_order, fs)
            red_bp = filters.apply_iir_filter(red_signal, b_bp, a_bp)
            ir_bp = filters.apply_iir_filter(ir_signal, b_bp, a_bp)
        except Exception as e:
            return {
                "spo2_pct": None,
                "r_ratio": None,
                "quality": "Poor",
                "quality_reason": f"Bộ lọc thông dải thất bại: {str(e)}"
            }

        # Step 2: Extract AC (use RMS of bandpassed signal)
        ac_red = filters.calculate_ac_rms(red_bp)
        ac_ir = filters.calculate_ac_rms(ir_bp)
        if not np.isfinite(ac_red) or not np.isfinite(ac_ir):
            return {
                "spo2_pct": None,
                "r_ratio": None,
                "quality": "Poor",
                "quality_reason": "Thành phần AC không hợp lệ (NaN/Inf)"
            }

        # Step 3: Extract DC (apply very low lowpass to get baseline)
        dc_order = 4
        dc_cutoff = 0.05  # Very low cutoff for DC extraction
        
        try:
            b_dc, a_dc = filters.design_iir_lowpass(dc_cutoff, dc_order, fs)
            red_dc_signal = filters.apply_iir_filter(red_signal, b_dc, a_dc)
            ir_dc_signal = filters.apply_iir_filter(ir_signal, b_dc, a_dc)
        except Exception as e:
            return {
                "spo2_pct": None,
                "r_ratio": None,
                "quality": "Poor",
                "quality_reason": f"Trích xuất thành phần DC thất bại: {str(e)}"
            }

        dc_red = filters.calculate_dc_mean(red_dc_signal)
        dc_ir = filters.calculate_dc_mean(ir_dc_signal)
        if not np.isfinite(dc_red) or not np.isfinite(dc_ir):
            return {
                "spo2_pct": None,
                "r_ratio": None,
                "ac_red": ac_red,
                "dc_red": dc_red,
                "ac_ir": ac_ir,
                "dc_ir": dc_ir,
                "quality": "Poor",
                "quality_reason": "Thành phần DC không hợp lệ (NaN/Inf)"
            }

        # Step 4: Calculate R ratio
        if dc_red <= 0 or dc_ir <= 0 or ac_ir <= 0:
            return {
                "spo2_pct": None,
                "r_ratio": None,
                "ac_red": ac_red,
                "dc_red": dc_red,
                "ac_ir": ac_ir,
                "dc_ir": dc_ir,
                "quality": "Poor",
                "quality_reason": "Giá trị AC/DC không hợp lệ (phải > 0)"
            }

        # Ratio-of-ratios: normalizes pulsatile amplitude (AC) by baseline (DC) per channel,
        # then compares Red against IR to estimate oxygen saturation sensitivity.
        r_ratio = (ac_red / dc_red) / (ac_ir / dc_ir)
        if not np.isfinite(r_ratio):
            return {
                "spo2_pct": None,
                "r_ratio": None,
                "ac_red": ac_red,
                "dc_red": dc_red,
                "ac_ir": ac_ir,
                "dc_ir": dc_ir,
                "quality": "Poor",
                "quality_reason": "Tỉ số R không hợp lệ (NaN/Inf)"
            }

        # Step 5: Validate R ratio
        if r_ratio < r_ratio_min or r_ratio > r_ratio_max:
            return {
                "spo2_pct": None,
                "r_ratio": r_ratio,
                "ac_red": ac_red,
                "dc_red": dc_red,
                "ac_ir": ac_ir,
                "dc_ir": dc_ir,
                "quality": "Poor",
                "quality_reason": f"Tỉ số R {r_ratio:.3f} nằm ngoài dải [{r_ratio_min}, {r_ratio_max}]"
            }

        # Step 6: Calculate SpO2
        # Linear calibration model from sensor/system calibration constants.
        spo2 = coeff_a - coeff_b * r_ratio
        if not np.isfinite(spo2):
            return {
                "spo2_pct": None,
                "r_ratio": r_ratio,
                "ac_red": ac_red,
                "dc_red": dc_red,
                "ac_ir": ac_ir,
                "dc_ir": dc_ir,
                "quality": "Poor",
                "quality_reason": "SpO2 tính ra không hợp lệ (NaN/Inf)"
            }

        # Quality assessment
        if spo2 < 70 or spo2 > 100:
            quality = "Warning"
            quality_reason = f"SpO2 {spo2:.1f}% nằm ngoài dải điển hình [70-100]"
        elif ac_red < 1 or ac_ir < 1:
            quality = "Warning"
            quality_reason = "Biên độ AC của tín hiệu quá thấp"
        else:
            quality = "Good"
            quality_reason = f"Tỉ số R {r_ratio:.3f}, SpO2 {spo2:.1f}%"

        return {
            "spo2_pct": spo2,
            "r_ratio": r_ratio,
            "ac_red": ac_red,
            "dc_red": dc_red,
            "ac_ir": ac_ir,
            "dc_ir": dc_ir,
            "red_bp_filtered": red_bp,
            "ir_bp_filtered": ir_bp,
            "quality": quality,
            "quality_reason": quality_reason,
        }

    except Exception as e:
        return {
            "spo2_pct": None,
            "r_ratio": None,
            "quality": "Poor",
            "quality_reason": f"Phân tích SpO2 thất bại: {str(e)}"
        }
