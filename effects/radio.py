import numpy as np
from pedalboard import Pedalboard, LowpassFilter, HighpassFilter, Distortion
from .base import AudioEffect

class RadioStyle(AudioEffect):
    def __init__(self, noise_level=0.015):
        super().__init__("AM Radio Style")
        self.noise_level = noise_level

    def process(self, audio, samplerate):
        board = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=300),
            LowpassFilter(cutoff_frequency_hz=3400),
            Distortion(drive_db=10)
        ])
        audio = board(audio, samplerate)
        
        # 加性高斯白噪声
        noise = np.random.normal(0, self.noise_level, audio.shape)
        return audio + noise
