"""
Configurable parameter panel for signal processing.

Provides compact 2x3 metric tabs and stacked parameter pages.
"""

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.preset_manager import PresetManager


SLIDER_STYLE = """
QSlider {
    min-height: 20px;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #C5CAE9;
    border-radius: 2px;
    margin: 0px;
}
QSlider::sub-page:horizontal {
    background: #3949AB;
    border-radius: 2px;
    height: 4px;
}
QSlider::add-page:horizontal {
    background: #E0E4EC;
    border-radius: 2px;
    height: 4px;
}
QSlider::handle:horizontal {
    background: #3949AB;
    border: 2px solid #FFFFFF;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #283593;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
"""


class ParameterPanel(QWidget):
    """Panel with configurable parameters for all metrics."""

    TAB_LABELS = ["HR", "SpO2", "RR", "HRV", "PI", "Cảnh báo"]

    def __init__(self, preset_manager: PresetManager):
        super().__init__()
        self.preset_manager = preset_manager
        self.metadata = preset_manager.get_param_metadata()
        self.param_controls = {}
        self.syncing = False
        self.tab_buttons = []
        self._tab_index = {}

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tab_grid = QGridLayout()
        tab_grid.setSpacing(3)
        tab_grid.setContentsMargins(0, 0, 0, 8)

        for i, label in enumerate(self.TAB_LABELS):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("metric_tab")
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda _, l=label: self._switch_tab(l))
            row, col = divmod(i, 3)
            tab_grid.addWidget(btn, row, col)
            self.tab_buttons.append(btn)

        layout.addLayout(tab_grid)

        self.filter_stack = QStackedWidget()
        self.filter_stack.addWidget(self._create_hr_tab())
        self.filter_stack.addWidget(self._create_spo2_tab())
        self.filter_stack.addWidget(self._create_rr_tab())
        self.filter_stack.addWidget(self._create_hrv_tab())
        self.filter_stack.addWidget(self._create_pi_tab())
        self.filter_stack.addWidget(self._create_validation_tab())
        layout.addWidget(self.filter_stack, 1)

        self._tab_index = {label: idx for idx, label in enumerate(self.TAB_LABELS)}
        self._switch_tab("HR")

        self.setStyleSheet(
            """
            QWidget { background: transparent; }
            QPushButton#metric_tab {
                border: 1px solid #E0E4EC;
                background: #FFFFFF;
                color: #5C6BC0;
                border-radius: 4px;
                font-size: 11px;
                padding: 0;
            }
            QPushButton#metric_tab:checked {
                background: #3949AB;
                color: #FFFFFF;
                border-color: #3949AB;
            }
            QPushButton#metric_tab:hover:!checked {
                background: #E8EAF6;
            }
            QLabel { color: #455A64; font-size: 11px; }
            """
        )

    def _switch_tab(self, label: str):
        for btn in self.tab_buttons:
            btn.setChecked(btn.text() == label)
        self.filter_stack.setCurrentIndex(self._tab_index[label])

    def _create_parameter_row(
        self,
        parent_layout,
        key,
        label_text,
        value_type,
        min_val,
        max_val,
        current_value,
        step=None,
        unit="",
    ):
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 3, 0, 3)
        row_layout.setSpacing(8)

        label = QLabel(label_text)
        label.setFixedWidth(110)
        label.setStyleSheet("font-size: 11px; color: #546E7A;")
        row_layout.addWidget(label)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setStyleSheet(SLIDER_STYLE)
        slider.setMinimumWidth(80)
        slider.setFixedHeight(20)

        if value_type == "int":
            slider.setMinimum(int(min_val))
            slider.setMaximum(int(max_val))
            slider.setValue(int(current_value))
            if step is None:
                step = 1

            spinbox = QSpinBox()
            spinbox.setMinimum(int(min_val))
            spinbox.setMaximum(int(max_val))
            spinbox.setValue(int(current_value))
            spinbox.setSingleStep(step)
        else:
            slider_range = int((max_val - min_val) * 100)
            slider.setMinimum(0)
            slider.setMaximum(slider_range)
            slider.setValue(int((current_value - min_val) * 100))
            if step is None:
                step = (max_val - min_val) / 100

            spinbox = QDoubleSpinBox()
            spinbox.setMinimum(min_val)
            spinbox.setMaximum(max_val)
            spinbox.setValue(current_value)
            spinbox.setSingleStep(step)
            spinbox.setDecimals(2)

        spinbox.setFixedWidth(54)
        spinbox.setFixedHeight(24)
        spinbox.setStyleSheet(
            """
            QDoubleSpinBox, QSpinBox {
                border: 1px solid #C5CAE9;
                border-radius: 4px;
                padding: 0 4px;
                background: #FFFFFF;
                color: #1A237E;
                font-size: 11px;
                font-weight: bold;
            }
            QDoubleSpinBox::up-button, QSpinBox::up-button,
            QDoubleSpinBox::down-button, QSpinBox::down-button {
                width: 14px;
            }
            """
        )

        unit_label = QLabel(unit)
        unit_label.setStyleSheet("font-size: 10px; color: #90A4AE;")
        unit_label.setFixedWidth(18)

        row_layout.addWidget(slider, 1)
        row_layout.addWidget(spinbox)
        row_layout.addWidget(unit_label)

        def on_slider_changed(val):
            if self.syncing:
                return
            self.syncing = True
            try:
                if value_type == "int":
                    spinbox.setValue(val)
                else:
                    spinbox.setValue(min_val + val / 100)
            finally:
                self.syncing = False

        def on_spinbox_changed(val):
            if self.syncing:
                return
            self.syncing = True
            try:
                if value_type == "int":
                    slider.setValue(val)
                else:
                    slider.setValue(int((val - min_val) * 100))
            finally:
                self.syncing = False

        slider.valueChanged.connect(on_slider_changed)
        spinbox.valueChanged.connect(on_spinbox_changed)
        self.param_controls[key] = {"slider": slider, "spinbox": spinbox}
        parent_layout.addLayout(row_layout)

    def _create_combobox_row(self, key, label_text, options, current_value):
        row = QHBoxLayout()
        row.setSpacing(6)
        row.setContentsMargins(0, 2, 0, 2)

        label = QLabel(label_text)
        label.setFixedWidth(130)
        label.setStyleSheet("font-size: 11px; color: #546E7A;")

        combobox = QComboBox()
        combobox.addItems(options)
        combobox.setCurrentText(current_value)
        combobox.setFixedHeight(24)
        combobox.setStyleSheet(
            """
            QComboBox {
                border: 1px solid #C5CAE9;
                border-radius: 4px;
                background: #FFFFFF;
                color: #1A237E;
                font-size: 11px;
                padding: 0 6px;
            }
            """
        )

        self.param_controls[key] = {"combobox": combobox}
        row.addWidget(label)
        row.addWidget(combobox, 1)
        return row

    def _create_section_label(self, text):
        label = QLabel(text)
        label.setObjectName("group_label")
        label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        label.setStyleSheet(
            """
            font-size: 10px;
            font-weight: bold;
            color: #90A4AE;
            padding-top: 8px;
            padding-bottom: 4px;
            border-top: 1px solid #ECEFF1;
            """
        )
        return label

    def _create_note_label(self, text: str):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(
            """
            background: #F5F7FF;
            color: #5C6BC0;
            border: 1px solid #DDE3FF;
            border-radius: 6px;
            padding: 6px 8px;
            font-size: 10px;
            """
        )
        return label

    def _build_page_container(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        return page, layout

    def _create_hr_tab(self):
        widget, layout = self._build_page_container()

        layout.addWidget(self._create_note_label(
            "Lọc tín hiệu HR: IIR Butterworth (zero-phase filtfilt)."
        ))

        layout.addWidget(self._create_section_label("Bộ lọc thông cao (IIR Butterworth)"))
        self._create_parameter_row(layout, "hr.highpass_cutoff", "Tần số cắt", "float", 0.1, 2.0, 0.5, step=0.1, unit="Hz")
        self._create_parameter_row(layout, "hr.highpass_order", "Bậc lọc", "int", 1, 10, 4)

        layout.addWidget(self._create_section_label("Bộ lọc thông thấp (IIR Butterworth)"))
        self._create_parameter_row(layout, "hr.lowpass_cutoff", "Tần số cắt", "float", 1.0, 10.0, 4.5, step=0.5, unit="Hz")
        self._create_parameter_row(layout, "hr.lowpass_order", "Bậc lọc", "int", 1, 10, 4)

        layout.addWidget(self._create_section_label("Phát hiện đỉnh"))
        self._create_parameter_row(layout, "hr.peak_min_distance", "Khoảng cách tối thiểu", "float", 0.3, 1.5, 0.6, step=0.05, unit="s")
        self._create_parameter_row(layout, "hr.peak_min_height_pct", "Biên độ tối thiểu", "int", 10, 80, 30, unit="%")

        layout.addStretch()
        return widget

    def _create_spo2_tab(self):
        widget, layout = self._build_page_container()

        layout.addWidget(self._create_note_label(
            "Lọc tín hiệu SpO2: IIR Butterworth (bandpass + lowpass)."
        ))

        layout.addWidget(self._create_section_label("Bộ lọc thông dải (IIR Butterworth)"))
        self._create_parameter_row(layout, "spo2.bandpass_low", "Tần số cắt thấp", "float", 0.5, 2.0, 0.8, step=0.1, unit="Hz")
        self._create_parameter_row(layout, "spo2.bandpass_high", "Tần số cắt cao", "float", 2.0, 8.0, 4.0, step=0.5, unit="Hz")
        self._create_parameter_row(layout, "spo2.bandpass_order", "Bậc lọc", "int", 1, 10, 4)

        layout.addWidget(self._create_section_label("Kiểm tra tỉ số R"))
        self._create_parameter_row(layout, "spo2.r_ratio_min", "R tối thiểu", "float", 0.2, 2.0, 0.4, step=0.1)
        self._create_parameter_row(layout, "spo2.r_ratio_max", "R tối đa", "float", 1.5, 5.0, 3.4, step=0.5)

        layout.addWidget(self._create_section_label("Hiệu chuẩn"))
        self._create_parameter_row(layout, "spo2.coeff_a", "Hệ số A", "float", 100, 120, 104.0, step=1.0)
        self._create_parameter_row(layout, "spo2.coeff_b", "Hệ số B", "float", 10, 30, 17.0, step=1.0)

        layout.addStretch()
        return widget

    def _create_rr_tab(self):
        widget, layout = self._build_page_container()

        layout.addWidget(self._create_note_label(
            "Lọc tín hiệu RR: IIR Butterworth thông thấp để tách đường nền hô hấp."
        ))

        layout.addWidget(self._create_section_label("Bộ lọc thông thấp (IIR Butterworth)"))
        self._create_parameter_row(layout, "rr.lowpass_cutoff", "Tần số cắt", "float", 0.1, 0.8, 0.4, step=0.05, unit="Hz")
        self._create_parameter_row(layout, "rr.lowpass_order", "Bậc lọc", "int", 1, 12, 6)

        layout.addWidget(self._create_section_label("Phát hiện đỉnh"))
        self._create_parameter_row(layout, "rr.peak_min_spacing", "Khoảng cách tối thiểu", "float", 2.0, 8.0, 3.0, step=0.5, unit="s")
        self._create_parameter_row(layout, "rr.peak_max_spacing", "Khoảng cách tối đa", "float", 3.0, 12.0, 6.0, step=0.5, unit="s")

        layout.addStretch()
        return widget

    def _create_hrv_tab(self):
        widget, layout = self._build_page_container()

        layout.addWidget(self._create_section_label("Thiết lập phân tích"))
        layout.addLayout(self._create_combobox_row("hrv.analysis_channel", "Kênh phân tích", ["IR", "Đỏ"], "IR"))
        self._create_parameter_row(layout, "hrv.min_segment_length", "Độ dài tối thiểu", "int", 60, 300, 120, unit="s")

        layout.addWidget(self._create_section_label("Ngưỡng căng thẳng"))
        self._create_parameter_row(layout, "hrv.stress_sdnn_low", "SDNN thấp", "int", 10, 50, 20, unit="ms")
        self._create_parameter_row(layout, "hrv.stress_sdnn_high", "SDNN cao", "int", 30, 100, 50, unit="ms")

        layout.addStretch()
        return widget

    def _create_pi_tab(self):
        widget, layout = self._build_page_container()

        layout.addWidget(self._create_note_label(
            "PI dùng thành phần AC/DC từ tín hiệu đã lọc IIR. "
            "Tab này chỉ chứa tham số xử lý/lọc, không chứa ngưỡng cảnh báo."
        ))

        layout.addWidget(self._create_section_label("Xử lý thành phần AC/DC (IIR)"))
        self._create_parameter_row(layout, "pi.ac_dc_window", "Cửa sổ AC/DC", "float", 0.5, 5.0, 1.0, step=0.5, unit="s")

        layout.addStretch()
        return widget

    def _create_validation_tab(self):
        widget, layout = self._build_page_container()

        layout.addWidget(self._create_note_label(
            "Các tham số trong tab này chỉ phục vụ kiểm tra và cảnh báo chất lượng, "
            "được tách riêng khỏi các tab điều chỉnh lọc tín hiệu."
        ))

        layout.addWidget(self._create_section_label("Tần số lấy mẫu"))

        auto_detect_row = QHBoxLayout()
        auto_detect_row.setSpacing(6)
        auto_detect_row.setContentsMargins(0, 2, 0, 2)
        auto_detect_label = QLabel("Tự phát hiện Fs")
        auto_detect_label.setFixedWidth(130)
        auto_detect_check = QCheckBox()
        auto_detect_check.setChecked(True)
        self.param_controls["validation.auto_detect_fs"] = {"checkbox": auto_detect_check}
        auto_detect_row.addWidget(auto_detect_label)
        auto_detect_row.addWidget(auto_detect_check)
        auto_detect_row.addStretch()
        layout.addLayout(auto_detect_row)

        self._create_parameter_row(layout, "validation.fs_manual", "Fs thủ công", "float", 25, 2000, 100.0, step=10.0, unit="Hz")

        layout.addWidget(self._create_section_label("Ngưỡng cảnh báo chất lượng"))
        self._create_parameter_row(layout, "pi.warning_threshold", "PI cảnh báo", "float", 0.1, 2.0, 0.5, step=0.1, unit="%")
        self._create_parameter_row(layout, "validation.min_duration", "Độ dài tối thiểu", "int", 30, 300, 120, unit="s")

        layout.addWidget(self._create_section_label("Cảnh báo nhiễu"))
        self._create_parameter_row(layout, "validation.artifact_threshold_sd", "Ngưỡng SD", "float", 1.0, 10.0, 3.0, step=0.5, unit="σ")

        layout.addWidget(self._create_section_label("Hiển thị"))
        self._create_parameter_row(layout, "validation.max_display_rows", "Dòng tối đa", "int", 100, 5000, 1000)

        layout.addStretch()
        return widget

    def get_parameters(self) -> dict:
        params = {}

        for key, controls in self.param_controls.items():
            if "spinbox" in controls:
                params[key] = controls["spinbox"].value()
            elif "slider" in controls:
                params[key] = controls["slider"].value()
            elif "checkbox" in controls:
                params[key] = controls["checkbox"].isChecked()
            elif "combobox" in controls:
                params[key] = controls["combobox"].currentText()

        return params

    def set_parameters(self, params: dict):
        self.syncing = True
        try:
            for key, value in params.items():
                if key not in self.param_controls:
                    continue

                controls = self.param_controls[key]
                if "spinbox" in controls:
                    spinbox = controls["spinbox"]
                    slider = controls.get("slider")

                    if isinstance(spinbox, QSpinBox):
                        int_value = int(round(float(value)))
                        spinbox.setValue(int_value)
                        if slider is not None:
                            slider.setValue(int_value)
                    elif isinstance(spinbox, QDoubleSpinBox):
                        float_value = float(value)
                        spinbox.setValue(float_value)
                        if slider is not None:
                            slider_value = int((float_value - spinbox.minimum()) * 100)
                            slider_value = max(slider.minimum(), min(slider.maximum(), slider_value))
                            slider.setValue(slider_value)
                elif "checkbox" in controls:
                    controls["checkbox"].setChecked(bool(value))
                elif "combobox" in controls:
                    controls["combobox"].setCurrentText(str(value))
        finally:
            self.syncing = False

    def get_param(self, key: str):
        if key not in self.param_controls:
            return None

        controls = self.param_controls[key]
        if "spinbox" in controls:
            return controls["spinbox"].value()
        if "slider" in controls:
            return controls["slider"].value()
        if "checkbox" in controls:
            return controls["checkbox"].isChecked()
        if "combobox" in controls:
            return controls["combobox"].currentText()
        return None
