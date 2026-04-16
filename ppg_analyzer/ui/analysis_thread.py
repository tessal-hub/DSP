"""
Background analysis thread for non-blocking signal processing.

Runs the complete analysis pipeline in a separate thread to prevent UI freezing.
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.excel_io import SignalData
from core.signal_processor import SignalProcessor


class AnalysisThread(QThread):
    """Thread for background signal analysis."""

    # Signals
    finished = pyqtSignal(dict)  # Emits results dict
    error = pyqtSignal(str)      # Emits error message
    progress = pyqtSignal(str)   # Emits progress text

    def __init__(self, signal_data: SignalData, params_dict: Dict[str, Any]):
        """
        Initialize analysis thread.

        Args:
            signal_data: SignalData object
            params_dict: Configuration parameters
        """
        super().__init__()
        
        self.signal_data = signal_data
        self.params_dict = params_dict

    def run(self):
        """Execute analysis in background."""
        try:
            self.progress.emit("Bắt đầu phân tích...")
            
            # Create processor and run analysis
            processor = SignalProcessor(self.signal_data, self.params_dict)
            results = processor.run_analysis()
            self.finished.emit(results)
        
        except Exception as e:
            self.error.emit(f"Phân tích thất bại: {str(e)}")
