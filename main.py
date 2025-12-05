import os
from audio_loader import AudioHandler
from audio_exporter import AudioExporter
from effects_processor import EffectsProcessor

def main():
    print("=== 通信原理课程项目：音频风格化工具原型 ===")
    
    # 1. 准备模块
    loader = AudioHandler()
    exporter = AudioExporter()
    processor = EffectsProcessor()
    
    # 输入文件
    input_file = "test.mp3"
    
    # 自动生成测试文件逻辑
    if not os.path.exists(input_file):
        print(f"未找到 {input_file}，生成测试音频...")
        from pydub import AudioSegment
        AudioSegment.silent(duration=3000).export(input_file, format="mp3")

    try:
        # Step 1: 接收与解码
        print("\n[Step 1] 接收音频...")
        wav_path = loader.convert_mp3_to_wav(input_file)
        # 准备输出路径
        # 为了不覆盖原文件，我们创建一个新的文件名
        processed_wav = wav_path.replace(".wav", "_process.wav")
        
        # Step 2: 信号处理 (TODO: 这里未来接入 Pedalboard)
        print("\n[Step 2] 配置处理链路...")

        # === 核心：在这里定义你想要的“链路” ===
        # 场景 A: 磁带风格
        # chain = ['tape']
        
        # 场景 B: 黑胶风格 + 归一化
        chain = ['vinyl', 'normalize']
        
        # 场景 C: 疯狂的实验 (收音机 -> 磁带 -> 再加点黑胶爆豆)
        # chain = ['radio', 'tape', 'normalize']

        # 场景 D: 无效果
        # chain = []
        
        # 执行处理
        processor.process(
            input_wav=wav_path, 
            output_wav=processed_wav, 
            effect_chain=chain
        ) 
        
        # Step 3: 编码与导出
        print("\n[Step 3] 导出最终成品...")
        mp3_path = exporter.export_to_mp3(processed_wav)
        
        # Step 4: Web 播放预览
        print("\n[Step 4] 启动 Web 预览...")
        exporter.regex_browser_playback(mp3_path)
        
    except Exception as e:
        print(f"\n❌ 处理链发生错误: {e}")

if __name__ == "__main__":
    main()