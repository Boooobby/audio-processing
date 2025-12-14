import numpy as np
from PIL import Image, ImageOps
from scipy.signal import istft
from .base import AudioEffect


class SpectrogramArtStyle(AudioEffect):
    """
     频谱画中音
    原理：利用 ISTFT 将图像的像素亮度映射为声音频谱的幅度。
    图像的Y轴对应频率，X轴对应时间。
    注意：此效果会忽略输入音频，直接根据图片生成新的音频。
    """

    def __init__(self, image_path, duration=5.0):
        """
        :param image_path: 图片路径 (建议黑底白字或简单线条图，效果最好)
        :param duration: 生成音频的目标时长 (秒)
        """
        super().__init__("Spectrogram Art Generator")
        self.image_path = image_path
        self.duration = duration
        # FFT窗口大小，决定了图片的高度分辨率
        self.n_fft = 2048
        # 步长，决定了横向时间分辨率
        self.hop_length = self.n_fft // 4

    def process(self, audio, samplerate):
        print(f" [SpectrogramArt] 正在尝试将图片 '{self.image_path}' 转换为音频...")

        # 1. 读取图片并转为灰度图 (L模式)
        try:
            img = Image.open(self.image_path).convert('L')
        except Exception as e:
            print(f"❌ [Error] 无法读取图片: {e}")
            # 如果失败，返回静音信号以免程序崩溃
            return np.zeros_like(audio)

        # 2. 计算目标尺寸
        # 图片高度必须对应 FFT 的正频率频点数 (n_fft // 2 + 1)
        target_height = self.n_fft // 2 + 1
        # 图片宽度决定了音频时长：总采样点数 / 步长
        target_width = int((self.duration * samplerate) / self.hop_length)

        # 3. 调整图片
        # 使用 BICUBIC 插值缩放，保证线条平滑
        img = img.resize((target_width, target_height), Image.Resampling.BICUBIC)
        # 重要：频谱图通常低频在下，图片坐标0在顶部，需要垂直翻转
        img = ImageOps.flip(img)

        # 4. 转为数值矩阵并归一化
        # pixels 矩阵代表了频谱的幅度 (Magnitude)
        pixels = np.array(img) / 255.0

        # 5. 构造复数频谱 (STFT矩阵)
        # 我们只有幅度信息，没有相位信息。
        # 为了让生成的频谱图清晰，使用随机相位是最佳实践。
        random_phase = np.random.uniform(0, 2 * np.pi, pixels.shape)
        # 构造复数: Magnitude * e^(j * Phase)
        # 对幅度做一点指数增强 (pixels**2)，提高对比度
        Zxx = (pixels ** 2) * np.exp(1j * random_phase)

        # 6. 逆变换：频域 -> 时域 (ISTFT)
        _, generated_audio = istft(Zxx, fs=samplerate, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)

        # 7. 最终幅度归一化 (防止爆音)
        max_val = np.max(np.abs(generated_audio))
        if max_val > 0:
            # 留一点余量 (* 0.95)
            generated_audio = generated_audio / max_val * 0.95

        # 如果需要立体声，可以复制一份: np.stack([generated_audio, generated_audio])
        # 这里默认生成单声道兼容性更好
        return generated_audio