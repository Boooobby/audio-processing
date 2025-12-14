import os
from audio_loader import AudioHandler
from audio_exporter import AudioExporter
from pipeline import AudioPipeline

# 导入所有独立的原子模块
from effects.tape import TapeStyle
from effects.vinyl import VinylStyle
from effects.radio import RadioStyle
from effects.normalizer import Normalizer
from effects.pcm import PCMBitcrusherStyle
# [新增] 导入通信原理实验模块
from effects.aliasing import AliasingStyle
from effects.companding import CompandingStyle


def main():
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
        # TapeStyle()
        # VinylStyle(crackle_amount=0.005)
        # RadioStyle()
        # PCMBitcrusherStyle(bit_depth=4)
        # Normalizer()
    ]

    # === [新增功能 1] 通信原理实验：采样率变换与混叠效应 ===
    # 场景 A: 遵守通信原理 (加抗混叠滤波) -> 声音闷但无杂音
    aliasing_safe_chain = [
        AliasingStyle(target_samplerate=4000, obey_nyquist=True),
        Normalizer()
    ]
    # 场景 B: 违反通信原理 (无滤波暴力抽取) -> 混叠金属杂音 (Robot Voice)
    aliasing_broken_chain = [
        AliasingStyle(target_samplerate=4000, obey_nyquist=False),
        Normalizer()
    ]

    # === [新增功能 2] 通信原理实验：非均匀量化 (A律压扩) ===
    # 场景 C: 均匀量化 (低比特率下小信号噪声大)
    linear_pcm_chain = [
        CompandingStyle(bit_depth=4, enable_companding=False),
        Normalizer()
    ]
    # 场景 D: A律压扩 (提升小信号信噪比)
    alaw_pcm_chain = [
        CompandingStyle(bit_depth=4, enable_companding=True),
        Normalizer()
    ]

    # === [实验选择开关] 解开下方注释以覆盖默认 style_chain ===

    # style_chain = aliasing_broken_chain  # 测试混叠效应
    style_chain = alaw_pcm_chain  # 测试A律压扩

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