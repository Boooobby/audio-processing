import numpy as np
from pedalboard import Pedalboard, LowpassFilter
from .base import AudioEffect

class AliasingStyle(AudioEffect):
    """
     采样率变换与混叠效应
    增加了“重建滤波器”逻辑，让 Safe 模式的波形变平滑，频谱变干净。
    """
    def __init__(self, target_samplerate=4000, obey_nyquist=False):
        status = "Clean/Filtered" if obey_nyquist else "Distorted/Aliased"
        super().__init__(f"Resampler ({target_samplerate}Hz) [{status}]")
        self.target_sr = target_samplerate
        self.obey_nyquist = obey_nyquist

    def process(self, audio, samplerate):
        if self.target_sr >= samplerate:
            return audio

        # 1. 抗混叠滤波 (Anti-aliasing Filter) - 输入端
        # 防止高频信号折叠进低频
        audio_to_process = audio
        if self.obey_nyquist:
            nyquist_freq = self.target_sr / 2
            # 留一点余量 (*0.9) 防止边缘效应
            board = Pedalboard([LowpassFilter(cutoff_frequency_hz=nyquist_freq * 0.9)])
            audio_to_process = board(audio, samplerate)

        # 2. 降采样 (Decimation) - 模拟 ADC
        step = int(samplerate / self.target_sr)
        if step <= 1: return audio
        downsampled = audio_to_process[..., ::step]

        # 3. 零阶保持插值 (Zero-Order Hold) - 模拟 DAC
        # 这一步产生了“台阶”，引入了大量高频镜像噪声
        audio_restored = np.repeat(downsampled, step, axis=-1)

        # 长度对齐
        original_length = audio.shape[-1]
        current_length = audio_restored.shape[-1]
        if current_length > original_length:
            audio_restored = audio_restored[..., :original_length]
        elif current_length < original_length:
            padding = original_length - current_length
            pad_width = [(0, 0)] * (audio.ndim - 1) + [(0, padding)]
            audio_restored = np.pad(audio_restored, pad_width, mode='edge')

        # === [核心新增] 4. 重建滤波 (Reconstruction Filter) - 输出端 ===
        # 只有在“遵守定理”时，我们才做完美的平滑重建
        # 这会将“台阶”磨平变成“波浪”，并消除频谱图上半部分的橙色
        if self.obey_nyquist:
            nyquist_freq = self.target_sr / 2
            # 再次滤波，滤除由 np.repeat 产生的台阶高频噪声
            board_recon = Pedalboard([LowpassFilter(cutoff_frequency_hz=nyquist_freq * 0.9)])
            audio_restored = board_recon(audio_restored, samplerate)

        return audio_restored