from matplotlib import pyplot as plt
import numpy as np
from scipy import signal

from basic_DSP.signal_gen import generate_signal


def plot_window_comparison():
    # Dùng cùng tín hiệu thử nghiệm để so sánh công bằng giữa các loại cửa sổ
    t, clean_signal, noisy_signal, fs = generate_signal()

    numtaps = 40
    cutoff = 10.0

    window_configs = [
        ("Chữ nhật", "boxcar", "tab:blue"),
        ("Hamming", "hamming", "tab:red"),
        ("Hanning", "hann", "tab:green"),
        ("Blackman", "blackman", "tab:orange"),
    ]

    fir_coefficients = {}
    filtered_signals = {}
    frequency_responses = {}

    for display_name, scipy_window_name, _ in window_configs:
        coeffs = signal.firwin(numtaps, cutoff, window=scipy_window_name, fs=fs)
        fir_coefficients[display_name] = coeffs
        filtered_signals[display_name] = signal.lfilter(coeffs, 1.0, noisy_signal)

        frequencies, response = signal.freqz(coeffs, worN=4096, fs=fs)
        magnitude_db = 20 * np.log10(np.maximum(np.abs(response), 1e-12))
        frequency_responses[display_name] = (frequencies, magnitude_db)

    plt.figure(figsize=(12, 12))

    # Bảng 1: So sánh hệ số h[n] của 4 loại cửa sổ FIR
    plt.subplot(3, 1, 1)
    for display_name, _, color in window_configs:
        plt.plot(fir_coefficients[display_name], label=display_name, color=color, linewidth=2)

    plt.title("Bảng 1 - Hệ số bộ lọc FIR h[n] theo từng kiểu cửa sổ", pad=8, fontsize=10)
    plt.xlabel("Chỉ số mẫu n", fontsize=8)
    plt.ylabel("Biên độ h[n]", fontsize=8)
    plt.legend()
    plt.grid(True)

    # Bảng 2: So sánh đáp ứng tần số biên độ theo dB
    plt.subplot(3, 1, 2)
    for display_name, _, color in window_configs:
        frequencies, magnitude_db = frequency_responses[display_name]
        plt.plot(frequencies, magnitude_db, label=display_name, color=color, linewidth=2)

    plt.title("Bảng 2 - Đáp ứng tần số |H(f)| theo dB", pad=8, fontsize=10)
    plt.xlabel("Tần số (Hz)", fontsize=8)
    plt.ylabel("Biên độ (dB)", fontsize=8)
    plt.legend()
    plt.grid(True)
    plt.xlim(0, fs / 2)
    plt.ylim(-120, 10)

    # Bảng 3: So sánh tín hiệu sau lọc theo thời gian
    plt.subplot(3, 1, 3)
    plt.plot(t, noisy_signal, label="Tín hiệu nhiễu đầu vào", color="lightgray", linewidth=1.5)
    plt.plot(t, clean_signal, label="Tín hiệu sạch tham chiếu", color="cyan", linestyle="dashed", linewidth=2)

    for display_name, _, color in window_configs:
        plt.plot(t, filtered_signals[display_name], label=f"Sau lọc FIR - {display_name}", color=color, linewidth=2)

    plt.title("Bảng 3 - So sánh tín hiệu sau lọc theo từng kiểu cửa sổ", pad=8, fontsize=10)
    plt.xlabel("Thời gian (giây)", fontsize=8)
    plt.ylabel("Biên độ", fontsize=8)
    plt.legend()
    plt.grid(True)
    plt.xlim(0, 0.5)

    plt.tight_layout(h_pad=2)
    plt.show()


if __name__ == "__main__":
    plot_window_comparison()
