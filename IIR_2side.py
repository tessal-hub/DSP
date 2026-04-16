from scipy import signal

from signal_gen import generate_signal_2side

def IIR_2side():
    t, clean_signal, noisy_signal, fs = generate_signal_2side()

    order = 2
    cutoff = 10.0  # Dùng cùng cutoff cho LP/HP để so sánh trực tiếp

    sos_lowpass = signal.butter(order, cutoff, btype="low", fs=fs, output="sos")
    sos_highpass = signal.butter(order, cutoff, btype="high", fs=fs, output="sos")

    noisy_signal_lowpassed = signal.sosfilt(sos_lowpass, noisy_signal)
    noisy_signal_highpassed = signal.sosfilt(sos_highpass, noisy_signal)
    filtered_frequency_signal = noisy_signal_lowpassed + noisy_signal_highpassed

    return t, clean_signal, noisy_signal, filtered_frequency_signal, fs