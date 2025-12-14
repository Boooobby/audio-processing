import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq

# 设置绘图风格
plt.style.use('bmh')


class AudioAnalyzer:
    @staticmethod
    def calculate_snr(original, processed):
        """
        计算信噪比 (Signal-to-Noise Ratio)
        SNR_dB = 10 * log10(P_signal / P_noise)
        """
        # 确保长度一致，取最短
        min_len = min(len(original), len(processed))
        org = original[:min_len]
        proc = processed[:min_len]

        # 噪声信号 = 原始 - 处理后
        noise = org - proc

        # 计算功率 (信号幅度的平方和)
        p_signal = np.sum(org.astype(np.float64) ** 2)
        p_noise = np.sum(noise.astype(np.float64) ** 2)

        # 防止除以零
        if p_noise < 1e-10: return float('inf')

        snr = 10 * np.log10(p_signal / p_noise)
        return snr

    @staticmethod
    def plot_comparison(original, processed, samplerate, title="Analysis Result", filename="analysis_output.png"):
        """
        生成对比图：上图为频谱对比，下图为时域波形细节对比
        """
        # 确保是单声道
        if len(original.shape) > 1: original = original[0]
        if len(processed.shape) > 1: processed = processed[0]

        # 长度对齐
        min_len = min(len(original), len(processed))
        org = original[:min_len]
        proc = processed[:min_len]

        fig, axes = plt.subplots(2, 1, figsize=(12, 10))

        # === 子图1: 频域频谱对比 (Frequency Domain) ===
        def get_fft_magnitude(y, sr):
            n = len(y)
            yf = fft(y)
            xf = fftfreq(n, 1 / sr)
            # 只取正频率部分
            mask = (xf >= 0) & (xf <= sr / 2)
            return xf[mask], 2.0 / n * np.abs(yf[mask])

        x1, y1 = get_fft_magnitude(org, samplerate)
        x2, y2 = get_fft_magnitude(proc, samplerate)

        ax1 = axes[0]
        ax1.set_title(f"Spectrum Comparison: {title}", fontsize=12, fontweight='bold')
        # 使用半透明填充，方便看清重叠部分
        ax1.fill_between(x1, y1, color='green', alpha=0.3, label='Original Input')
        ax1.plot(x1, y1, color='green', alpha=0.6, linewidth=1)
        ax1.fill_between(x2, y2, color='red', alpha=0.3, label='Processed Output')
        ax1.plot(x2, y2, color='red', alpha=0.6, linewidth=1)
        ax1.set_ylabel("Magnitude")
        ax1.set_xlabel("Frequency (Hz)")
        ax1.legend(loc='upper right')
        ax1.grid(True, which='both', linestyle='--')

        # === 子图2: 时域波形细节 (Time Domain Zoom-in) ===
        # 只截取中间很短的一段(例如 30ms)来看看波形细节
        mid_point = len(org) // 2
        window_size = int(0.03 * samplerate)  # 30ms 窗口
        start = mid_point
        end = mid_point + window_size

        # 生成时间轴
        time_axis = np.linspace(0, window_size / samplerate, window_size) * 1000  # 转为毫秒

        ax2 = axes[1]
        ax2.set_title("Waveform Detail (30ms Zoom-in)", fontsize=12)
        # 原始信号用灰色虚线做背景
        ax2.plot(time_axis, org[start:end], color='gray', linestyle='--', alpha=0.5, label='Original')
        # 处理后信号用鲜艳颜色
        ax2.plot(time_axis, proc[start:end], color='blue', alpha=0.8, linewidth=1.5, label='Processed')
        ax2.set_ylabel("Amplitude")
        ax2.set_xlabel("Time (ms)")
        ax2.set_ylim(-1.1, 1.1)  # 固定纵坐标范围
        ax2.legend(loc='upper right')

        plt.tight_layout()
        plt.savefig(filename, dpi=150)
        plt.close()  # 关闭图表释放内存
        print(f"📊 [Analysis] 图表分析已生成: {filename}")