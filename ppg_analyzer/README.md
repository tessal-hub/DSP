# PPG Signal Analyzer

Desktop application for photoplethysmography (PPG) signal analysis and biometric extraction.

> This project is standardized as a **desktop app only** (PyQt6).

## App Overview

PPG Signal Analyzer is a desktop tool for quickly loading PPG Excel files, tuning processing parameters, and viewing analysis results in one screen.

- **Left panel**: input file info + parameter controls
- **Center panel**: signal plots (raw / filtered / peaks / artifacts)
- **Right panel**: metric cards (HR, SpO2, RR, HRV, PI) with quality status

Typical workflow in app:
1. Load Excel file (`Timestamp`, `IR`, `Red`)
2. Adjust parameters in tabs
3. Click **Run Analysis**
4. App auto-switches to **Filtered** plot view, while **Raw** tab still keeps original raw data

## Features

- **5 Biometric Metrics**: Heart Rate (HR/BPM), Blood Oxygen (SpO2), Respiration Rate (RR), Heart Rate Variability (HRV), and Perfusion Index (PI)
- **Fully Configurable**: All signal processing parameters are user-adjustable via UI sliders and spinboxes
- **Advanced Signal Processing**: IIR filters (Butterworth), peak detection, and motion artifact detection
- **Real-time Validation**: Parameter validation, signal quality assessment, and artifact detection
- **Preset System**: Save and load parameter configurations as JSON presets
- **Interactive Plots**: Visualize raw, filtered, peak detection, and artifact regions

## Installation

### Requirements

- Python 3.8+
- PyQt6
- numpy, scipy, pandas
- openpyxl, matplotlib

### Setup

1. **Install dependencies**:

```bash
cd ppg_analyzer
pip install -r requirements.txt
```

2. **Run the application**:

```bash
python main.py
```

## Quick Start

1. **Load Excel File**: Click "Load Excel" and select a file with columns: Timestamp, IR, Red
2. **Configure Parameters**: Adjust filter settings, thresholds, and validation parameters in tabs
3. **Run Analysis**: Click "Run Analysis" to process the signal
4. **View Results**: Check metric values and quality indicators in the right panel

## Parameter Configuration

All parameters are configurable and organized by metric:

- **HR Tab**: Highpass/lowpass filters, peak detection thresholds
- **SpO2 Tab**: Bandpass filter, R-ratio validation, calibration coefficients
- **RR Tab**: Lowpass filter for respiratory baseline extraction
- **HRV Tab**: Analysis duration, stress classification thresholds
- **PI Tab**: AC/DC processing parameters
- **Warning Tab**: Sampling rate checks, minimum duration, and warning thresholds

## File Format

Input Excel file must contain 3 columns (case-insensitive):

- **Timestamp** (or Time, Time_s): Time in seconds
- **IR** (or Infrared): Infrared channel signal
- **Red** (or Red_Channel): Red channel signal

Example:

```
Timestamp | IR    | Red
0.0       | 100.5 | 85.2
0.01      | 101.2 | 84.9
0.02      | 102.1 | 85.5
...
```

## Architecture

```
ppg_analyzer/
├── main.py                     # App entry point
├── requirements.txt            # Python dependencies
├── presets/
│   ├── default.json           # Default parameters
│   └── user_presets/          # User-saved presets
├── core/
│   ├── preset_manager.py      # Preset I/O and validation
│   ├── filters.py             # IIR/FIR filter implementations
│   ├── peak_detector.py       # Peak finding algorithms
│   ├── artifact_detector.py   # Motion artifact detection
│   ├── excel_io.py            # Excel loading and SignalData model
│   ├── signal_processor.py    # Main analysis orchestrator
│   └── metrics/               # Analysis modules
│       ├── hr.py              # Heart rate analysis
│       ├── spo2.py            # Blood oxygen analysis
│       ├── rr.py              # Respiration rate analysis
│       ├── hrv.py             # Heart rate variability
│       └── pi.py              # Perfusion index
├── ui/
│   ├── main_window.py         # Main PyQt6 window
│   ├── param_panel.py         # Configurable parameter sliders
│   ├── plot_widget.py         # Matplotlib canvas
│   ├── results_panel.py       # Results display with quality badges
│   ├── analysis_thread.py     # Background processing thread
│   └── __init__.py            # UI package marker
└── README.md                  # Usage documentation
```

## Key Algorithms

### Heart Rate (HR/BPM)

- IIR highpass filter (0.5 Hz) to remove baseline wander
- IIR lowpass filter (4.5 Hz) to remove noise
- Peak detection on filtered IR signal
- BPM = 60 / mean(beat intervals)

### Blood Oxygen (SpO2)

- IIR bandpass filter (0.8-4.0 Hz) on Red and IR channels
- Extract AC (RMS of bandpassed) and DC (mean of lowpassed)
- R-ratio = (AC_Red/DC_Red) / (AC_IR/DC_IR)
- SpO2 = 104 - 17 × R (calibration formula)

### Respiration Rate (RR)

- IIR lowpass filter (0.4 Hz, high order) to isolate respiratory baseline
- Peak detection on lowpass-filtered IR signal with large spacing (3-6 seconds)
- RR = 60 / mean(respiratory intervals)

### Heart Rate Variability (HRV)

- Extract N-N intervals (beat-to-beat times) from HR peaks
- SDNN = Standard deviation of N-N intervals
- RMSSD = Root mean square of successive differences
- Stress classification based on RMSSD thresholds

### Perfusion Index (PI)

- PI = (AC_IR / DC_IR) × 100%
- Signal quality indicator: PI < 0.5% = weak signal

## Quality Indicators

Results include quality assessment:

- **Good**: Metric computed reliably in physiological range
- **Warning**: Metric computed but with some concerns
- **Poor**: Metric unreliable or out of range

## Troubleshooting

### "Invalid sampling rate" error

- Ensure timestamp column contains time in **seconds** (not milliseconds or datetime)
- Check that timestamps are monotonically increasing

### Low quality results

- Verify sensor placement and hand position
- Ensure minimum signal duration (120 seconds recommended)
- Check for motion artifacts (shown in "Artifacts" tab)
- Adjust filter parameters in UI

### Memory issues with large files

- Maximum recommended: 10 hours continuous recording at 100 Hz
- For longer recordings, process in segments

## License

© 2024

## Support

For issues or feature requests, refer to the project documentation.
