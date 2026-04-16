from matplotlib import pyplot as plt

from FIR import FIR
from IIR import IIR
from IIR_2side import IIR_2side

def plot_signals():
    # Bảng 1: so sánh FIR và IIR cơ bản trên cùng tín hiệu nhiễu 1 chiều
    t_fir, clean_signal_basic, noisy_signal_basic, fs_basic, filtered_signal_fir = FIR()
    t_iir, _, _, _, filtered_signal_iir = IIR()

    # Bảng 2: so sánh IIR low-pass và IIR high-pass trên tín hiệu nhiễu 2 phía
    (
        t_two_side,
        clean_signal_two_side,
        noisy_signal_two_side,
        filtered_frequency_signal,
        _,
    ) = IIR_2side()

    plt.figure(figsize=(12, 16))
    
    plt.subplot(2, 1, 1)
    plt.plot(t_fir, noisy_signal_basic, label='Tín hiệu có nhiễu (5Hz + 150Hz)', color='lightgray')

    # Vẽ tín hiệu gốc để so sánh (đứt nét màu xanh dương)
    plt.plot(t_fir, clean_signal_basic, label='Tín hiệu gốc sạch (5Hz)', color='blue', linestyle='dashed', linewidth=2)

    # Vẽ tín hiệu sau khi qua FIR (màu đỏ)
    plt.plot(t_fir, filtered_signal_fir, label='Tín hiệu sau khi lọc FIR (40 taps)', color='red', linewidth=2)

    # Vẽ tín hiệu sau khi qua IIR (màu xanh lá cây)
    plt.plot(t_iir, filtered_signal_iir, label='Tín hiệu sau khi lọc IIR cơ bản (low-pass, 10Hz)', color='green', linewidth=2)

    plt.title('Bảng 1 - So sánh lọc FIR và IIR cơ bản')
    plt.xlabel('Thời gian (giây)')
    plt.ylabel('Biên độ')
    plt.legend()
    plt.grid(True)
    plt.xlim(0, 0.5) # Chỉ hiển thị nửa giây đầu cho dễ nhìn
    
    
    plt.subplot(2, 1, 2)
    # Tham chiếu tín hiệu sạch và tín hiệu nhiễu đầu vào
    plt.plot(t_two_side, clean_signal_two_side, label='Tín hiệu sạch tham chiếu (1.5Hz)', color='cyan', linestyle='dashed', linewidth=1.5)
    plt.plot(t_two_side, noisy_signal_two_side, label='Tín hiệu nhiễu đầu vào (0.2Hz + 50Hz)', color='lightgray', linewidth=1)
    plt.plot(t_two_side, filtered_frequency_signal, label='Tần số sau lọc', color='magenta', linewidth=2)
    
    plt.title('Bảng 2 - IIR gộp low-pass và high-pass trên tín hiệu nhiễu 2 phía')
    plt.xlabel('Thời gian (giây)')
    plt.ylabel('Biên độ')
    plt.legend()
    plt.grid(True)
    plt.xlim(0, 2)  # Hiển thị 2 giây đầu để dễ quan sát đáp ứng lọc
    plt.show()
    
if __name__ == "__main__":
    plot_signals()