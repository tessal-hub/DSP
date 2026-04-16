"""
Perfusion Index (PI) analysis module.

Calculates perfusion index from IR signal and assesses signal quality.
PI = (AC_IR / DC_IR) × 100%
"""

import numpy as np
from typing import Dict, Any
from core import filters, artifact_detector
from core.excel_io import SignalData


def analyze_pi(signal_data: SignalData, params_dict: Dict) -> Dict[str, Any]:
    """
    Analyze perfusion index from PPG IR signal.

    PI represents the ratio of pulsatile (AC) to non-pulsatile (DC) blood flow.
    Low PI indicates poor signal quality or peripheral vasoconstriction.

    Args:
        signal_data: SignalData object
        params_dict: Configuration dict with PI parameters

    Returns:
        Dictionary with keys:
        - pi_pct: float (perfusion index percentage)
        - ac_ir, dc_ir: float values
        - quality: str ("Good", "Poor", "Warning")
        - quality_reason: str
    """
    try:
        # Extract parameters
        warning_threshold = params_dict.get("pi.warning_threshold", 0.5)  # %
        
        fs = signal_data.fs
        ir_signal = signal_data.ir.copy()

        # Apply artifact mask
        artifact_mask = artifact_detector.create_artifact_mask(
            len(ir_signal), signal_data.artifacts
        )
        ir_signal = artifact_detector.apply_artifact_mask(ir_signal, artifact_mask)

        # Step 1: Extract AC component (high-frequency pulsatile)
        # Use same bandpass as SpO2 for consistency
        bp_low = params_dict.get("spo2.bandpass_low", 0.8)
        bp_high = params_dict.get("spo2.bandpass_high", 4.0)
        bp_order = params_dict.get("spo2.bandpass_order", 4)

        try:
            b_bp, a_bp = filters.design_iir_bandpass(bp_low, bp_high, bp_order, fs)
            ir_bp = filters.apply_iir_filter(ir_signal, b_bp, a_bp)
        except Exception as e:
            return {
                "pi_pct": None,
                "ac_ir": None,
                "dc_ir": None,
                "quality": "Poor",
                "quality_reason": f"Bộ lọc thông dải thất bại: {str(e)}"
            }

        ac_ir = filters.calculate_ac_rms(ir_bp)
        if not np.isfinite(ac_ir):
            return {
                "pi_pct": None,
                "ac_ir": None,
                "dc_ir": None,
                "quality": "Poor",
                "quality_reason": "Thành phần AC không hợp lệ (NaN/Inf)"
            }

        # Step 2: Extract DC component (low-frequency non-pulsatile)
        dc_cutoff = 0.05  # Very low cutoff
        dc_order = 4

        try:
            b_dc, a_dc = filters.design_iir_lowpass(dc_cutoff, dc_order, fs)
            ir_dc_signal = filters.apply_iir_filter(ir_signal, b_dc, a_dc)
        except Exception as e:
            return {
                "pi_pct": None,
                "ac_ir": ac_ir,
                "dc_ir": None,
                "quality": "Poor",
                "quality_reason": f"Trích xuất thành phần DC thất bại: {str(e)}"
            }

        dc_ir = filters.calculate_dc_mean(ir_dc_signal)
        if not np.isfinite(dc_ir):
            return {
                "pi_pct": None,
                "ac_ir": ac_ir,
                "dc_ir": dc_ir,
                "quality": "Poor",
                "quality_reason": "Thành phần DC không hợp lệ (NaN/Inf)"
            }

        # Step 3: Calculate PI
        if dc_ir <= 0 or ac_ir < 0:
            return {
                "pi_pct": None,
                "ac_ir": ac_ir,
                "dc_ir": dc_ir,
                "quality": "Poor",
                "quality_reason": "Giá trị AC/DC không hợp lệ"
            }

        # PI is the pulsatile-to-static blood flow ratio, reported in percent.
        pi_ratio = ac_ir / dc_ir
        pi_pct = pi_ratio * 100.0
        if not np.isfinite(pi_pct):
            return {
                "pi_pct": None,
                "ac_ir": ac_ir,
                "dc_ir": dc_ir,
                "quality": "Poor",
                "quality_reason": "PI tính ra không hợp lệ (NaN/Inf)"
            }

        # Quality assessment
        if pi_pct < warning_threshold:
            quality = "Poor"
            quality_reason = f"PI {pi_pct:.2f}% < ngưỡng {warning_threshold}%. " \
                           f"Tín hiệu yếu — kiểm tra vị trí đặt cảm biến."
        elif pi_pct < warning_threshold * 2:
            quality = "Warning"
            quality_reason = f"PI {pi_pct:.2f}% còn thấp. Có thể ảnh hưởng độ chính xác của chỉ số."
        else:
            quality = "Good"
            quality_reason = f"PI {pi_pct:.2f}% - Chất lượng tín hiệu tốt"

        return {
            "pi_pct": pi_pct,
            "ac_ir": ac_ir,
            "dc_ir": dc_ir,
            "ir_bp_filtered": ir_bp,
            "quality": quality,
            "quality_reason": quality_reason,
        }

    except Exception as e:
        return {
            "pi_pct": None,
            "ac_ir": None,
            "dc_ir": None,
            "quality": "Poor",
            "quality_reason": f"Phân tích PI thất bại: {str(e)}"
        }
