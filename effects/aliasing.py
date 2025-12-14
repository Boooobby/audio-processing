import numpy as np
from pedalboard import Pedalboard, LowpassFilter
from .base import AudioEffect

class AliasingStyle(AudioEffect):
    """
    [通信原理演示模块] 采样率变换与混叠效应
    支持切换：是否开启抗混叠滤波 (Anti-aliasing Filter)
    """
    def __init__(self, target_samplerate=4000, obey_nyquist=False):
        """
        :param target_samplerate: 目标采样率 (Hz)
        :param obey_nyquist:
            True  = 遵守定理 (先滤波再抽取，声音闷但干净)
            False = 违反定理 (直接抽取，产生金属混叠杂音)
        """
        status = "Clean/Filtered" if obey_nyquist else "Distorted/Aliased"
        super().__init__(f"Resampler ({target_samplerate}Hz) [{status}]")

        self.target_sr = target_samplerate
        self.obey_nyquist = obey_nyquist

    def process(self, audio, samplerate):
        if self.target_sr >= samplerate:
            return audio

        # === 核心切换逻辑 ===
        audio_to_process = audio

        if self.obey_nyquist:
            # 【遵守定理】：加上抗混叠滤波器
            # 截止频率设为目标采样率的一半 (奈奎斯特频率)
            nyquist_freq = self.target_sr / 2

            # 使用 Pedalboard 快速实现高质量滤波
            board = Pedalboard([
                # 留一点余量防止边缘混叠，通常取 0.9 倍或者直接取 /2
                LowpassFilter(cutoff_frequency_hz=nyquist_freq)
            ])
            # 注意：Pedalboard 可能会改变形状，确保维度正确
            audio_to_process = board(audio, samplerate)

        # === 降采样 (Decimation) ===
        # 计算步长
        step = int(samplerate / self.target_sr)
        if step <= 1: return audio

        # 暴力抽取
        downsampled = audio_to_process[..., ::step]

        # === 零阶保持插值 (还原回原长度以便播放) ===
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

        return audio_restored