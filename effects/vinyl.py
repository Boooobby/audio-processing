import numpy as np
from pedalboard import Pedalboard, LowpassFilter, HighpassFilter, Gain, Chorus, Distortion, PeakFilter
from .base import AudioEffect

class VinylStyle(AudioEffect):
    def __init__(self, crackle_amount=0.0005, hiss_level=0.002, wow_amount=0.1):
        super().__init__("Vinyl Record Style")
        self.crackle_amount = crackle_amount
        self.hiss_level = hiss_level  # 持续的底噪大小
        self.wow_amount = wow_amount  # 唱片转速不稳的程度 (0.0 - 1.0)

    def generate_colored_noise(self, shape, color='pink'):
        """生成有色噪声模拟唱片底噪 (简化版)"""
        noise = np.random.normal(0, 1, shape)
        if color == 'pink' or color == 'brown':
            # 简单的累积求和模拟布朗噪声，比白噪声听起来更像低频轰隆声
            noise = np.cumsum(noise, axis=0) 
            # 归一化防止溢出
            noise = noise / (np.max(np.abs(noise)) + 1e-9)
        return noise

    def process(self, audio, samplerate):
        # 1. 模拟物理缺陷：抖动
        # 使用 Mix=1.0 的 Chorus 效果来模拟音高微小的波动
        # 这种波动模仿了唱片不平整或转速微小变化带来的“晃动感”
        wow_effect = Chorus(
            rate_hz=0.8,              # 慢速晃动
            depth=self.wow_amount,    # 晃动深度
            centre_delay_ms=2.0,
            feedback=0.0,
            mix=1.0                   # 全湿信号，只听变调后的声音
        )
        
        # 2. 模拟模拟设备的“温暖感”：饱和度与EQ
        # 温暖感 = 轻微失真 + 中低频提升 + 高频平滑滚降
        analog_chain = Pedalboard([
            # 2.1 饱和度
            # 模拟电子管或磁带的非线性失真，增加谐波，让声音变“厚”
            Distortion(drive_db=5.0), 

            # 2.2 频响修正
            # 提升 200Hz-500Hz 区域增加厚度
            PeakFilter(cutoff_frequency_hz=300, gain_db=3.0, q=0.5),
            # 滚降超低频
            HighpassFilter(cutoff_frequency_hz=40),
            # 平滑高频 
            LowpassFilter(cutoff_frequency_hz=12000), 
        ])

        # 应用效果链
        board = Pedalboard([wow_effect, *analog_chain])
        audio_processed = board(audio, samplerate)

        # 3. 模拟物理噪声层
        
        # 3.1 持续底噪
        # 生成稍微偏低频的噪声，而非刺耳的白噪声
        noise_floor = self.generate_colored_noise(audio.shape, color='brown') * self.hiss_level
        
        # 3.2 爆豆/划痕 
        # 保持你的 Numpy 逻辑，但稍微稀疏一点，因为真实的爆豆不是持续的
        crackle = np.zeros_like(audio)
        indices = np.random.rand(*audio.shape) < self.crackle_amount
        # 爆豆通常只有一边声道或者两边不对称
        crackle[indices] = np.random.uniform(-0.15, 0.15, np.sum(indices))
        
        # 混合所有信号
        # 原始音频经过处理 + 底噪 + 爆豆
        final_audio = audio_processed + noise_floor + crackle
        
        return final_audio
    