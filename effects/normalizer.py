import numpy as np
from .base import AudioEffect

class Normalizer(AudioEffect):
    def __init__(self, target_db=-1.0):
        super().__init__("Safety Normalizer")
        self.target_factor = 10 ** (target_db / 20) # dB转线性幅度

    def process(self, audio, samplerate):
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            return audio / max_val * self.target_factor
        return audio
