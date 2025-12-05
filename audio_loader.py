import os
from pathlib import Path
from pydub import AudioSegment
import time

class AudioHandler:
    def __init__(self, temp_dir="temp_audio"):
        """
        初始化音频处理器
        :param temp_dir: 用于存放转换后的临时 WAV 文件的目录
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
        
        :param input_path: 输入文件的路径 (str 或 Path)
        :return: 转换后的 wav 文件绝对路径 (str)
        """
        input_path = Path(input_path)
        
        # 1. 基础校验
        if not input_path.exists():
            raise FileNotFoundError(f"找不到文件: {input_path}")
        
        if input_path.suffix.lower() != '.mp3':
            # 可以在这里扩展支持其他格式，目前仅针对需求
            print(f"警告: 输入文件 {input_path.name} 可能不是 MP3，尝试强制读取...")

        print(f"正在处理: {input_path.name} ...")

        try:
            # 2. 使用 pydub 加载音频
            # Pydub 会调用底层的 ffmpeg 进行解码
            audio = AudioSegment.from_mp3(str(input_path))
            
            # 3. 准备输出路径
            # 使用时间戳防止文件名冲突 (为未来 Web 多用户并发做准备)
            timestamp = int(time.time())
            output_filename = f"{input_path.stem}_{timestamp}.wav"
            output_path = self.temp_dir / output_filename

            # 4. 导出为 WAV
            # 通信原理课程项目中，采样率通常很重要，这里默认保留原采样率
            # 如果后续 Pedalboard 效果器需要特定采样率（如 44100），可以在这里指定：
            # audio = audio.set_frame_rate(44100)
            
            audio.export(str(output_path), format="wav")
            
            print(f"转换成功: {output_path}")
            return str(output_path.absolute())

        except Exception as e:
            raise RuntimeError(f"音频转换失败: {str(e)}")

# --- 快速原型测试代码 (当直接运行此文件时执行) ---
if __name__ == "__main__":
    # 模拟用户上传了一个 mp3 文件
    # 你可以在同目录下放一个 test.mp3 来测试
    
    converter = AudioHandler()
    
    # 假设有一个输入文件
    test_file = "test.mp3" 
    
    # 为了演示，我们先创建一个假的 mp3 文件（如果不存在的话），以免报错
    if not os.path.exists(test_file):
        print("未找到测试文件，正在生成一个静音 MP3 用于测试...")
        AudioSegment.silent(duration=1000).export(test_file, format="mp3")

    try:
        wav_path = converter.convert_mp3_to_wav(test_file)
        print(f"下一步：将 '{wav_path}' 传递给 DSP 处理模块（磁带/黑胶效果）")
    except Exception as e:
        print(f"错误: {e}")