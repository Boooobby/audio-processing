import os
import glob
from audio_loader import AudioHandler
from audio_exporter import AudioExporter
from pipeline import AudioPipeline

# 导入所有独立的原子模块
from effects.tape import TapeStyle
from effects.vinyl import VinylStyle
from effects.radio import RadioStyle
from effects.normalizer import Normalizer
from effects.pcm import PCMBitcrusherStyle
from effects.doppler import DopplerEffect
from effects.enhanced_am import EnhancedAMEffect
from effects.fsk import FSKEffect
from effects.convolution_reverb import ConvolutionReverb

def cleanup_directories():
    """
    清理 temp_audio 和 output_audio 目录下的临时文件
    保留目录结构，只删除文件。
    """
    # 定义要清理的文件夹
    directories = ['temp_audio', 'output_audio']
    # 定义要删除的文件扩展名 (白名单机制，防止误删)
    extensions = ['*.wav', '*.mp3', '*.html', '*.png']

    print("\n🧹 正在清理临时文件...")
    
    for folder in directories:
        if not os.path.exists(folder):
            continue
            
        for ext in extensions:
            # 拼接路径模式，例如: temp_audio/*.wav
            pattern = os.path.join(folder, ext)
            # 查找所有匹配的文件
            files = glob.glob(pattern)
            
            for file_path in files:
                try:
                    os.remove(file_path)
                    print(f"   已删除: {file_path}")
                except Exception as e:
                    print(f"   ❌ 删除失败 {file_path}: {e}")
    
    print("✨ 清理完成。")

def main():
    cleanup_directories()

    loader = AudioHandler()
    exporter = AudioExporter()
    pipeline = AudioPipeline()
    
    # mp3文件入口
    input_file = "./testmp3/test02.mp3"
    if not os.path.exists(input_file):
        # 如果没有文件，生成一个静音做测试
        from pydub import AudioSegment
        AudioSegment.silent(duration=3000).export(input_file, format="mp3")

    # Step 1: 转 Wav
    wav_path = loader.convert_mp3_to_wav(input_file)
    output_wav = wav_path.replace(".wav", "_final.wav")
    
    # === 在这里像搭积木一样配置 ===
    
    # 1. 配置预处理链 (可以放去水印、降噪等)
    clean_chain = [
        
    ]
    
    # 2. 配置主效果链 (风格化 + 最后归一化)
    style_chain = [
        # TapeStyle(), 
        # VinylStyle(crackle_amount=0.01), 
        # RadioStyle(), 
        # DopplerEffect(), 
        EnhancedAMEffect(), 
        FSKEffect(), 
        # ConvolutionReverb(), 
        PCMBitcrusherStyle(bit_depth=4), 
        DopplerEffect(), 
        # Normalizer(), 
        # ConvolutionReverb()
    ]
    
    # 执行
    pipeline.run(
        input_path=wav_path,
        output_path=output_wav,
        pre_processors=clean_chain,
        main_effects=style_chain
    )
    
    # Step 3: 导出播放
    mp3_path = exporter.export_to_mp3(output_wav)
    # exporter.regex_browser_playback(mp3_path)
    exporter.browser_playback(mp3_path)

if __name__ == "__main__":
    main()