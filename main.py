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
from effects.aliasing import AliasingStyle
from effects.companding import CompandingStyle
from effects.steganography import SpectrogramArtStyle
from analysis import AudioAnalyzer
from pedalboard.io import AudioFile


def main():
    loader = AudioHandler()
    exporter = AudioExporter()
    pipeline = AudioPipeline()

    # mp3文件入口
    input_file = "./testmp3/test02.mp3"
    if not os.path.exists(input_file):
        # 如果没有文件，生成一个静音做测试
        from pydub import AudioSegment
        # 确保目录存在
        os.makedirs(os.path.dirname(input_file), exist_ok=True)
        AudioSegment.silent(duration=3000).export(input_file, format="mp3")

    # Step 1: 转 Wav
    wav_path = loader.convert_mp3_to_wav(input_file)
    output_wav = wav_path.replace(".wav", "_final.wav")

    # === 在这里像搭积木一样配置 ===

    # 1. 配置预处理链 (可以放去水印、降噪等)
    clean_chain = [

    ]

    # 2. 配置主效果链 (风格化 + 最后归一化)
    # 原有的复古效果配置
    vintage_chain = [
        # TapeStyle(),
        RadioStyle(),  # 示例：使用收音机效果
        # VinylStyle(crackle_amount=0.005),
        # PCMBitcrusherStyle(bit_depth=8),
        Normalizer()
    ]

    # === [实验功能 1] 通信原理：采样率变换与混叠效应 ===
    # 场景 A: 遵守定理 (声音闷，无杂音)
    aliasing_safe_chain = [
        AliasingStyle(target_samplerate=4000, obey_nyquist=True),
        Normalizer()
    ]
    # 场景 B: 违反定理 (金属混叠杂音) -> 观察频谱高频折叠
    aliasing_broken_chain = [
        AliasingStyle(target_samplerate=4000, obey_nyquist=False),
        Normalizer()
    ]

    # === [实验功能 2] 通信原理：非均匀量化 (A律压扩) ===
    # 场景 C: 均匀量化 (低比特下噪声大) -> 观察波形颗粒感
    linear_pcm_chain = [
        CompandingStyle(bit_depth=4, enable_companding=False),
        Normalizer()
    ]
    # 场景 D: A律压扩 (提升信噪比)
    alaw_pcm_chain = [
        CompandingStyle(bit_depth=4, enable_companding=True),
        Normalizer()
    ]

    # === [实验功能 3] 频谱画中音 (Spectrogram Art) ===
    # 注意：需要根目录下有一张名为 secret.png 的图片
    stego_chain = [
        # 生成 5 秒钟的音频，隐藏图片信息
        SpectrogramArtStyle(image_path="secret.png", duration=5.0),
        Normalizer()
    ]

    # ==================================================
    #  总控开关：在这里解开注释，选择你要运行的链路
    # ==================================================

    # 选项1：运行原有复古效果
    style_chain = vintage_chain
    experiment_name = "Vintage_Radio"

    # 选项2：测试混叠效应 (违反定理)
    # style_chain = aliasing_broken_chain
    # experiment_name = "Aliasing_Effect"

    # 选项3：测试A律压扩优势
    # style_chain = alaw_pcm_chain
    # experiment_name = "Alaw_Companding"

    # 选项4：生成“画中音”音频 (记得放图片!)
    # style_chain = stego_chain
    # experiment_name = "Spectrogram_Art"

    # ==================================================

    # 执行处理
    print(f"🚀 开始运行处理链路: {experiment_name} ...")
    pipeline.run(
        input_path=wav_path,
        output_path=output_wav,
        pre_processors=clean_chain,
        main_effects=style_chain
    )

    # [新增步骤] Step 2.5: 可视化分析与SNR计算
    print("\n--- 开始进行信号分析 ---")
    # 读取原始和处理后的音频数据
    with AudioFile(wav_path) as f:
        original_data = f.read(f.frames)[0]
        sr = f.samplerate
    with AudioFile(output_wav) as f:
        processed_data = f.read(f.frames)[0]

    # 1. 计算信噪比
    snr_value = AudioAnalyzer.calculate_snr(original_data, processed_data)
    print(f"📈 [Result] 当前处理结果的信噪比 (SNR): {snr_value:.2f} dB")

    # 2. 生成对比分析图
    analysis_img_name = f"{experiment_name}_analysis.png"
    AudioAnalyzer.plot_comparison(
        original_data,
        processed_data,
        sr,
        title=f"{experiment_name} (SNR={snr_value:.1f}dB)",
        filename=analysis_img_name
    )
    print("-----------------------\n")

    # Step 3: 导出播放
    mp3_path = exporter.export_to_mp3(output_wav)
    # exporter.regex_browser_playback(mp3_path)
    exporter.browser_playback(mp3_path)


if __name__ == "__main__":
    main()