"""
PPG Signal Analyzer - Main Application

Desktop application for analyzing photoplethysmography (PPG) signals from Excel files.
Extracts 5 biometric metrics: HR, SpO2, RR, HRV, and PI.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #F5F6FA;
    color: #263238;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 12px;
}
QWidget#left_panel, QWidget#right_panel {
    background-color: #FFFFFF;
}
QWidget#plot_area {
    background-color: #FFFFFF;
}
QWidget#topbar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E0E4EC;
}
QLabel#section_label {
    color: #78909C;
    font-size: 10px;
    font-weight: bold;
}
QLabel#group_label {
    color: #90A4AE;
    font-size: 10px;
    font-weight: bold;
    border-top: 1px solid #ECEFF1;
    padding-top: 6px;
}
QDoubleSpinBox, QSpinBox {
    border: 1px solid #C5CAE9;
    border-radius: 4px;
    padding: 2px 4px;
    background: #FFFFFF;
    color: #1A237E;
    font-weight: bold;
    max-width: 62px;
}
QPushButton#metric_tab {
    border: none;
    background: transparent;
    color: #5C6BC0;
    padding: 3px 10px;
    border-radius: 4px;
    font-size: 11px;
}
QPushButton#metric_tab:checked {
    background: #3949AB;
    color: #FFFFFF;
}
QPushButton#metric_tab:hover:!checked {
    background: #E8EAF6;
}
QPushButton#view_toggle {
    border: none;
    background: transparent;
    color: #90A4AE;
    padding: 4px 12px;
    border-bottom: 2px solid transparent;
    font-size: 11px;
}
QPushButton#view_toggle:checked {
    color: #3949AB;
    border-bottom: 2px solid #3949AB;
}
QPushButton#view_toggle:hover:!checked {
    color: #5C6BC0;
}
QPushButton#btn_run {
    background: #3949AB;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-size: 12px;
    font-weight: bold;
}
QPushButton#btn_run:hover { background: #283593; }
QPushButton#btn_run:disabled { background: #9FA8DA; }
QPushButton#btn_normal {
    background: #FFFFFF;
    color: #3949AB;
    border: 1px solid #C5CAE9;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
}
QPushButton#btn_normal:hover { background: #E8EAF6; }
QPushButton#btn_normal:disabled { color: #B0BEC5; border-color: #E0E4EC; }
QPushButton#btn_reset {
    background: #FFFFFF;
    color: #C62828;
    border: 1px solid #EF9A9A;
    border-radius: 6px;
    padding: 6px 0;
    font-size: 11px;
}
QPushButton#btn_reset:hover { background: #FFEBEE; }
QPushButton#btn_save {
    background: #FFFFFF;
    color: #2E7D32;
    border: 1px solid #A5D6A7;
    border-radius: 6px;
    padding: 6px 0;
    font-size: 11px;
}
QPushButton#btn_save:hover { background: #E8F5E9; }
QStatusBar {
    background: #ECEFF1;
    color: #546E7A;
    font-size: 10px;
    border-top: 1px solid #CFD8DC;
}
QFrame#file_card {
    background: #F0F4FF;
    border: 1px solid #C5CAE9;
    border-radius: 8px;
}
QFrame#metric_card {
    background: #F8F9FE;
    border: 1px solid #E8EEF8;
    border-radius: 8px;
}
"""
 

def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    
    
    # Set application metadata
    app.setApplicationName("PPG Signal Analyzer")
    app.setApplicationVersion("1.0.0")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
