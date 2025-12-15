import numpy as np
import scipy.signal
from .base import AudioEffect

class ConvolutionReverb(AudioEffect):
    """
    [通信原理核心展示] 卷积混响
    原理：利用 LTI 系统特性，通过与脉冲响应 (IR) 进行卷积，
    将音频“置入”特定的物理空间或设备中。
    """
    def __init__(self, ir_type='spring', mix=0.3):
        super().__init__(f"Convolution Reverb ({ir_type})")
        self.mix = mix
        self.ir = self._generate_synthetic_ir(ir_type)

    def _generate_synthetic_ir(self, ir_type):
        """
        生成模拟的脉冲响应 (IR)。
        在实际项目中，这里应该加载一个真实的 .wav IR 文件。
        """
        sr = 44100
        if ir_type == 'spring':
            # 模拟“弹簧混响”：这是吉他音箱和老式设备常用的，金属感很强
            length_sec = 2.0
            t = np.linspace(0, length_sec, int(sr * length_sec))
            # 载波噪声 * 指数衰减
            noise = np.random.normal(0, 1, len(t))
            # 弹簧特有的“不断反弹”的颤动感 (Chirp)
            chirp = np.sin(2 * np.pi * 50 * t * t) 
            envelope = np.exp(-3 * t) # 衰减包络
            
            ir = noise * chirp * envelope
            
        elif ir_type == 'old_radio':
            # 模拟“小盒子内部反射”：短、闷
            length_sec = 0.2
            t = np.linspace(0, length_sec, int(sr * length_sec))
            noise = np.random.normal(0, 1, len(t))
            # 这是一个低通滤波特性的极短混响
            envelope = np.exp(-20 * t) 
            ir = noise * envelope
            
        # 归一化 IR，防止能量过大
        return ir / np.max(np.abs(ir))

    def process(self, audio, samplerate):
        # audio shape: (2, N) 双声道
        # ir shape: (M,)
        
        # 1. 既然 Scipy 的 fftconvolve 支持多维，我们可以尝试直接卷
        # 但通常建议分声道处理以防止串扰奇怪
        # 为了演示数理原理，可以手动对每个声道做 FFT 卷积
        
        # 使用 Scipy 的 FFT 卷积算法 (自动选择重叠相加法等优化)
        # mode='same' 保证输出长度和输入一致，不会变长
        
        wet_signal_max_len = audio.shape[1]
        wet_channels = []

        for i in range(audio.shape[0]): # 遍历左、右声道
            channel_audio = audio[i]
            
            # 【核心数学操作】 y[n] = x[n] * h[n]
            # 这里实际上执行的是 IFFT( FFT(x) * FFT(h) )
            convolved = scipy.signal.fftconvolve(channel_audio, self.ir, mode='full')
            
            # 裁剪到原始长度 (卷积会让信号变长 IR的长度，形成拖尾)
            # 我们只取前半部分对齐
            wet_channels.append(convolved[:wet_signal_max_len])

        wet_signal = np.array(wet_channels)
        
        # 2. 也是必做的一步：归一化湿信号能量
        # 因为卷积是累加运算，数值会爆炸非常大
        wet_signal = wet_signal / (np.max(np.abs(wet_signal)) + 1e-9)
        
        # 3. 干湿混合 (Dry/Wet Mix)
        # Dry(1-mix) + Wet(mix)
        return audio * (1 - self.mix) + wet_signal * self.mix