import numpy as np
import scipy.signal
from .base import AudioEffect

class ConvolutionReverb(AudioEffect):
    """
    核心展示：卷积混响
    原理：利用 LTI 系统特性，通过与脉冲响应进行卷积，
    将音频“置入”特定的物理空间或设备中。
    """
    def __init__(self, ir_type='spring', mix=0.3):
        super().__init__(f"Convolution Reverb ({ir_type})")
        self.mix = mix
        self.ir = self._generate_synthetic_ir(ir_type)

    def _generate_synthetic_ir(self, ir_type):
        """
        生成模拟的脉冲响应
        """
        sr = 44100
        if ir_type == 'spring':
            # 模拟“弹簧混响”
            length_sec = 2.0
            t = np.linspace(0, length_sec, int(sr * length_sec))
            # 载波噪声 * 指数衰减
            noise = np.random.normal(0, 1, len(t))
            # 弹簧特有的“不断反弹”的颤动感
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
            
        # 归一化，防止能量过大
        return ir / np.max(np.abs(ir))

    def process(self, audio, samplerate):
        wet_signal_max_len = audio.shape[1]
        wet_channels = []

        for i in range(audio.shape[0]): # 遍历左、右声道
            channel_audio = audio[i]
            
            # y[n] = x[n] * h[n]
            # 实际上是 IFFT( FFT(x) * FFT(h) )
            convolved = scipy.signal.fftconvolve(channel_audio, self.ir, mode='full')
            
            # 取前半部分对齐
            wet_channels.append(convolved[:wet_signal_max_len])

        wet_signal = np.array(wet_channels)
        
        # 2. 归一化
        wet_signal = wet_signal / (np.max(np.abs(wet_signal)) + 1e-9)
        
        # 3. 混合
        return audio * (1 - self.mix) + wet_signal * self.mix