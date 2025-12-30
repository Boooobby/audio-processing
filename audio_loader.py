import os
from pathlib import Path
from pydub import AudioSegment
import time

class AudioHandler:
    def __init__(self, temp_dir="temp_audio"):
        """
        初始化音频处理器
        """
        self.temp_dir = Path(temp_dir)
        self._ensure_dir()

    def _ensure_dir(self):
        """确保临时目录存在"""
        if not self.temp_dir.exists():
            self.temp_dir.mkdir(parents=True)

    def convert_mp3_to_wav(self, input_path):
        """
        接收 MP3 文件路径，将其转换为 WAV 格式
        """
        input_path = Path(input_path)
        
        # 1. 基础校验
        if not input_path.exists():
            raise FileNotFoundError(f"找不到文件: {input_path}")
        
        if input_path.suffix.lower() != '.mp3':
            print(f"警告: 输入文件 {input_path.name} 可能不是 MP3，尝试强制读取...")

        print(f"正在处理: {input_path.name} ...")

        try:
            # 2. 使用 pydub 加载音频
            audio = AudioSegment.from_mp3(str(input_path))
            
            # 3. 准备输出路径
            timestamp = int(time.time())
            output_filename = f"{input_path.stem}_{timestamp}.wav"
            output_path = self.temp_dir / output_filename

            # 4. 导出为 WAV
            audio.export(str(output_path), format="wav")
            
            print(f"转换成功: {output_path}")
            return str(output_path.absolute())

        except Exception as e:
            raise RuntimeError(f"音频转换失败: {str(e)}")

# 用于测试
if __name__ == "__main__":
    converter = AudioHandler()
    
    test_file = "test.mp3" 
    
    if not os.path.exists(test_file):
        print("未找到测试文件，正在生成一个静音 MP3 用于测试...")
        AudioSegment.silent(duration=1000).export(test_file, format="mp3")

    try:
        wav_path = converter.convert_mp3_to_wav(test_file)
        print(f"下一步：将 '{wav_path}' 传递给 DSP 处理模块（磁带/黑胶效果）")
    except Exception as e:
        print(f"错误: {e}")