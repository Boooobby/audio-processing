import numpy as np
from pedalboard import Pedalboard, LowpassFilter
from .base import AudioEffect

class AliasingStyle(AudioEffect):
    """
    采样率变换与混叠效应
    """
    def __init__(self, target_samplerate=4000, obey_nyquist=False):
        status = "Clean/Filtered" if obey_nyquist else "Distorted/Aliased"
        super().__init__(f"Resampler ({target_samplerate}Hz) [{status}]")
        self.target_sr = target_samplerate
        self.obey_nyquist = obey_nyquist

    def process(self, audio, samplerate):
        if self.target_sr >= samplerate:
            return audio

        # 1. 抗混叠滤波 - 输入端
        audio_to_process = audio
        if self.obey_nyquist:
            nyquist_freq = self.target_sr / 2
            # 留一点余量 (*0.9)
            board = Pedalboard([LowpassFilter(cutoff_frequency_hz=nyquist_freq * 0.9)])
            audio_to_process = board(audio, samplerate)

        # 2. 降采样 - 模拟 ADC
        step = int(samplerate / self.target_sr)
        if step <= 1: return audio
        downsampled = audio_to_process[..., ::step]

        # 3. 零阶保持插值 - 模拟 DAC
        audio_restored = np.repeat(downsampled, step, axis=-1)

        # 对齐
        original_length = audio.shape[-1]
        current_length = audio_restored.shape[-1]
        if current_length > original_length:
            audio_restored = audio_restored[..., :original_length]
        elif current_length < original_length:
            padding = original_length - current_length
            pad_width = [(0, 0)] * (audio.ndim - 1) + [(0, padding)]
            audio_restored = np.pad(audio_restored, pad_width, mode='edge')

        # 4. 重建滤波 - 输出端
        if self.obey_nyquist:
            nyquist_freq = self.target_sr / 2
            # 再次滤波
            board_recon = Pedalboard([LowpassFilter(cutoff_frequency_hz=nyquist_freq * 0.9)])
            audio_restored = board_recon(audio_restored, samplerate)

        return audio_restored