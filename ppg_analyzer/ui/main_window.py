"""
Main application window for PPG Signal Analyzer.

Orchestrates the overall UI layout and signal/slot connections.
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog,
    QStatusBar, QProgressBar,
    QFrame, QDialog, QSizePolicy
)
from PyQt6.QtCore import Qt

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.excel_io import SignalLoader, SignalData
from core.preset_manager import PresetManager
from ui.param_panel import ParameterPanel
from ui.plot_widget import PlotWidget
from ui.results_panel import ResultsPanel
from ui.analysis_thread import AnalysisThread


class LightDialog(QDialog):
    """Custom light-theme dialog replacing default QMessageBox."""

    def __init__(self, title, message, icon_type="warning", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setStyleSheet(
            """
            QDialog { background: #FFFFFF; }
            QLabel#msg { color: #37474F; font-size: 12px; }
            QPushButton {
                background: #FFFFFF;
                color: #3949AB;
                border: 1px solid #C5CAE9;
                border-radius: 6px;
                padding: 6px 20px;
            }
            QPushButton:hover { background: #E8EAF6; }
            """
        )

        layout = QVBoxLayout(self)
        row = QHBoxLayout()

        icon_label = QLabel()
        if icon_type == "warning":
            icon_label.setText("⚠")
            icon_label.setStyleSheet("font-size: 24px; color: #FFA000;")
        elif icon_type == "error":
            icon_label.setText("✕")
            icon_label.setStyleSheet("font-size: 20px; color: #C62828; font-weight: bold;")
        else:
            icon_label.setText("i")
            icon_label.setStyleSheet("font-size: 20px; color: #3949AB; font-weight: bold;")
        row.addWidget(icon_label)

        msg_label = QLabel(message)
        msg_label.setObjectName("msg")
        msg_label.setWordWrap(True)
        row.addWidget(msg_label, 1)
        layout.addLayout(row)

        btn = QPushButton("Đồng ý")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)
        self.setMinimumWidth(380)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()
        
        self.setWindowTitle("PPG Signal Analyzer")
        self.setGeometry(100, 100, 1600, 900)
        
        # App state
        self.signal_data = None
        self.current_results = None
        self.preset_manager = PresetManager()
        self.analysis_thread = None
        self.current_preset_name = "mặc định"
        
        # Initialize UI
        self._setup_ui()
        self._setup_status_bar()
        self._apply_styles()
        
        # Load last-used preset
        self._load_last_preset()

    def _setup_ui(self):
        """Setup main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Top toolbar with buttons
        topbar = QWidget()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(52)
        topbar.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        toolbar_layout = QHBoxLayout(topbar)
        toolbar_layout.setContentsMargins(20, 0, 20, 0)
        toolbar_layout.setSpacing(8)

        title_label = QLabel("PPG Signal Analyzer")
        title_label.setObjectName("headerTitle")
        toolbar_layout.addWidget(title_label)
        toolbar_layout.addStretch()
        
        btn_load = QPushButton("Tải Excel")
        btn_load.clicked.connect(self._on_load_excel)
        btn_load.setMinimumWidth(140)
        btn_load.setFixedHeight(34)
        btn_load.setObjectName("btn_normal")
        self.btn_load = btn_load

        btn_run = QPushButton("Chạy phân tích")
        btn_run.clicked.connect(self._on_run_analysis)
        btn_run.setMinimumWidth(160)
        btn_run.setFixedHeight(34)
        btn_run.setEnabled(False)
        btn_run.setObjectName("btn_run")
        self.btn_run = btn_run
        
        toolbar_layout.addWidget(btn_load)
        toolbar_layout.addWidget(btn_run)
        
        main_layout.addWidget(topbar)
        
        # Main content area with left panel, center plot, right results
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Left panel: File info + Parameters
        left_widget = QWidget()
        left_widget.setObjectName("left_panel")
        left_widget.setFixedWidth(280)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(0)
        
        # File info section
        file_info_label = QLabel("Dữ liệu đầu vào")
        file_info_label.setObjectName("section_label")
        left_layout.addWidget(file_info_label)
        left_layout.addSpacing(6)
        
        file_card = QFrame()
        file_card.setObjectName("file_card")
        file_card_layout = QVBoxLayout(file_card)
        file_card_layout.setContentsMargins(10, 8, 10, 8)
        file_card_layout.setSpacing(2)
        self.lbl_filename = QLabel("Chưa tải tệp")
        self.lbl_filename.setStyleSheet("font-size: 12px; font-weight: bold; color: #1A237E;")
        self.lbl_filemeta = QLabel("3 cột · 0 mẫu · Fs = -- Hz")
        self.lbl_filemeta.setStyleSheet("font-size: 11px; color: #5C6BC0;")
        file_card_layout.addWidget(self.lbl_filename)
        file_card_layout.addWidget(self.lbl_filemeta)
        left_layout.addWidget(file_card)
        left_layout.addSpacing(14)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #E0E4EC;")
        left_layout.addWidget(divider)
        left_layout.addSpacing(10)

        filter_label = QLabel("Thông số bộ lọc")
        filter_label.setObjectName("section_label")
        left_layout.addWidget(filter_label)
        left_layout.addSpacing(8)

        self.param_panel = ParameterPanel(self.preset_manager)
        left_layout.addWidget(self.param_panel, 1)

        left_layout.addSpacing(10)

        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(8)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        btn_reset = QPushButton("Đặt lại mặc định")
        btn_reset.setObjectName("btn_reset")
        btn_reset.setFixedHeight(32)
        btn_reset.clicked.connect(self._on_reset_defaults)
        self.btn_reset = btn_reset
        btn_save = QPushButton("Lưu cấu hình")
        btn_save.setObjectName("btn_save")
        btn_save.setFixedHeight(32)
        btn_save.clicked.connect(self._on_save_preset)
        self.btn_save = btn_save
        preset_layout.addWidget(btn_reset)
        preset_layout.addWidget(btn_save)
        left_layout.addLayout(preset_layout)
        
        # Center: Plot widget
        self.plot_widget = PlotWidget()
        
        # Right: Results panel
        self.results_panel = ResultsPanel()
        self.results_panel.setObjectName("right_panel")
        self.results_panel.setFixedWidth(220)

        content_layout.addWidget(left_widget)
        content_layout.addWidget(self.plot_widget, 1)
        content_layout.addWidget(self.results_panel)
        main_layout.addWidget(content_widget, 1)

    def _setup_status_bar(self):
        """Setup status bar."""
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Sẵn sàng")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)

    @staticmethod
    def _format_duration(duration_s: float) -> str:
        minutes = int(duration_s // 60)
        seconds = int(duration_s % 60)
        return f"{minutes} phút {seconds:02d} giây"

    def _show_status(self, prefix: str = ""):
        if self.signal_data is None:
            self.statusBar().showMessage(prefix or "Sẵn sàng")
            return

        fs = self.signal_data.fs
        dur = self.signal_data.duration
        base = (
            f"Fs: {fs:.0f} Hz (tự phát hiện)  |  "
            f"Thời lượng: {self._format_duration(dur)}  |  "
            f"Cấu hình: {self.current_preset_name}"
        )
        if prefix:
            self.statusBar().showMessage(f"{prefix}  |  {base}")
        else:
            self.statusBar().showMessage(base)

    def _apply_styles(self):
        """Apply light professional style."""
        self.setStyleSheet(
            """
            QLabel#headerTitle {
                font-size: 16px;
                font-weight: 700;
                color: #1A237E;
                padding-left: 0;
            }
            QWidget#left_panel {
                border-right: 1px solid #E0E4EC;
            }
            QWidget#right_panel {
                border-left: 1px solid #E0E4EC;
            }
            QScrollBar:vertical {
                background: #F5F6FA;
                width: 12px;
                margin: 0;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #B0BEC5;
                min-height: 24px;
                border-radius: 6px;
            }
            """
        )

    def _load_last_preset(self):
        """Load last-used preset on startup."""
        try:
            params = self.preset_manager.auto_load_last_used()
            self.param_panel.set_parameters(params)
        except Exception as e:
            print(f"Could not load last preset: {e}")

    def _show_warning(self, title: str, message: str):
        LightDialog(title, message, "warning", self).exec()

    def _show_error(self, title: str, message: str):
        LightDialog(title, message, "error", self).exec()

    def _show_info(self, title: str, message: str):
        LightDialog(title, message, "info", self).exec()

    def _set_busy_state(self, is_busy: bool):
        """Toggle UI controls while background analysis is running."""
        self.btn_run.setEnabled(not is_busy and self.signal_data is not None)
        self.btn_load.setEnabled(not is_busy)
        self.btn_reset.setEnabled(not is_busy)
        self.btn_save.setEnabled(not is_busy)
        self.progress_bar.setVisible(is_busy)
        if is_busy:
            self.progress_bar.setMaximum(0)
        else:
            self.progress_bar.setMaximum(100)

    def _on_load_excel(self):
        """Handle Load Excel button click."""
        if self.analysis_thread is not None and self.analysis_thread.isRunning():
            self._show_warning("Đang phân tích", "Vui lòng chờ phân tích hiện tại hoàn tất trước khi tải tệp mới.")
            return

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Tải tệp Excel", "", "Excel Files (*.xlsx)"
        )
        
        if not filepath:
            return
        
        try:
            self.statusBar().showMessage("Đang tải file Excel...")
            
            # Load signal
            timestamps, ir, red, detected_fs, duration = SignalLoader.load_excel(filepath)
            
            # Validate
            is_valid, warning = SignalLoader.validate_signal_data(
                timestamps, ir, red, detected_fs, duration,
                min_duration=self.param_panel.get_param("validation.min_duration")
            )
            
            if warning:
                self._show_warning("Cảnh báo kiểm tra dữ liệu", warning)
            
            # Create SignalData
            self.signal_data = SignalData(timestamps, ir, red, detected_fs)
            
            # Update file info display
            filename = Path(filepath).name
            self.lbl_filename.setText(filename)
            self.lbl_filemeta.setText(
                f"3 cột · {self.signal_data.num_samples:,} mẫu · "
                f"Fs = {self.signal_data.fs:.0f} Hz (tự phát hiện)"
            )

            self._show_status()
            
            # Enable analysis button
            self._set_busy_state(False)
            
            # Plot raw signal
            self.plot_widget.plot_raw_signal(
                self.signal_data.timestamp, self.signal_data.ir, self.signal_data.red
            )
            
            self._show_status(f"Đã tải: {filename}")
            
        except Exception as e:
            self._show_error("Lỗi tải tệp", str(e))
            self.statusBar().showMessage("Lỗi tải tệp")

    def _on_run_analysis(self):
        """Handle Run Analysis button click."""
        if self.signal_data is None:
            self._show_warning("Chưa có dữ liệu", "Vui lòng tải tệp Excel trước")
            return
        if self.analysis_thread is not None and self.analysis_thread.isRunning():
            self._show_warning("Đang phân tích", "Phân tích đang chạy. Vui lòng chờ hoàn tất.")
            return
        
        # Validate parameters
        params = self.param_panel.get_parameters()
        errors = self.preset_manager.validate_params(params)
        
        if errors:
            self._show_error("Thông số không hợp lệ", "Kiểm tra thông số thất bại:\n" + "\n".join(errors))
            return
        
        # Disable controls and show progress
        self._set_busy_state(True)
        self.statusBar().showMessage("Đang phân tích dữ liệu...")
        
        # Start analysis in background thread
        self.analysis_thread = AnalysisThread(self.signal_data, params)
        self.analysis_thread.finished.connect(self._on_analysis_finished)
        self.analysis_thread.error.connect(self._on_analysis_error)
        self.analysis_thread.progress.connect(self._show_status)
        self.analysis_thread.start()

    def _on_analysis_finished(self, results):
        """Handle analysis completion."""
        self.current_results = results
        
        # Update plots
        self.plot_widget.plot_results(self.signal_data, results)
        self.plot_widget.show_filtered_view()
        
        # Update results panel
        self.results_panel.display_results(results)
        
        # Restore UI
        self.analysis_thread = None
        self._set_busy_state(False)
        
        elapsed = results.get("processing_info", {}).get("elapsed_time_s", 0)
        if results.get("error"):
            self._show_warning("Phân tích có lỗi", str(results["error"]))
        self._show_status(f"Phân tích hoàn tất ({elapsed:.2f} giây)")

    def _on_analysis_error(self, error_msg):
        """Handle analysis error."""
        self._show_error("Lỗi phân tích", error_msg)

        self.analysis_thread = None
        self._set_busy_state(False)
        self.statusBar().showMessage("Phân tích thất bại")

    def _on_reset_defaults(self):
        """Reset parameters to defaults."""
        try:
            defaults = self.preset_manager.load_defaults()
            self.param_panel.set_parameters(defaults)
            self.current_preset_name = "mặc định"
            self._show_status("Đã đặt lại thông số về mặc định")
        except Exception as e:
            self._show_error("Lỗi", f"Không thể tải mặc định: {e}")

    def _on_save_preset(self):
        """Save current parameters as preset."""
        params = self.param_panel.get_parameters()
        
        # Validate
        errors = self.preset_manager.validate_params(params)
        if errors:
            self._show_warning("Thông số không hợp lệ", "Không thể lưu cấu hình không hợp lệ:\n" + "\n".join(errors))
            return
        
        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Lưu cấu hình", "", "JSON Files (*.json)"
            )
            
            if filepath:
                self.preset_manager.save_preset(params, filepath)
                self.current_preset_name = Path(filepath).stem
                self._show_status(f"Đã lưu cấu hình: {Path(filepath).name}")
        except Exception as e:
            self._show_error("Lỗi", f"Không thể lưu cấu hình: {e}")

    def _on_about(self):
        """Show about dialog."""
        self._show_info(
            "Giới thiệu PPG Signal Analyzer",
            "PPG Signal Analyzer v1.0.0\n\n"
            "Ứng dụng desktop để phân tích tín hiệu quang thể tích đồ (PPG)\n"
            "và trích xuất 5 chỉ số sinh học: HR, SpO2, RR, HRV và PI.\n\n"
            "© 2024"
        )

    def closeEvent(self, event):
        """Handle window close - save last-used preset."""
        if self.analysis_thread is not None and self.analysis_thread.isRunning():
            self.analysis_thread.requestInterruption()
            self.analysis_thread.quit()
            if not self.analysis_thread.wait(2000):
                self.analysis_thread.terminate()
                self.analysis_thread.wait()

        try:
            params = self.param_panel.get_parameters()
            self.preset_manager.save_last_used(params)
        except Exception:
            pass
        
        event.accept()
