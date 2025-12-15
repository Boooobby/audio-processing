import numpy as np
from .base import AudioEffect


class CompandingStyle(AudioEffect):
    """
    非均匀量化 (A-law Companding)
    模拟电话系统 (PCM-30/32) 中的 A律 压扩技术。
    流程: 信号 -> A律压缩 -> 均匀量化 -> A律扩张 -> 恢复信号
    """

    def __init__(self, bit_depth=8, A=87.6, enable_companding=True):
        super().__init__(f"PCM {bit_depth}-bit [A-law={enable_companding}]")
        self.levels = 2 ** bit_depth
        self.A = A
        self.enable_companding = enable_companding

    def _a_law_compress(self, x):
        x = x.copy()
        sign = np.sign(x)
        abs_x = np.abs(x)
        y = np.zeros_like(x)

        denom = 1 + np.log(self.A)
        mask_small = abs_x < (1 / self.A)
        y[mask_small] = (self.A * abs_x[mask_small]) / denom

        mask_large = ~mask_small
        y[mask_large] = (1 + np.log(self.A * abs_x[mask_large])) / denom
        return sign * y

    def _a_law_expand(self, y):
        y = y.copy()
        sign = np.sign(y)
        abs_y = np.abs(y)
        x = np.zeros_like(y)

        denom = 1 + np.log(self.A)
        threshold = 1 / denom

        mask_small = abs_y < threshold
        x[mask_small] = (abs_y[mask_small] * denom) / self.A

        mask_large = ~mask_small
        x[mask_large] = np.exp(abs_y[mask_large] * denom - 1) / self.A
        return sign * x

    def process(self, audio, samplerate):
        # 0. 归一化输入防止越界
        max_val = np.max(np.abs(audio))
        if max_val > 1.0: audio = audio / max_val

        signal = audio

        # 1. 压缩 (Compression)
        if self.enable_companding:
            signal = self._a_law_compress(signal)

        # 2. 量化 (Quantization)
        signal = (signal + 1.0) / 2.0
        signal = np.floor(signal * self.levels) / self.levels
        signal = signal * 2.0 - 1.0

        # 3. 扩张 (Expansion)
        if self.enable_companding:
            signal = self._a_law_expand(signal)

        return signal