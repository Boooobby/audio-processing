import numpy as np
from .base import AudioEffect


class CompandingStyle(AudioEffect):
    """
    非均匀量化 (A-law Companding)
    模拟电话系统 (PCM-30/32) 中的 A律 压扩技术。
    流程: 信号 -> A律压缩 -> 均匀量化 -> A律扩张 -> 恢复信号
    """

    def __init__(self, bit_depth=8, A=87.6, enable_companding=True):
        """
        :param bit_depth: 量化比特深度 (通常电话系统为8bit)
        :param A: A律参数 (欧洲/中国标准 A=87.6)
        :param enable_companding:
            True  = 开启 A律 (非均匀量化)
            False = 关闭 A律 (退化为普通的线性/均匀量化)
        """
        status = "A-law (Non-Linear)" if enable_companding else "Linear (Uniform)"
        super().__init__(f"PCM {bit_depth}-bit [{status}]")

        self.levels = 2 ** bit_depth
        self.A = A
        self.enable_companding = enable_companding

    def _a_law_compress(self, x):
        """A律压缩公式 (F(x))"""
        # 避免修改原数组
        x = x.copy()

        # 1. 获取符号和绝对值
        sign = np.sign(x)
        abs_x = np.abs(x)

        # 2. 准备输出数组
        y = np.zeros_like(x)

        # 3. 分段函数条件
        # A律标准: 1 + ln(A)
        denom = 1 + np.log(self.A)

        # 情况1: |x| < 1/A (小信号线性放大)
        mask_small = abs_x < (1 / self.A)
        y[mask_small] = (self.A * abs_x[mask_small]) / denom

        # 情况2: 1/A <= |x| <= 1 (大信号对数压缩)
        mask_large = ~mask_small
        y[mask_large] = (1 + np.log(self.A * abs_x[mask_large])) / denom

        return sign * y

    def _a_law_expand(self, y):
        """A律扩张公式 (F^-1(y)) - 压缩的逆运算"""
        y = y.copy()
        sign = np.sign(y)
        abs_y = np.abs(y)
        x = np.zeros_like(y)

        denom = 1 + np.log(self.A)
        threshold = 1 / denom

        # 情况1: 还原小信号
        mask_small = abs_y < threshold
        x[mask_small] = (abs_y[mask_small] * denom) / self.A

        # 情况2: 还原大信号
        mask_large = ~mask_small
        x[mask_large] = np.exp(abs_y[mask_large] * denom - 1) / self.A

        return sign * x

    def process(self, audio, samplerate):
        # 0. 归一化输入防止越界
        max_val = np.max(np.abs(audio))
        if max_val > 1.0:
            audio = audio / max_val

        signal = audio

        # 1. 压缩 (Compression)
        if self.enable_companding:
            signal = self._a_law_compress(signal)

        # 2. 核心：量化 (Quantization)
        # 将连续信号映射到离散台阶上。这会产生“量化噪声”。
        # 只有在这一步损失精度，压扩才有意义。
        # 映射到 [0, 1] -> floor -> 归一化回 [-1, 1]
        signal = (signal + 1.0) / 2.0
        signal = np.floor(signal * self.levels) / self.levels
        signal = signal * 2.0 - 1.0

        # 3. 扩张 (Expansion)
        if self.enable_companding:
            signal = self._a_law_expand(signal)

        return signal