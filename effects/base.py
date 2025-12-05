from abc import ABC, abstractmethod

class AudioEffect(ABC):
    """Effect Interface"""
    def __init__(self, name="Unknown Effect"):
        self.name = name

    @abstractmethod
    def process(self, audio, samplerate):
        pass
