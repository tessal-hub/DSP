import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

def generate_signal():
    # Parameters
    fs = 1000  # Sampling frequency
    t = np.arange(0, 1, 1/fs)  # Time vector of 1 second

        # Tín hiệu hữu ích (sóng sin chậm, tần số 5 Hz)
    clean_signal = np.sin(2 * np.pi * 5 * t)

    # Nhiễu (sóng sin nhanh, tần số 150 Hz)
    noise = 0.5 * np.sin(2 * np.pi * 150 * t)

    # Tín hiệu thực tế ta thu được (đã bị nhiễu)
    noisy_signal = clean_signal + noise

    return t, clean_signal, noisy_signal, fs

def generate_signal_2side():
    fs = 200  
    
    # Trục thời gian (0 đến 10 giây)
    t = np.arange(0, 10, 1/fs)
    
    # 1. TÍN HIỆU GỐC (Clean Signal) - Nhịp tim 1.5 Hz
    # Dùng hàm sin cơ bản làm ví dụ
    clean_signal = 1.0 * np.sin(2 * np.pi * 1.5 * t)
    
    # 2. NHIỄU TẦN SỐ THẤP (Low-Frequency Noise) - Nhịp thở 0.2 Hz
    # Biên độ là 2.5 (Lớn hơn tín hiệu gốc làm cho sóng bị trôi dạt)
    low_freq_noise = 3 * np.sin(2 * np.pi * 0.2 * t)
    
    # 3. NHIỄU TẦN SỐ CAO (High-Frequency Noise) - Điện lưới 50 Hz
    # Biên độ là 0.4 (Nhỏ nhưng tạo ra độ xù xì, răng cưa)
    high_freq_noise = 1 * np.sin(2 * np.pi * 50 * t)
    
    # TRỘN TÍN HIỆU (Mix them all together)
    noisy_signal = clean_signal + low_freq_noise + high_freq_noise
    
    return t, clean_signal, noisy_signal, fs