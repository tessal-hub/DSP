"""
Main signal processing orchestrator.

Coordinates the complete analysis pipeline:
  1. Detect motion artifacts
  2. Run all 5 metrics in sequence
  3. Collect and return results
"""

import numpy as np
from typing import Dict, Any
from core.excel_io import SignalData
from core import artifact_detector
from core.metrics import hr, spo2, rr, hrv, pi


class SignalProcessor:
    """
    Main orchestrator for PPG signal analysis.
    
    Runs complete analysis pipeline with all 5 metrics.
    """

    def __init__(self, signal_data: SignalData, params_dict: Dict):
        """
        Initialize processor.

        Args:
            signal_data: SignalData object with timestamps, IR, Red
            params_dict: Configuration dictionary with all parameters
        """
        self.signal_data = signal_data
        self.params_dict = params_dict

    def run_analysis(self) -> Dict[str, Any]:
        """
        Execute complete analysis pipeline.

        Returns:
            Dictionary with results from all 5 metrics:
            {
                "hr": { result dict },
                "spo2": { result dict },
                "rr": { result dict },
                "hrv": { result dict },
                "pi": { result dict },
                "artifacts": { artifact statistics },
                "processing_info": { timing and metadata }
            }
        """
        import time
        start_time = time.time()

        results = {
            "hr": {},
            "spo2": {},
            "rr": {},
            "hrv": {},
            "pi": {},
            "artifacts": {},
        }

        try:
            if self.signal_data.num_samples < 2:
                raise ValueError("Không đủ dữ liệu để phân tích (cần ít nhất 2 mẫu)")
            if not np.isfinite(self.signal_data.fs) or self.signal_data.fs <= 0:
                raise ValueError(f"Tần số lấy mẫu không hợp lệ: {self.signal_data.fs}")

            # Step 1: Detect motion artifacts
            artifact_threshold_sd = self.params_dict.get(
                "validation.artifact_threshold_sd", 3.0
            )
            self.signal_data.artifacts = artifact_detector.detect_motion_artifacts(
                self.signal_data.ir,
                self.signal_data.fs,
                artifact_threshold_sd,
                window_duration_s=2.0,
            )
            
            artifact_stats = artifact_detector.get_artifact_statistics(
                self.signal_data.artifacts, self.signal_data.fs
            )
            results["artifacts"] = artifact_stats

            # Step 2: Run HR analysis (prerequisite for HRV)
            hr_result = hr.analyze_hr(self.signal_data, self.params_dict)
            results["hr"] = hr_result

            # Step 3: Run SpO2 analysis
            spo2_result = spo2.analyze_spo2(self.signal_data, self.params_dict)
            results["spo2"] = spo2_result

            # Step 4: Run RR analysis
            rr_result = rr.analyze_rr(self.signal_data, self.params_dict)
            results["rr"] = rr_result

            # Step 5: Run HRV analysis (uses HR peaks)
            # Pass HR peak indices and times if HR analysis succeeded
            if hr_result.get("peak_indices") is not None and len(hr_result.get("peak_indices", [])) > 0:
                hrv_result = hrv.analyze_hrv(
                    self.signal_data,
                    self.params_dict,
                    hr_peak_indices=hr_result["peak_indices"],
                    hr_peak_times=hr_result.get("peak_times"),
                )
            else:
                hrv_result = {
                    "sdnn_ms": None,
                    "rmssd_ms": None,
                    "stress_level": None,
                    "quality": "Poor",
                    "quality_reason": "Phân tích HR thất bại hoặc không tìm thấy đỉnh",
                    "n_n_intervals_ms": np.array([]),
                }
            results["hrv"] = hrv_result

            # Step 6: Run PI analysis
            pi_result = pi.analyze_pi(self.signal_data, self.params_dict)
            results["pi"] = pi_result

        except Exception as e:
            # Preserve expected keys so UI can still render placeholder subplots/cards.
            results["hr"] = results.get("hr") or {
                "bpm": None,
                "quality": "Poor",
                "quality_reason": "Không thể tính HR",
            }
            results["spo2"] = results.get("spo2") or {
                "spo2_pct": None,
                "quality": "Poor",
                "quality_reason": "Không thể tính SpO2",
            }
            results["rr"] = results.get("rr") or {
                "rr_breaths_min": None,
                "quality": "Poor",
                "quality_reason": "Không thể tính RR",
            }
            results["hrv"] = results.get("hrv") or {
                "sdnn_ms": None,
                "quality": "Poor",
                "quality_reason": "Không thể tính HRV",
            }
            results["pi"] = results.get("pi") or {
                "pi_pct": None,
                "quality": "Poor",
                "quality_reason": "Không thể tính PI",
            }
            results["error"] = str(e)

        # Processing info
        elapsed_time = time.time() - start_time
        results["processing_info"] = {
            "elapsed_time_s": elapsed_time,
            "num_samples": self.signal_data.num_samples,
            "signal_duration_s": self.signal_data.duration,
            "sampling_rate_hz": self.signal_data.fs,
        }

        return results

    @staticmethod
    def get_results_summary(results: Dict) -> Dict[str, Any]:
        """
        Extract summary of key metrics from results.

        Args:
            results: Output from run_analysis()

        Returns:
            Dictionary with simplified summary
        """
        summary = {
            "hr_bpm": results.get("hr", {}).get("bpm"),
            "spo2_pct": results.get("spo2", {}).get("spo2_pct"),
            "rr_breaths_min": results.get("rr", {}).get("rr_breaths_min"),
            "hrv_sdnn_ms": results.get("hrv", {}).get("sdnn_ms"),
            "hrv_rmssd_ms": results.get("hrv", {}).get("rmssd_ms"),
            "hrv_stress": results.get("hrv", {}).get("stress_level"),
            "pi_pct": results.get("pi", {}).get("pi_pct"),
            "artifacts_count": results.get("artifacts", {}).get("num_artifacts", 0),
            "artifacts_duration_s": results.get("artifacts", {}).get("total_duration_s", 0),
        }
        return summary

    @staticmethod
    def get_quality_summary(results: Dict) -> Dict[str, str]:
        """
        Extract quality indicators for all metrics.

        Args:
            results: Output from run_analysis()

        Returns:
            Dictionary mapping metric name to quality string
        """
        quality = {
            "hr": results.get("hr", {}).get("quality", "N/A"),
            "spo2": results.get("spo2", {}).get("quality", "N/A"),
            "rr": results.get("rr", {}).get("quality", "N/A"),
            "hrv": results.get("hrv", {}).get("quality", "N/A"),
            "pi": results.get("pi", {}).get("quality", "N/A"),
        }
        return quality
