import numpy as np
from pedalboard import Pedalboard, LowpassFilter, HighpassFilter, Gain
from .base import AudioEffect

class VinylStyle(AudioEffect):
    def __init__(self, crackle_amount=0.001):
        super().__init__("Vinyl Record Style")
        self.crackle_amount = crackle_amount

    def process(self, audio, samplerate):
        # 1. 模拟频响
        board = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=30),
            LowpassFilter(cutoff_frequency_hz=10000),
            Gain(gain_db=2)
        ])
        audio = board(audio, samplerate)

        # 2. 模拟爆豆 (Numpy 逻辑)
        noise = np.zeros_like(audio)
        # 生成随机布尔遮罩
        indices = np.random.rand(*audio.shape) < self.crackle_amount
        # 注入脉冲噪声
        noise[indices] = np.random.uniform(-0.1, 0.1, np.sum(indices))
        
        return audio + noise
