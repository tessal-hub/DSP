"""
Results panel for displaying analysis metrics.

Shows HR, SpO2, RR, HRV, and PI with quality indicators.
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

sys.path.insert(0, str(Path(__file__).parent.parent))


class MetricCard(QFrame):
    """Card displaying a single metric."""

    def __init__(self, title: str):
        """
        Initialize metric card.

        Args:
            title: Metric name
        """
        super().__init__()

        self.BADGE_STYLES = {
            "good": "background:#E8F5E9;color:#2E7D32;border-radius:10px;padding:1px 8px;font-size:10px",
            "warning": "background:#FFF8E1;color:#F57F17;border-radius:10px;padding:1px 8px;font-size:10px",
            "poor": "background:#FFEBEE;color:#C62828;border-radius:10px;padding:1px 8px;font-size:10px",
            "na": "background:#ECEFF1;color:#546E7A;border-radius:10px;padding:1px 8px;font-size:10px",
        }
        
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("metric_card")
        self.setStyleSheet(
            """
            QFrame#metric_card {
                background-color: #F8F9FE;
                border: 1px solid #E8EEF8;
                border-radius: 8px;
            }
            """
        )
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        title_label.setStyleSheet("color: #78909C;")
        layout.addWidget(title_label)
        
        # Main value (large)
        self.value_label = QLabel("—")
        font = QFont("Segoe UI", 22, QFont.Weight.DemiBold)
        self.value_label.setFont(font)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.value_label.setStyleSheet("color: #1A237E;")
        layout.addWidget(self.value_label)
        
        # Unit + Quality
        unit_quality_layout = QHBoxLayout()
        self.unit_label = QLabel("")
        self.unit_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.unit_label.setStyleSheet("color: #5C6BC0;")
        unit_quality_layout.addWidget(self.unit_label)
        
        self.quality_label = QLabel("N/A")
        self.quality_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.quality_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.quality_label.setStyleSheet(
            self.BADGE_STYLES["na"]
        )
        unit_quality_layout.addWidget(self.quality_label)
        
        layout.addLayout(unit_quality_layout)
        
        # Details
        self.details_label = QLabel("")
        self.details_label.setFont(QFont("Segoe UI", 10))
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet("color: #90A4AE;")
        layout.addWidget(self.details_label)

    def set_value(self, value, unit="", quality="N/A", quality_color="black", details=""):
        """Set metric value."""
        if value is None:
            self.value_label.setText("—")
        else:
            self.value_label.setText(f"{value:.1f}" if isinstance(value, float) else str(value))
        
        self.unit_label.setText(unit)
        self.quality_label.setText(quality)
        quality_key = {
            "#2E7D32": "good",
            "#F57F17": "warning",
            "#C62828": "poor",
        }.get(quality_color, "na")
        self.quality_label.setStyleSheet(self.BADGE_STYLES[quality_key])
        self.details_label.setText(details)


class ResultsPanel(QWidget):
    """Panel displaying all metric results."""

    def __init__(self):
        """Initialize results panel."""
        super().__init__()
        
        self._setup_ui()

    def _setup_ui(self):
        """Setup results display."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        title = QLabel("KẾT QUẢ")
        title.setObjectName("section_label")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("text-transform: uppercase;")
        layout.addWidget(title)
        
        # Vertical metric cards
        self.hr_card = MetricCard("Nhịp tim")
        self.spo2_card = MetricCard("SpO2")
        self.rr_card = MetricCard("Nhịp thở")
        self.hrv_card = MetricCard("HRV - SDNN")
        self.pi_card = MetricCard("Chỉ số tưới máu")
        layout.addWidget(self.hr_card)
        layout.addWidget(self.spo2_card)
        layout.addWidget(self.rr_card)
        layout.addWidget(self.hrv_card)
        layout.addWidget(self.pi_card)
        layout.addStretch()

    def display_results(self, results: dict):
        """
        Display results from analysis.

        Args:
            results: Results dictionary from signal processor
        """
        # HR
        hr_result = results.get("hr", {})
        hr_bpm = hr_result.get("bpm")
        hr_quality = hr_result.get("quality", "N/A")
        hr_reason = hr_result.get("quality_reason", "")
        hr_details = f"Dải tham chiếu: 60–100 BPM\n{hr_reason}".strip()
        hr_quality_color = self._get_quality_color(hr_quality)
        
        self.hr_card.set_value(
            hr_bpm, "BPM", self._localize_quality(hr_quality), hr_quality_color, hr_details or "Dải tham chiếu: 60–100 BPM"
        )
        
        # SpO2
        spo2_result = results.get("spo2", {})
        spo2_pct = spo2_result.get("spo2_pct")
        spo2_quality = spo2_result.get("quality", "N/A")
        r_ratio = spo2_result.get("r_ratio")
        spo2_details = f"R-ratio: {r_ratio:.3f}" if r_ratio is not None else "R-ratio: --"
        spo2_quality_color = self._get_quality_color(spo2_quality)
        
        self.spo2_card.set_value(
            spo2_pct, "%", self._localize_quality(spo2_quality), spo2_quality_color, spo2_details
        )
        
        # RR
        rr_result = results.get("rr", {})
        rr_breaths = rr_result.get("rr_breaths_min")
        rr_quality = rr_result.get("quality", "N/A")
        rr_details = rr_result.get("quality_reason", "")
        rr_quality_color = self._get_quality_color(rr_quality)
        
        self.rr_card.set_value(
            rr_breaths, "br/ph", self._localize_quality(rr_quality), rr_quality_color, rr_details
        )
        
        # HRV
        hrv_result = results.get("hrv", {})
        stress_level = hrv_result.get("stress_level", "N/A")
        hrv_quality = hrv_result.get("quality", "N/A")
        sdnn = hrv_result.get("sdnn_ms")
        rmssd = hrv_result.get("rmssd_ms")
        hrv_quality_color = self._get_quality_color(hrv_quality)
        hrv_details = (
            f"RMSSD: {rmssd:.0f} ms · {self._localize_stress(stress_level)}"
            if rmssd is not None
            else hrv_result.get("quality_reason", "Cần ≥ 2 phút để tính HRV")
        )
        
        self.hrv_card.set_value(
            int(sdnn) if sdnn is not None else None,
            "ms",
            self._localize_quality(hrv_quality),
            hrv_quality_color,
            hrv_details
        )
        
        # PI
        pi_result = results.get("pi", {})
        pi_pct = pi_result.get("pi_pct")
        pi_quality = pi_result.get("quality", "N/A")
        pi_details = pi_result.get("quality_reason", "")
        pi_quality_color = self._get_quality_color(pi_quality)
        
        self.pi_card.set_value(
            pi_pct, "%", self._localize_quality(pi_quality), pi_quality_color, pi_details
        )

        if results.get("error"):
            self.pi_card.details_label.setText(
                f"{self.pi_card.details_label.text()}\nLỗi pipeline: {results['error']}".strip()
            )

    @staticmethod
    def _get_quality_color(quality: str) -> str:
        """Get color for quality indicator."""
        if quality == "Good":
            return "#2E7D32"
        elif quality == "Warning":
            return "#F57F17"
        elif quality == "Poor":
            return "#C62828"
        else:
            return "#90A4AE"

    @staticmethod
    def _localize_quality(quality: str) -> str:
        mapping = {
            "Good": "Tốt",
            "Warning": "Cảnh báo",
            "Poor": "Kém",
            "N/A": "N/A",
        }
        return mapping.get(quality, quality)

    @staticmethod
    def _localize_stress(stress_level: str) -> str:
        mapping = {
            "Relaxed": "Thư giãn",
            "Normal": "Bình thường",
            "High Stress": "Căng thẳng cao",
            None: "N/A",
        }
        return mapping.get(stress_level, stress_level)
