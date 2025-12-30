from pedalboard.io import AudioFile
import numpy as np

class AudioPipeline:
    def run(self, input_path, output_path, pre_processors=None, main_effects=None):
        if pre_processors is None: pre_processors = []
        if main_effects is None: main_effects = []

        print(f"开始处理: {input_path}")

        # 1. 读入
        with AudioFile(input_path) as f:
            audio = f.read(f.frames)
            samplerate = f.samplerate

        # 2. 预处理
        pass_count = 1
        for effect in pre_processors:
            print(f"   [{pass_count}] 预处理: {effect.name}")
            audio = effect.process(audio, samplerate)
            pass_count += 1

        # 3. 主效果
        for effect in main_effects:
            print(f"   [{pass_count}] 风格化: {effect.name}")
            audio = effect.process(audio, samplerate)
            pass_count += 1

        if len(audio.shape) > 1:
            num_channels = audio.shape[0]
        else:
            num_channels = 1

        with AudioFile(output_path, 'w', samplerate, num_channels) as f:
            f.write(audio)
        # ----------------------------------------------------

        print(f"完成: {output_path}")