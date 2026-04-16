import numpy as np
import matplotlib.pyplot as plt
from typing import cast
from scipy import signal

from signal_gen import generate_signal

def IIR():
# 1) Lấy dữ liệu mẫu
    t, clean_signal, noisy_signal, fs = generate_signal()

# 2) Cấu hình bộ lọc
    order = 2      # Bậc lọc: càng cao thì dốc lọc càng mạnh
    cutoff = 10.0  # Tần số cắt 10 Hz (giữ thành phần dưới 10 Hz)

    # 3) Thiết kế bộ lọc ở dạng SOS để ổn định số tốt hơn
    # Dùng fs thì cutoff để trực tiếp theo đơn vị Hz (không cần tự chuẩn hóa)
    sos = signal.butter(order, cutoff, btype="low", fs=fs, output="sos")

    # 4) Lọc tín hiệu nhiễu
    filtered_signal_IIR = signal.sosfilt(sos, noisy_signal)

    return t, clean_signal, noisy_signal, fs, filtered_signal_IIR