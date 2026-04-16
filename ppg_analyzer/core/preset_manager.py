"""
Preset management system for PPG Signal Analyzer.

Handles loading, saving, and validating signal processing parameters from JSON presets.
All parameters follow a flat key structure: "metric.param_name": value
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class PresetManager:
    """Manages loading, validating, and saving signal processing parameter presets."""

    def __init__(self, presets_dir: str = None):
        """
        Initialize preset manager.

        Args:
            presets_dir: Path to presets directory. If None, uses ./presets/
        """
        if presets_dir is None:
            presets_dir = self._get_app_data_dir() / "presets"
        else:
            presets_dir = Path(presets_dir)

        self.presets_dir = Path(presets_dir)
        self.default_preset_path = self.presets_dir / "default.json"
        self.last_used_path = self._get_app_data_dir() / "last_used.json"

        # Create presets directory if not exists
        self.presets_dir.mkdir(parents=True, exist_ok=True)
        (self.presets_dir / "user_presets").mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _get_app_data_dir() -> Path:
        """Return a writable per-user data directory."""
        base_dir = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
        if base_dir:
            return Path(base_dir) / "PPG Signal Analyzer"
        return Path.home() / ".ppg_analyzer"

    @staticmethod
    def _get_bundle_root() -> Path:
        """Return the bundle root for frozen apps or the source root otherwise."""
        if getattr(sys, "frozen", False):
            return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        return Path(__file__).resolve().parent.parent

    def _iter_default_preset_candidates(self):
        """Yield default preset paths in priority order."""
        yield self.default_preset_path
        yield self._get_bundle_root() / "presets" / "default.json"
        yield Path(__file__).resolve().parent.parent / "presets" / "default.json"

    def load_preset(self, filepath: str) -> Dict:
        """
        Load parameters from a JSON preset file.

        Args:
            filepath: Path to preset JSON file

        Returns:
            Dictionary of parameters (key: "metric.param", value: number/bool/string)

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Không tìm thấy tệp cấu hình: {filepath}")

        try:
            with open(filepath, "r") as f:
                params = json.load(f)
            return params
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON không hợp lệ trong tệp cấu hình: {e.msg}", e.doc, e.pos)

    def save_preset(self, params: Dict, filepath: str = None) -> str:
        """
        Save parameters to a JSON preset file.

        Args:
            params: Dictionary of parameters (flat structure)
            filepath: Path to save. If None, saves to user_presets/ with timestamp

        Returns:
            Path to saved preset file

        Raises:
            IOError: If file cannot be written
        """
        if filepath is None:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.presets_dir / "user_presets" / f"preset_{timestamp}.json"
        else:
            filepath = Path(filepath)

        filepath.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(filepath, "w") as f:
                json.dump(params, f, indent=2)
            return str(filepath)
        except IOError as e:
            raise IOError(f"Không thể lưu cấu hình vào {filepath}: {e}")

    def load_defaults(self) -> Dict:
        """
        Load default parameters from presets/default.json.

        Returns:
            Dictionary of default parameters

        Raises:
            FileNotFoundError: If default.json doesn't exist
        """
        for preset_path in self._iter_default_preset_candidates():
            if preset_path.exists():
                return self.load_preset(str(preset_path))

        raise FileNotFoundError("Không tìm thấy tệp default.json")

    def auto_load_last_used(self) -> Dict:
        """
        Load last-used preset if it exists, otherwise load defaults.

        Returns:
            Dictionary of parameters
        """
        if self.last_used_path.exists():
            try:
                return self.load_preset(str(self.last_used_path))
            except Exception:
                # Fall back to defaults if last-used is corrupted
                return self.load_defaults()
        else:
            return self.load_defaults()

    def save_last_used(self, params: Dict) -> None:
        """
        Save current parameters as last-used preset.

        Args:
            params: Dictionary of current parameters
        """
        try:
            with open(self.last_used_path, "w") as f:
                json.dump(params, f, indent=2)
        except IOError:
            pass  # Silently fail if we can't save last-used

    def is_param_valid(self, key: str, value) -> Tuple[bool, str]:
        """
        Validate a single parameter value.

        Args:
            key: Parameter key (e.g., "hr.highpass_cutoff")
            value: Parameter value to validate

        Returns:
            Tuple (is_valid: bool, error_message: str or "")
        """
        # Define valid ranges for each parameter
        param_ranges = {
            # HR parameters
            "hr.highpass_cutoff": (0.1, 2.0),
            "hr.highpass_order": (1, 10),
            "hr.lowpass_cutoff": (1.0, 10.0),
            "hr.lowpass_order": (1, 10),
            "hr.peak_min_distance": (0.3, 1.5),
            "hr.peak_min_height_pct": (10, 80),
            # SpO2 parameters
            "spo2.bandpass_low": (0.5, 2.0),
            "spo2.bandpass_high": (2.0, 8.0),
            "spo2.bandpass_order": (1, 10),
            "spo2.r_ratio_min": (0.2, 2.0),
            "spo2.r_ratio_max": (1.5, 5.0),
            "spo2.coeff_a": (100, 120),
            "spo2.coeff_b": (10, 30),
            # RR parameters
            "rr.lowpass_cutoff": (0.1, 0.8),
            "rr.lowpass_order": (1, 12),
            "rr.peak_min_spacing": (2.0, 8.0),
            "rr.peak_max_spacing": (3.0, 12.0),
            # HRV parameters
            "hrv.min_segment_length": (60, 300),
            "hrv.stress_sdnn_low": (10, 50),
            "hrv.stress_sdnn_high": (30, 100),
            # PI parameters
            "pi.warning_threshold": (0.1, 2.0),
            "pi.ac_dc_window": (0.5, 5.0),
            # Validation parameters
            "validation.fs_manual": (25, 2000),
            "validation.min_duration": (30, 300),
            "validation.artifact_threshold_sd": (1, 10),
            "validation.max_display_rows": (100, 5000),
        }

        if key not in param_ranges:
            return True, ""  # Unknown param, assume valid

        try:
            value = float(value)
        except (ValueError, TypeError):
            return False, f"{key}: giá trị phải là số"

        min_val, max_val = param_ranges[key]
        if not (min_val <= value <= max_val):
            return False, f"{key}: giá trị phải nằm trong khoảng {min_val} đến {max_val}"

        return True, ""

    def validate_params(self, params: Dict) -> List[str]:
        """
        Validate all parameters in a preset.

        Args:
            params: Dictionary of parameters

        Returns:
            List of error messages. Empty list if all valid.
        """
        errors = []

        # Validate individual parameters
        for key, value in params.items():
            is_valid, error_msg = self.is_param_valid(key, value)
            if not is_valid:
                errors.append(error_msg)

        # Cross-parameter validation
        try:
            if params.get("hr.highpass_cutoff", 0) >= params.get("hr.lowpass_cutoff", 10):
                errors.append("HR: highpass_cutoff phải nhỏ hơn lowpass_cutoff")

            if params.get("spo2.bandpass_low", 0) >= params.get("spo2.bandpass_high", 10):
                errors.append("SpO2: bandpass_low phải nhỏ hơn bandpass_high")

            if params.get("spo2.r_ratio_min", 0) >= params.get("spo2.r_ratio_max", 10):
                errors.append("SpO2: r_ratio_min phải nhỏ hơn r_ratio_max")

            if params.get("rr.peak_min_spacing", 0) >= params.get("rr.peak_max_spacing", 10):
                errors.append("RR: peak_min_spacing phải nhỏ hơn peak_max_spacing")

            if params.get("hrv.stress_sdnn_low", 0) >= params.get("hrv.stress_sdnn_high", 100):
                errors.append("HRV: stress_sdnn_low phải nhỏ hơn stress_sdnn_high")
        except (KeyError, TypeError):
            pass  # Skip cross-validation if params are incomplete

        return errors

    def get_param_metadata(self) -> Dict:
        """
        Get metadata about all parameters (ranges, units, types).

        Returns:
            Dictionary with parameter metadata
        """
        return {
            # HR
            "hr.highpass_cutoff": {"min": 0.1, "max": 2.0, "unit": "Hz", "type": "float"},
            "hr.highpass_order": {"min": 1, "max": 10, "unit": "", "type": "int"},
            "hr.lowpass_cutoff": {"min": 1.0, "max": 10.0, "unit": "Hz", "type": "float"},
            "hr.lowpass_order": {"min": 1, "max": 10, "unit": "", "type": "int"},
            "hr.peak_min_distance": {"min": 0.3, "max": 1.5, "unit": "s", "type": "float"},
            "hr.peak_min_height_pct": {"min": 10, "max": 80, "unit": "%", "type": "int"},
            # SpO2
            "spo2.bandpass_low": {"min": 0.5, "max": 2.0, "unit": "Hz", "type": "float"},
            "spo2.bandpass_high": {"min": 2.0, "max": 8.0, "unit": "Hz", "type": "float"},
            "spo2.bandpass_order": {"min": 1, "max": 10, "unit": "", "type": "int"},
            "spo2.r_ratio_min": {"min": 0.2, "max": 2.0, "unit": "", "type": "float"},
            "spo2.r_ratio_max": {"min": 1.5, "max": 5.0, "unit": "", "type": "float"},
            "spo2.coeff_a": {"min": 100, "max": 120, "unit": "", "type": "float"},
            "spo2.coeff_b": {"min": 10, "max": 30, "unit": "", "type": "float"},
            # RR
            "rr.lowpass_cutoff": {"min": 0.1, "max": 0.8, "unit": "Hz", "type": "float"},
            "rr.lowpass_order": {"min": 1, "max": 12, "unit": "", "type": "int"},
            "rr.peak_min_spacing": {"min": 2.0, "max": 8.0, "unit": "s", "type": "float"},
            "rr.peak_max_spacing": {"min": 3.0, "max": 12.0, "unit": "s", "type": "float"},
            # HRV
            "hrv.analysis_channel": {"options": ["IR", "Red"], "type": "enum"},
            "hrv.min_segment_length": {"min": 60, "max": 300, "unit": "s", "type": "int"},
            "hrv.stress_sdnn_low": {"min": 10, "max": 50, "unit": "ms", "type": "int"},
            "hrv.stress_sdnn_high": {"min": 30, "max": 100, "unit": "ms", "type": "int"},
            # PI
            "pi.warning_threshold": {"min": 0.1, "max": 2.0, "unit": "%", "type": "float"},
            "pi.ac_dc_window": {"min": 0.5, "max": 5.0, "unit": "s", "type": "float"},
            # Validation
            "validation.auto_detect_fs": {"type": "bool"},
            "validation.fs_manual": {"min": 25, "max": 2000, "unit": "Hz", "type": "float"},
            "validation.min_duration": {"min": 30, "max": 300, "unit": "s", "type": "int"},
            "validation.artifact_threshold_sd": {"min": 1, "max": 10, "unit": "SD", "type": "float"},
            "validation.max_display_rows": {"min": 100, "max": 5000, "unit": "", "type": "int"},
        }
