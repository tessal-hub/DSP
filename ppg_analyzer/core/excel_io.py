"""
Excel file I/O and signal data validation for PPG analysis.

Loads 3-column Excel files (Timestamp, IR, Red) with automatic validation
and sampling frequency detection.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, Dict


class InvalidExcelError(Exception):
    """Exception raised for invalid Excel file format."""
    pass


class InputValidationWarning(Warning):
    """Warning for non-critical input validation issues."""
    pass


class SignalLoader:
    """
    Loads and validates PPG signal data from Excel files.
    
    Expected format: 3 columns (Timestamp, IR, Red)
    Column names are case-insensitive and flexible:
    - Timestamp: 'timestamp', 'time', 'time_s', 'seconds'
    - IR channel: 'ir', 'infrared'
    - Red channel: 'red', 'red_channel'
    """

    # Acceptable column name variations
    TIMESTAMP_NAMES = {"timestamp", "time", "time_s", "seconds", "sec"}
    IR_NAMES = {"ir", "infrared", "ir_channel"}
    RED_NAMES = {"red", "red_channel", "red_led"}

    @staticmethod
    def _parse_datetime_value(value, row_idx: int) -> datetime:
        """
        Parse a datetime-like timestamp value.

        Args:
            value: String or datetime-like value
            row_idx: Zero-based row index for error messages

        Returns:
            datetime instance

        Raises:
            InvalidExcelError: If the value cannot be parsed
        """
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            text = value.strip()
            for fmt in ("%H:%M:%S.%f", "%H:%M:%S"):
                try:
                    return datetime.strptime(text, fmt)
                except ValueError:
                    continue

            raise InvalidExcelError(
                f"Mốc thời gian không hợp lệ ở dòng {row_idx + 1}: {value!r}. "
                f"Dự kiến là số giây, 'HH:MM:SS.mmm', 'HH:MM:SS' hoặc giá trị datetime/Timestamp."
            )

        raise InvalidExcelError(
            f"Mốc thời gian không hợp lệ ở dòng {row_idx + 1}: {value!r}. "
            f"Dự kiến là số giây, 'HH:MM:SS.mmm', 'HH:MM:SS' hoặc giá trị datetime/Timestamp."
        )

    @staticmethod
    def parse_timestamps(raw_timestamps) -> np.ndarray:
        """
        Normalize timestamp column to seconds.

        Rules:
        1. Numeric timestamps are used directly as seconds.
        2. String timestamps in HH:MM:SS.mmm or HH:MM:SS are parsed and
           converted to relative seconds.
        3. pandas Timestamp / datetime values are handled the same way.
        4. Any unsupported value raises a clear InvalidExcelError.

        Args:
            raw_timestamps: Iterable of timestamp values

        Returns:
            NumPy array of timestamps in seconds
        """
        values = list(raw_timestamps)
        if len(values) == 0:
            raise InvalidExcelError("Cột thời gian đang trống")

        non_null_values = [(idx, value) for idx, value in enumerate(values) if not pd.isna(value)]
        if len(non_null_values) == 0:
            raise InvalidExcelError("Cột thời gian chỉ chứa giá trị rỗng")

        first_idx, first_value = non_null_values[0]

        if isinstance(first_value, (int, float, np.integer, np.floating)) and not isinstance(first_value, bool):
            try:
                return np.asarray([float(value) for value in values], dtype=float)
            except (TypeError, ValueError) as e:
                raise InvalidExcelError(
                    f"Mốc thời gian dạng số không hợp lệ ở dòng {first_idx + 1}: {first_value!r}. "
                    f"Dữ liệu thời gian phải là số giây hoặc chuỗi thời gian/datetime hợp lệ."
                ) from e

        parsed_seconds = []
        base_datetime = None

        for row_idx, value in enumerate(values):
            if pd.isna(value):
                raise InvalidExcelError(f"Mốc thời gian ở dòng {row_idx + 1} bị trống")

            current_datetime = SignalLoader._parse_datetime_value(value, row_idx)
            if base_datetime is None:
                base_datetime = current_datetime

            parsed_seconds.append((current_datetime - base_datetime).total_seconds())

        return np.asarray(parsed_seconds, dtype=float)

    @staticmethod
    def find_column(df: pd.DataFrame, acceptable_names: set) -> Optional[str]:
        """
        Find a column by flexible name matching (case-insensitive).

        Args:
            df: DataFrame
            acceptable_names: Set of acceptable column name variations

        Returns:
            Column name if found, None otherwise
        """
        df_cols_lower = {col: col for col in df.columns}  # Map lowercase to original
        
        for col in df.columns:
            if col.lower() in acceptable_names:
                return col
        
        return None

    @staticmethod
    def load_excel(filepath: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
        """
        Load PPG signal from Excel file.

        Args:
            filepath: Path to .xlsx file

        Returns:
            Tuple of (timestamps_s, ir_array, red_array, detected_fs, duration_s)

        Raises:
            InvalidExcelError: If file format is invalid
            FileNotFoundError: If file doesn't exist
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Không tìm thấy tệp: {filepath}")

        try:
            # Read Excel file - try all sheets until one works
            xls = pd.ExcelFile(filepath)
            df = None
            
            for sheet_name in xls.sheet_names:
                try:
                    df = pd.read_excel(filepath, sheet_name=sheet_name)
                    if len(df) > 0:
                        break
                except Exception:
                    continue
            
            if df is None or len(df) == 0:
                raise InvalidExcelError("Tệp Excel không có dữ liệu")

        except Exception as e:
            if isinstance(e, InvalidExcelError):
                raise
            raise InvalidExcelError(f"Không thể đọc tệp Excel: {str(e)}")

        # Find required columns
        timestamp_col = SignalLoader.find_column(df, SignalLoader.TIMESTAMP_NAMES)
        ir_col = SignalLoader.find_column(df, SignalLoader.IR_NAMES)
        red_col = SignalLoader.find_column(df, SignalLoader.RED_NAMES)

        # Check if all 3 columns found
        missing_cols = []
        if timestamp_col is None:
            missing_cols.append("Mốc thời gian (dự kiến: 'timestamp', 'time', 'time_s')")
        if ir_col is None:
            missing_cols.append("Kênh IR (dự kiến: 'ir', 'infrared')")
        if red_col is None:
            missing_cols.append("Kênh Red (dự kiến: 'red', 'red_channel')")

        if missing_cols:
            available = ", ".join(df.columns)
            raise InvalidExcelError(
                f"Thiếu các cột bắt buộc:\n"
                f"  - {chr(10).join('  - ' + col for col in missing_cols)}\n"
                f"Các cột hiện có: {available}"
            )

        try:
            # Extract data
            timestamps = SignalLoader.parse_timestamps(df[timestamp_col].tolist())
            # Normalize to start at 0.0s so plotting never begins with negative offsets.
            timestamps = timestamps - timestamps[0]
            ir_signal = df[ir_col].astype(float).values
            red_signal = df[red_col].astype(float).values
        except (ValueError, TypeError) as e:
            raise InvalidExcelError(f"Không thể chuyển dữ liệu sang số: {str(e)}")

        # Validation
        if len(timestamps) == 0:
            raise InvalidExcelError("Không tìm thấy dòng dữ liệu")

        if len(timestamps) != len(ir_signal) or len(timestamps) != len(red_signal):
            raise InvalidExcelError("Độ dài các cột không khớp nhau")

        # Check for NaNs
        nan_count = np.sum(np.isnan(timestamps)) + np.sum(np.isnan(ir_signal)) + np.sum(np.isnan(red_signal))
        if nan_count > 0:
            raise InvalidExcelError(f"Phát hiện {nan_count} giá trị NaN trong dữ liệu")
        if not np.all(np.isfinite(timestamps)) or not np.all(np.isfinite(ir_signal)) or not np.all(np.isfinite(red_signal)):
            raise InvalidExcelError("Dữ liệu chứa giá trị vô hạn (Inf/-Inf)")

        # Check monotonic increasing timestamps
        if not np.all(np.diff(timestamps) >= 0):
            raise InvalidExcelError("Mốc thời gian không tăng dần")

        # Auto-detect sampling frequency
        time_diffs = np.diff(timestamps)
        if np.sum(time_diffs > 0) == 0:
            raise InvalidExcelError("Tất cả mốc thời gian đều giống nhau")

        # Get sampling period from median of non-zero differences
        valid_diffs = time_diffs[time_diffs > 0]
        if len(valid_diffs) == 0:
            raise InvalidExcelError("Không thể xác định tần số lấy mẫu từ mốc thời gian")

        sampling_period = np.median(valid_diffs)
        detected_fs = 1.0 / sampling_period

        # Check if Fs is reasonable
        if detected_fs < 25 or detected_fs > 2000:
            raise InvalidExcelError(
                f"Tần số lấy mẫu phát hiện {detected_fs:.1f} Hz nằm ngoài dải [25, 2000]. "
                f"Vui lòng kiểm tra định dạng cột thời gian (nên là giây)."
            )

        duration_s = timestamps[-1] - timestamps[0]

        return timestamps, ir_signal, red_signal, detected_fs, duration_s

    @staticmethod
    def validate_signal_data(
        timestamps: np.ndarray,
        ir_signal: np.ndarray,
        red_signal: np.ndarray,
        detected_fs: float,
        duration_s: float,
        min_duration: float = 120,
    ) -> Tuple[bool, str]:
        """
        Validate loaded signal data.

        Args:
            timestamps: Timestamp array
            ir_signal: IR channel array
            red_signal: Red channel array
            detected_fs: Sampling frequency in Hz
            duration_s: Signal duration in seconds
            min_duration: Minimum required duration in seconds

        Returns:
            Tuple of (is_valid, warning_message)
        """
        warnings = []

        if duration_s < min_duration:
            warnings.append(
                f"Thời lượng tín hiệu {duration_s:.1f}s < mức tối thiểu {min_duration}s. "
                f"Một số chỉ số (HRV) có thể không hoạt động đúng."
            )

        if detected_fs < 50:
            warnings.append(
                f"Tần số lấy mẫu thấp {detected_fs:.1f} Hz. "
                f"Phát hiện đỉnh có thể kém chính xác hơn."
            )

        # Check for constant signal (no variation)
        ir_range = np.ptp(ir_signal)
        red_range = np.ptp(red_signal)
        
        if ir_range < 1:
            warnings.append("Tín hiệu IR có độ biến thiên biên độ rất thấp")
        if red_range < 1:
            warnings.append("Tín hiệu Red có độ biến thiên biên độ rất thấp")

        warning_message = "\n".join(warnings) if warnings else ""
        return len(warnings) == 0, warning_message


