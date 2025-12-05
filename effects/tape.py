from pedalboard import Pedalboard, Chorus, Distortion, LowpassFilter, Compressor
from .base import AudioEffect

class TapeStyle(AudioEffect):
    def __init__(self, flutter=0.15, drive=3):
        super().__init__("Vintage Tape Style")
        self.flutter = flutter
        self.drive = drive

    def process(self, audio, samplerate):
        board = Pedalboard([
            Compressor(threshold_db=-10, ratio=2.5),
            Chorus(rate_hz=1.5, depth=self.flutter, mix=0.5),
            Distortion(drive_db=self.drive),
            LowpassFilter(cutoff_frequency_hz=12000),
        ])
        return board(audio, samplerate)
