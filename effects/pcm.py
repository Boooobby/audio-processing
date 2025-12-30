import numpy as np
from .base import AudioEffect

class PCMBitcrusherStyle(AudioEffect):
    """
    核心展示 手写 PCM 量化
    模拟降低比特深度带来的量化噪声。
    从 16bit/32bit 降低到 4bit 或 8bit 风格。
    """
    def __init__(self, bit_depth=4):
        super().__init__(f"PCM Quantization ({bit_depth}-bit)")
        self.quantization_levels = 2 ** bit_depth

    def process(self, audio, samplerate):
        audio_normalized = (audio + 1.0) / 2.0
        
        audio_quantized = np.floor(audio_normalized * self.quantization_levels) / self.quantization_levels
        
        return audio_quantized * 2.0 - 1.0
