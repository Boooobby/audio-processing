import numpy as np
from PIL import Image, ImageOps
from scipy.signal import istft
from .base import AudioEffect


class SpectrogramArtStyle(AudioEffect):
    """
    [黑科技] 频谱画中音
    原理：利用 ISTFT 将图像的像素亮度映射为声音频谱的幅度。
    图像的Y轴对应频率，X轴对应时间。
    """

    def __init__(self, image_path, duration=5.0):
        """
        :param image_path: 图片路径
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
        print(f"🎨 [SpectrogramArt] 正在处理图片: {self.image_path}")

        try:
            # 1. 读取图片并转为灰度图 (L模式)
            img = Image.open(self.image_path).convert('L')

            # === [核心修复] 自动反色检测 ===
            # 逻辑：检查左上角第一个像素。如果是亮的(>128)，说明是白底图片。
            # 白底会导致全屏噪音，所以我们需要反转颜色，让背景变黑(静音)。
            first_pixel = img.getpixel((0, 0))
            if first_pixel > 128:
                print("   💡 检测到白底图片，正在自动反色以优化听感...")
                img = ImageOps.invert(img)
            # ==============================

            # 2. 计算目标尺寸
            # 图片高度必须对应 FFT 的正频率频点数 (n_fft // 2 + 1)
            target_height = self.n_fft // 2 + 1
            # 图片宽度决定了音频时长
            target_width = int((self.duration * samplerate) / self.hop_length)

            # 3. 调整图片
            # 使用 BICUBIC 插值缩放，保证线条平滑
            img = img.resize((target_width, target_height), Image.Resampling.BICUBIC)
            # 垂直翻转：因为频谱图低频在下，而图片坐标0在顶部
            img = ImageOps.flip(img)

            # 4. 转为数值矩阵并归一化
            pixels = np.array(img) / 255.0

            # 5. 构造复数频谱 (STFT矩阵)
            # 使用随机相位 (Random Phase) 让图像成像更清晰
            # 对幅度做平方处理 (pixels**2) 增加对比度，让字更清楚，背景更黑
            random_phase = np.random.uniform(0, 2 * np.pi, pixels.shape)
            Zxx = (pixels ** 2) * np.exp(1j * random_phase)

            # 6. 逆变换：频域 -> 时域 (ISTFT)
            _, generated_audio = istft(Zxx, fs=samplerate, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)

            # 7. 最终幅度归一化 (防止爆音)
            max_val = np.max(np.abs(generated_audio))
            if max_val > 0:
                generated_audio = generated_audio / max_val * 0.95

            return generated_audio

        except Exception as e:
            print(f"❌ [Error] 图片处理失败: {e}")
            # 失败时返回静音，防止程序崩溃
            return np.zeros_like(audio)