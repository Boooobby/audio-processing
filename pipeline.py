from pedalboard.io import AudioFile

class AudioPipeline:
    def run(self, input_path, output_path, pre_processors=None, main_effects=None):
        """
        :param pre_processors: 清理/预处理对象列表
        :param main_effects: 风格化对象列表
        """
        if pre_processors is None: pre_processors = []
        if main_effects is None: main_effects = []
        
        print(f"🚀 开始处理: {input_path}")
        
        # 1. 读入
        with AudioFile(input_path) as f:
            audio = f.read(f.frames)
            samplerate = f.samplerate

        # 2. 预处理 (Pre-processing)
        pass_count = 1
        for effect in pre_processors:
            print(f"   [{pass_count}] 预处理: {effect.name}")
            audio = effect.process(audio, samplerate)
            pass_count += 1

        # 3. 主效果 (Main Effects)
        for effect in main_effects:
            print(f"   [{pass_count}] 风格化: {effect.name}")
            audio = effect.process(audio, samplerate)
            pass_count += 1
            
        # 4. 写入
        with AudioFile(output_path, 'w', samplerate, audio.shape[0]) as f:
            f.write(audio)
            
        print(f"✅ 完成: {output_path}")