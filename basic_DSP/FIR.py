import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

from basic_DSP.signal_gen import generate_signal

def FIR ():
    
    numtaps = 40  # Số lượng hệ số của bộ lọc FIR
    cutoff = 10  # Tần số cắt (10 Hz)
    
    # Thiết kế bộ lọc FIR sử dụng phương pháp cửa sổ
    fir_coefficients = signal.firwin(numtaps, cutoff, fs=1000)
    
    # Lấy tín hiệu đã được tạo ra
    t, clean_signal, noisy_signal, fs = generate_signal()
    # Áp dụng bộ lọc FIR cho tín hiệu nhiễu
    
    
    filtered_signal_FIR = signal.lfilter(fir_coefficients, 1.0, noisy_signal)
    ##fir_coefficients: Hệ số của bộ lọc FIR (trọng số của các phần tử trong bộ lọc)
    ##1.0: Hệ số của phần tử phản hồi (feedback) trong bộ lọc (đối với FIR, phần tử này thường là 1.0)
    ##noisy_signal: Tín hiệu đầu vào có nhiễu mà chúng ta muốn lọc
    
    return t, clean_signal, noisy_signal, fs, filtered_signal_FIR