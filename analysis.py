import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq

# 设置绘图风格，bmh 比较适合科研数据展示
plt.style.use('bmh')


class AudioAnalyzer:
    @staticmethod
    def calculate_snr(original, processed):
        """
        计算信噪比 (Signal-to-Noise Ratio)
        """
        # 1. 维度处理 (确保是单声道)
        if len(original.shape) > 1: original = original[0]
        if len(processed.shape) > 1: processed = processed[0]

        # 2. 长度对齐 (取交集)
        min_len = min(len(original), len(processed))
        org = original[:min_len]
        proc = processed[:min_len]

        # 3. 计算噪声成分
        # 噪声 = 原始信号 - 处理后信号
        noise = org - proc

        # 4. 计算功率 (Power)
        # 转换为 float64 防止溢出
        p_signal = np.sum(org.astype(np.float64) ** 2)
        p_noise = np.sum(noise.astype(np.float64) ** 2)

        # 5. 防止除以零
        if p_noise < 1e-10:
            return float('inf')  # 无噪声

        snr = 10 * np.log10(p_signal / p_noise)
        return snr

    @staticmethod
    def plot_comparison(original, processed, samplerate, title="Analysis", filename="analysis.png"):
        """
        绘制分析图：
        - 上图：处理后信号的声纹图 (Spectrogram) -> 用来看“画中音”和频谱变化
        - 下图：时域波形细节对比 (Waveform) -> 用来看量化阶梯和混叠形状
        """
        # === 数据预处理 ===
        if len(original.shape) > 1: original = original[0]
        if len(processed.shape) > 1: processed = processed[0]

        # 长度对齐
        min_len = min(len(original), len(processed))
        org = original[:min_len]
        proc = processed[:min_len]

        # 创建画布
        fig, axes = plt.subplots(2, 1, figsize=(12, 10))

        # ==========================================
        # Subplot 1: 声纹图 (Spectrogram) - 核心修改
        # ==========================================
        ax1 = axes[0]
        ax1.set_title(f"Spectrogram Analysis: {title}", fontsize=12, fontweight='bold')

        # 绘制声纹图
        # NFFT: 窗口大小，决定频率分辨率 (1024是一个平衡值)
        # noverlap: 重叠部分，让图像更平滑
        # cmap='inferno': 黑底->火红->亮黄，最适合显示隐藏图片
        Pxx, freqs, bins, im = ax1.specgram(
            proc,
            NFFT=1024,
            Fs=samplerate,
            noverlap=512,
            cmap='inferno'
        )

        ax1.set_ylabel("Frequency (Hz)")
        ax1.set_xlabel("Time (s)")

        # 添加颜色条 (显示音量/能量强度)
        cbar = plt.colorbar(im, ax=ax1)
        cbar.set_label('Intensity (dB)')

        # ==========================================
        # Subplot 2: 时域波形细节 (Waveform Zoom)
        # ==========================================
        ax2 = axes[1]

        # 为了看清细节，只截取中间的一小段 (50ms)
        window_ms = 50
        window_samples = int((window_ms / 1000) * samplerate)

        mid_point = len(proc) // 2
        start = max(0, mid_point - window_samples // 2)
        end = min(len(proc), mid_point + window_samples // 2)

        # 生成时间轴 (毫秒)
        time_axis = np.linspace(0, (end - start) / samplerate * 1000, end - start)

        ax2.set_title(f"Waveform Detail ({window_ms}ms Zoom-in)")

        # 原始信号 (虚线背景)
        ax2.plot(time_axis, org[start:end], color='gray', linestyle='--', alpha=0.6, label='Original Input',
                 linewidth=1)
        # 处理后信号 (实线前景)
        ax2.plot(time_axis, proc[start:end], color='#007acc', alpha=0.9, label='Processed Output', linewidth=1.5)

        ax2.set_xlabel("Time (ms)")
        ax2.set_ylabel("Amplitude")
        ax2.legend(loc='upper right')

        # 限制纵坐标范围，防止极大值破坏视图
        ax2.set_ylim(-1.1, 1.1)

        # === 保存 ===
        plt.tight_layout()
        try:
            plt.savefig(filename, dpi=150)
            print(f"📊 [Visual] 分析图表已保存至: {filename}")
        except Exception as e:
            print(f"⚠️ 保存图表失败: {e}")
        finally:
            plt.close()