class SignalData:
    """
    Container for PPG signal data.
    
    Stores raw signal (timestamps, IR, Red) and computed properties.
    """

    def __init__(
        self,
        timestamp: np.ndarray,
        ir: np.ndarray,
        red: np.ndarray,
        fs: float,
    ):
        """
        Initialize signal data.

        Args:
            timestamp: Timestamp array (seconds)
            ir: IR channel signal
            red: Red channel signal
            fs: Sampling frequency in Hz
        """
        self.timestamp = np.asarray(timestamp, dtype=float)
        self.ir = np.asarray(ir, dtype=float)
        self.red = np.asarray(red, dtype=float)
        self.fs = float(fs)

        if len(self.timestamp) == 0:
            raise ValueError("Tín hiệu không có mẫu dữ liệu")
        if len(self.timestamp) != len(self.ir) or len(self.timestamp) != len(self.red):
            raise ValueError("Độ dài timestamp/IR/Red không khớp nhau")
        if not np.isfinite(self.fs) or self.fs <= 0:
            raise ValueError(f"Tần số lấy mẫu không hợp lệ: {self.fs}")
        if not np.all(np.isfinite(self.timestamp)) or not np.all(np.isfinite(self.ir)) or not np.all(np.isfinite(self.red)):
            raise ValueError("Tín hiệu chứa giá trị NaN hoặc Inf")
        if not np.all(np.diff(self.timestamp) >= 0):
            raise ValueError("Timestamp phải tăng dần")

        self.timestamp = self.timestamp - self.timestamp[0]

        # Computed properties
        self.duration = self.timestamp[-1] - self.timestamp[0] if len(self.timestamp) > 1 else 0.0
        self.num_samples = len(self.timestamp)

        # Artifact regions (to be populated later)
        self.artifacts = []

    @property
    def sampling_period(self) -> float:
        """Sampling period in seconds."""
        return 1.0 / self.fs

    def get_time_range(self) -> Tuple[float, float]:
        """Get start and end timestamps."""
        return self.timestamp[0], self.timestamp[-1]

    def get_sample_at_time(self, time_s: float) -> int:
        """
        Get sample index closest to given time.

        Args:
            time_s: Time in seconds

        Returns:
            Sample index
        """
        return np.argmin(np.abs(self.timestamp - time_s))

    def get_time_at_sample(self, sample_idx: int) -> float:
        """
        Get timestamp at given sample index.

        Args:
            sample_idx: Sample index

        Returns:
            Time in seconds
        """
        if 0 <= sample_idx < len(self.timestamp):
            return self.timestamp[sample_idx]
        return None

    def get_segment(self, start_time: float, end_time: float) -> "SignalData":
        """
        Extract a time segment from signal.

        Args:
            start_time: Start time in seconds
            end_time: End time in seconds

        Returns:
            New SignalData object with segment
        """
        mask = (self.timestamp >= start_time) & (self.timestamp <= end_time)
        indices = np.where(mask)[0]

        if len(indices) == 0:
            raise ValueError(f"Không có dữ liệu trong khoảng thời gian [{start_time}, {end_time}]")

        new_data = SignalData(
            self.timestamp[indices],
            self.ir[indices],
            self.red[indices],
            self.fs,
        )

        return new_data

    def __len__(self) -> int:
        """Return number of samples."""
        return self.num_samples

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SignalData(samples={self.num_samples}, fs={self.fs}Hz, "
            f"duration={self.duration:.1f}s)"
        )
