"""
Plot widget for signal visualization using Matplotlib.

Displays raw signals, filtered signals, peak detection, and artifact regions.
"""

import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

sys.path.insert(0, str(Path(__file__).parent.parent))


class PlotWidget(QWidget):
    """Widget for plotting PPG signals with zoom/pan interaction."""

    COLORS = {
        "ir_raw": "#90CAF9",
        "ir_filtered": "#1565C0",
        "red_raw": "#FFAB91",
        "red_filtered": "#BF360C",
        "peaks": "#E53935",
        "rr_baseline": "#2E7D32",
        "artifact_bg": "#FFEBEE",
    }

    def __init__(self):
        super().__init__()

        self._pan_start = None
        self._axes_list: List = []
        self._original_xlim: List[Tuple[float, float]] = []
        self._current_timestamp = None
        self._current_signal_data = None
        self._current_results = None
        self._active_mode = "filtered"
        self._crosshair_lines = []
        self._hover_annotation = None
        self._last_hover_idx = None
        self._hover_visible = False

        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("plot_area")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.setStyleSheet(
            """
            QWidget {
                background: #FFFFFF;
                color: #455A64;
            }
            QLabel#artifactWarning {
                background: #FFF8E1;
                color: #E65100;
                border-left: 3px solid #FFA000;
                font-size: 11px;
                padding: 0 12px;
            }
            QPushButton#view_toggle {
                background: transparent;
                border: none;
                color: #5C6BC0;
                padding: 6px 10px;
                font-size: 13px;
            }
            QPushButton#view_toggle:hover {
                background: #E8EAF6;
                border-radius: 4px;
            }
            QPushButton#view_toggle:checked {
                color: #3949AB;
                font-weight: 600;
                border-bottom: 2px solid #3949AB;
            }
            QPushButton#resetButton {
                background: #FFFFFF;
                border: 1px solid #C5CAE9;
                border-radius: 6px;
                color: #3949AB;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton#resetButton:hover {
                background: #E8EAF6;
            }
            """
        )

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        self.btn_raw = self._create_mode_button("Thô", True)
        self.btn_filtered = self._create_mode_button("Đã lọc", False)
        self.btn_peaks = self._create_mode_button("Đỉnh", False)
        self.btn_artifacts = self._create_mode_button("Nhiễu", False)

        for button in [self.btn_raw, self.btn_filtered, self.btn_peaks, self.btn_artifacts]:
            self.mode_group.addButton(button)
            top_row.addWidget(button)

        top_row.addStretch()

        self.btn_reset_view = QPushButton("Đặt lại view")
        self.btn_reset_view.setObjectName("resetButton")
        self.btn_reset_view.clicked.connect(self.reset_view)
        top_row.addWidget(self.btn_reset_view)

        layout.addLayout(top_row)

        self.figure = Figure(figsize=(8, 6), facecolor="#FFFFFF")
        self.figure.subplots_adjust(hspace=0.35, left=0.08, right=0.97, top=0.95, bottom=0.08)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.canvas.setFocus()
        self.canvas.mpl_connect("scroll_event", self._on_scroll)
        self.canvas.mpl_connect("button_press_event", self._on_press)
        self.canvas.mpl_connect("button_release_event", self._on_release)
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.canvas.mpl_connect("motion_notify_event", self._on_hover)
        layout.addWidget(self.canvas, 1)

        self.artifact_warning_label = QLabel("Chưa phát hiện nhiễu chuyển động")
        self.artifact_warning_label.setObjectName("artifactWarning")
        self.artifact_warning_label.setFixedHeight(28)
        self.artifact_warning_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.artifact_warning_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        self.artifact_warning_label.setVisible(False)
        layout.addWidget(self.artifact_warning_label)

        self._create_axes()
        self._style_figure()

        self.btn_raw.toggled.connect(self._set_mode)
        self.btn_filtered.toggled.connect(self._set_mode)
        self.btn_peaks.toggled.connect(self._set_mode)
        self.btn_artifacts.toggled.connect(self._set_mode)

    def _create_mode_button(self, text: str, checked: bool) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("view_toggle")
        button.setCheckable(True)
        button.setChecked(checked)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _create_axes(self):
        self.figure.clear()
        grid = self.figure.add_gridspec(3, 1, height_ratios=[4, 3, 3], hspace=0.25)
        self.ax_hr = self.figure.add_subplot(grid[0, 0])
        self.ax_spo2 = self.figure.add_subplot(grid[1, 0], sharex=self.ax_hr)
        self.ax_rr = self.figure.add_subplot(grid[2, 0], sharex=self.ax_hr)
        self._axes_list = [self.ax_hr, self.ax_spo2, self.ax_rr]
        self._hover_annotation = self.ax_hr.annotate(
            "",
            xy=(0, 0),
            xytext=(10, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="#FFFFFF", ec="#C5CAE9", alpha=0.95),
            color="#263238",
            fontsize=9,
        )
        self._hover_annotation.set_visible(False)
        self._crosshair_lines = [ax.axvline(np.nan, color="#9E9E9E", linestyle="--", linewidth=0.8, alpha=0.6) for ax in self._axes_list]

    def _style_figure(self):
        self.figure.patch.set_facecolor("#FFFFFF")
        for ax in self._axes_list:
            self._style_axes(ax)

    @staticmethod
    def _style_axes(ax):
        ax.set_facecolor("#FAFBFF")
        ax.grid(True, linestyle="--", alpha=0.4, color="#CFD8DC")
        ax.tick_params(colors="#546E7A", labelsize=9)
        ax.xaxis.label.set_color("#78909C")
        ax.yaxis.label.set_color("#78909C")
        ax.yaxis.label.set_size(9)
        ax.title.set_color("#1A237E")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#CFD8DC")
        ax.spines["bottom"].set_color("#CFD8DC")

    def _set_mode(self):
        if self.btn_raw.isChecked():
            self._active_mode = "raw"
        elif self.btn_filtered.isChecked():
            self._active_mode = "filtered"
        elif self.btn_peaks.isChecked():
            self._active_mode = "peaks"
        elif self.btn_artifacts.isChecked():
            self._active_mode = "artifacts"
        self._redraw()

    def plot_raw_signal(self, timestamp, ir_signal, red_signal):
        self._current_timestamp = np.asarray(timestamp)
        self._current_signal_data = {
            "timestamp": np.asarray(timestamp),
            "ir": np.asarray(ir_signal),
            "red": np.asarray(red_signal),
        }
        self._current_results = None
        self._capture_original_xlim()
        self._redraw(raw_only=True)

    def plot_results(self, signal_data, results):
        self._current_signal_data = signal_data
        self._current_results = results
        self._current_timestamp = np.asarray(signal_data.timestamp)
        self._capture_original_xlim()
        self._redraw()

    def show_filtered_view(self):
        """Programmatically switch to filtered tab."""
        self.btn_filtered.setChecked(True)

    def _capture_original_xlim(self):
        if self._current_timestamp is None or len(self._current_timestamp) == 0:
            self._original_xlim = []
            return
        start = float(self._current_timestamp[0])
        end = float(self._current_timestamp[-1])
        self._original_xlim = [(start, end) for _ in self._axes_list]

    def _clear_axes(self):
        for ax in self._axes_list:
            ax.clear()
            self._style_axes(ax)

    def _redraw(self, raw_only: bool = False):
        if self._current_timestamp is None or self._current_signal_data is None:
            return

        timestamp = self._current_timestamp
        self._clear_axes()

        if raw_only or self._current_results is None:
            self._plot_raw_view(timestamp)
            self._set_default_titles()
            self._apply_shared_xlim()
            self.canvas.draw_idle()
            return

        results = self._current_results
        self._plot_result_view(timestamp, results)
        self._set_default_titles()
        self._apply_shared_xlim()
        self.canvas.draw_idle()

    def _plot_raw_view(self, timestamp):
        ir_raw, red_raw = self._get_raw_channels()
        self.ax_hr.plot(timestamp, ir_raw, color=self.COLORS["ir_raw"], linewidth=1.3, label="Tín hiệu gốc IR")
        self.ax_spo2.plot(timestamp, red_raw, color=self.COLORS["red_raw"], linewidth=1.3, label="Tín hiệu gốc Red")
        self.ax_rr.plot(timestamp, ir_raw, color=self.COLORS["ir_raw"], linewidth=1.0, alpha=0.6, label="Tín hiệu gốc IR")

        self.ax_hr.set_ylabel("Biên độ (a.u.)")
        self.ax_spo2.set_ylabel("Biên độ (a.u.)")
        self.ax_rr.set_ylabel("Đường cơ sở")
        self.ax_rr.set_xlabel("Thời gian (s)")

        self.ax_hr.legend(loc="upper right", fontsize=10, framealpha=0.8)
        self.ax_spo2.legend(loc="upper right", fontsize=10, framealpha=0.8)
        self.ax_rr.legend(loc="upper right", fontsize=10, framealpha=0.8)

    def _plot_result_view(self, timestamp, results):
        signal_data = self._current_signal_data
        hr_result = results.get("hr", {})
        spo2_result = results.get("spo2", {})
        rr_result = results.get("rr", {})

        if self._active_mode == "raw":
            self._plot_raw_view(timestamp)
            self._update_artifact_banner(signal_data.artifacts, timestamp)
            return

        hr_filtered = hr_result.get("filtered_signal")
        if hr_filtered is not None and len(hr_filtered) > 0:
            self.ax_hr.plot(timestamp, hr_filtered, color=self.COLORS["ir_filtered"], linewidth=1.3, label="Tín hiệu đã lọc")
            if self._active_mode in ("peaks", "filtered"):
                peak_indices = hr_result.get("peak_indices", [])
                if peak_indices is not None and len(peak_indices) > 0:
                    peak_values = np.asarray(hr_filtered)[peak_indices]
                    peak_times = timestamp[peak_indices]
                    self.ax_hr.scatter(peak_times, peak_values, marker="v", s=60, color=self.COLORS["peaks"], zorder=5, label="Các đỉnh")
        else:
            self.ax_hr.plot(timestamp, signal_data.ir, color=self.COLORS["ir_raw"], linewidth=1.1, label="Tín hiệu gốc")
            self._annotate_metric_unavailable(self.ax_hr, "HR")

        if "ir_bp_filtered" in spo2_result and "red_bp_filtered" in spo2_result:
            if self._active_mode in ("filtered", "peaks"):
                self.ax_spo2.plot(timestamp, spo2_result["ir_bp_filtered"], color=self.COLORS["ir_filtered"], linewidth=1.1, label="IR đã lọc")
                self.ax_spo2.plot(timestamp, spo2_result["red_bp_filtered"], color=self.COLORS["red_filtered"], linewidth=1.1, label="Red đã lọc")
            else:
                self.ax_spo2.plot(timestamp, signal_data.ir, color=self.COLORS["ir_raw"], linewidth=1.0, alpha=0.8, label="IR gốc")
                self.ax_spo2.plot(timestamp, signal_data.red, color=self.COLORS["red_raw"], linewidth=1.0, alpha=0.8, label="Red gốc")
        else:
            self.ax_spo2.plot(timestamp, signal_data.ir, color=self.COLORS["ir_raw"], linewidth=1.0, alpha=0.8, label="IR gốc")
            self.ax_spo2.plot(timestamp, signal_data.red, color=self.COLORS["red_raw"], linewidth=1.0, alpha=0.8, label="Red gốc")
            self._annotate_metric_unavailable(self.ax_spo2, "SpO2")

        rr_filtered = rr_result.get("filtered_signal")
        if rr_filtered is not None and len(rr_filtered) > 0:
            self.ax_rr.plot(timestamp, rr_filtered, color=self.COLORS["rr_baseline"], linewidth=1.2, label="Đường cơ sở")
        else:
            self.ax_rr.plot(timestamp, signal_data.ir, color=self.COLORS["rr_baseline"], linewidth=1.0, alpha=0.7, label="Đường cơ sở")
            self._annotate_metric_unavailable(self.ax_rr, "RR")

        if self._active_mode == "artifacts" and signal_data.artifacts:
            self._plot_artifacts(timestamp, signal_data.artifacts)
        elif signal_data.artifacts:
            self._plot_artifacts(timestamp, signal_data.artifacts, only_subtle=True)

        self.ax_hr.set_ylabel("Biên độ (a.u.)")
        self.ax_spo2.set_ylabel("Biên độ (a.u.)")
        self.ax_rr.set_ylabel("Đường cơ sở")
        self.ax_rr.set_xlabel("Thời gian (s)")

        self.ax_hr.legend(loc="upper right", fontsize=10, framealpha=0.8)
        self.ax_spo2.legend(loc="upper right", fontsize=10, framealpha=0.8)
        self.ax_rr.legend(loc="upper right", fontsize=10, framealpha=0.8)

        self._update_artifact_banner(signal_data.artifacts, timestamp)

    def _get_raw_channels(self):
        """Return raw IR/Red arrays for both dict and SignalData containers."""
        if hasattr(self._current_signal_data, "ir") and hasattr(self._current_signal_data, "red"):
            return np.asarray(self._current_signal_data.ir), np.asarray(self._current_signal_data.red)
        if isinstance(self._current_signal_data, dict):
            return np.asarray(self._current_signal_data["ir"]), np.asarray(self._current_signal_data["red"])
        return np.array([]), np.array([])

    def _plot_artifacts(self, timestamp, artifacts, only_subtle: bool = False):
        alpha = 0.08 if only_subtle else 0.15
        for start_idx, end_idx in artifacts:
            start_idx = max(0, min(start_idx, len(timestamp) - 1))
            end_idx = max(0, min(end_idx, len(timestamp) - 1))
            for ax in self._axes_list:
                ax.axvspan(timestamp[start_idx], timestamp[end_idx], alpha=alpha, color=self.COLORS["artifact_bg"])

    @staticmethod
    def _annotate_metric_unavailable(ax, metric_name: str):
        ax.text(
            0.5,
            0.5,
            f"Không thể tính {metric_name}",
            ha="center",
            va="center",
            transform=ax.transAxes,
            color="#90A4AE",
            fontsize=10,
        )

    def _update_artifact_banner(self, artifacts, timestamp):
        if artifacts and len(artifacts) > 0:
            start_idx, end_idx = artifacts[0]
            start_idx = max(0, min(start_idx, len(timestamp) - 1))
            end_idx = max(0, min(end_idx, len(timestamp) - 1))
            start_t = float(timestamp[start_idx])
            end_t = float(timestamp[end_idx])
            self.artifact_warning_label.setText(
                f"Phát hiện nhiễu chuyển động tại {start_t:.2f}s - {end_t:.2f}s. "
                f"Đoạn này bị loại khỏi phân tích HRV."
            )
            self.artifact_warning_label.setVisible(True)
        else:
            self.artifact_warning_label.setText("Chưa phát hiện nhiễu chuyển động")
            self.artifact_warning_label.setVisible(False)

    def _set_default_titles(self):
        self.ax_hr.set_title("HR / HRV / PI")
        self.ax_spo2.set_title("SpO2")
        self.ax_rr.set_title("RR")

    def _apply_shared_xlim(self):
        if self._original_xlim:
            for ax, xlim in zip(self._axes_list, self._original_xlim):
                if ax.get_xlim() == (0.0, 1.0):
                    ax.set_xlim(*xlim)
        self.figure.tight_layout()

    def reset_view(self):
        if not self._original_xlim:
            return
        for ax, xlim in zip(self._axes_list, self._original_xlim):
            ax.set_xlim(*xlim)
        self.canvas.draw_idle()

    def _on_scroll(self, event):
        """Zoom tại vị trí con trỏ, tất cả subplot đồng bộ trục X."""
        if event.inaxes is None or event.xdata is None:
            return
        factor = 0.85 if event.button == "up" else 1.15
        center = event.xdata
        for ax in self._axes_list:
            xlim = ax.get_xlim()
            left = center - (center - xlim[0]) * factor
            right = center + (xlim[1] - center) * factor
            if left == right:
                continue
            ax.set_xlim(left, right)
        self.canvas.draw_idle()

    def _on_press(self, event):
        """Bắt đầu kéo để pan."""
        if event.button == 1 and event.inaxes is not None and event.xdata is not None:
            self._pan_start = (event.xdata, [ax.get_xlim() for ax in self._axes_list])

    def _on_release(self, event):
        self._pan_start = None

    def _on_motion(self, event):
        """Pan đồng bộ tất cả subplot theo trục X."""
        if self._pan_start is None or event.xdata is None:
            return
        dx = event.xdata - self._pan_start[0]
        for ax, xlim in zip(self._axes_list, self._pan_start[1]):
            ax.set_xlim(xlim[0] - dx, xlim[1] - dx)
        self.canvas.draw_idle()

    def _on_hover(self, event):
        if event.inaxes is None or event.xdata is None:
            if self._hover_visible:
                self._hover_annotation.set_visible(False)
                self._hover_visible = False
                self._last_hover_idx = None
                self.canvas.draw_idle()
            return

        for line in self._crosshair_lines:
            line.set_xdata([event.xdata, event.xdata])

        if self._current_timestamp is None:
            return

        idx = int(np.clip(np.searchsorted(self._current_timestamp, event.xdata), 0, len(self._current_timestamp) - 1))
        if self._last_hover_idx == idx and self._hover_visible:
            return

        t = float(self._current_timestamp[idx])
        y = 0.0
        if self._current_signal_data is not None:
            if hasattr(self._current_signal_data, "ir"):
                y = float(np.asarray(self._current_signal_data.ir)[idx])
            elif isinstance(self._current_signal_data, dict) and "ir" in self._current_signal_data:
                y = float(np.asarray(self._current_signal_data["ir"])[idx])

        self._hover_annotation.xy = (t, y)
        self._hover_annotation.set_text(f"t = {t:.2f} s\ny = {y:.2f}")
        self._hover_annotation.set_visible(True)
        self._hover_visible = True
        self._last_hover_idx = idx
        self.canvas.draw_idle()

    def clear_plots(self):
        self.figure.clear()
        self._create_axes()
        self._style_figure()
        self.canvas.draw_idle()
        self.artifact_warning_label.setVisible(False)
