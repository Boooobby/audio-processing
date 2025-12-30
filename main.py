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

# [新增] 导入通信原理实验模块
from effects.aliasing import AliasingStyle
from effects.companding import CompandingStyle
from effects.steganography import SpectrogramArtStyle
from effects.channel_code import HammingCodeEffect, CRC32Effect, CombinedChannelCodeEffect

# [新增] 导入可视化分析工具
from analysis import AudioAnalyzer
from pedalboard.io import AudioFile


def cleanup_directories():
    """清理临时文件"""
    directories = ['temp_audio', 'output_audio']
    extensions = ['*.wav', '*.mp3', '*.html', '*.png']
    print("\n🧹 正在清理临时文件...")
    for folder in directories:
        if not os.path.exists(folder): continue
        for ext in extensions:
            files = glob.glob(os.path.join(folder, ext))
            for f in files:
                try:
                    os.remove(f)
                except:
                    pass
    print("✨ 清理完成。")


def main():
    cleanup_directories()
    loader = AudioHandler()
    exporter = AudioExporter()
    pipeline = AudioPipeline()

    # mp3文件入口
    input_file = "./testmp3/short-test.mp3"
    if not os.path.exists(input_file):
        os.makedirs(os.path.dirname(input_file), exist_ok=True)
        from pydub import AudioSegment
        AudioSegment.silent(duration=3000).export(input_file, format="mp3")

    # Step 1: 转 Wav
    wav_path = loader.convert_mp3_to_wav(input_file)
    output_wav = wav_path.replace(".wav", "_final.wav")

    clean_chain = []  # 预处理链(留空)

    # ==================== 1. 定义所有可能的链路 ====================

    # [链路 1] 原有复古效果组合
    vintage_chain = [
        # PCMBitcrusherStyle(bit_depth=8), 
        # VinylStyle(crackle_amount=0.005, hiss_level=0.01), 
        # ConvolutionReverb()
        HammingCodeEffect()
    ]

    # [链路 2] 混叠效应实验 (Aliasing)
    aliasing_safe_chain = [AliasingStyle(target_samplerate=4000, obey_nyquist=True), Normalizer()]
    aliasing_broken_chain = [AliasingStyle(target_samplerate=4000, obey_nyquist=False), Normalizer()]

    # [链路 3] 非均匀量化实验 (Companding)
    linear_pcm_chain = [CompandingStyle(bit_depth=4, enable_companding=False), Normalizer()]
    alaw_pcm_chain = [CompandingStyle(bit_depth=4, enable_companding=True), Normalizer()]

    # [链路 4] 画中音 (Steganography)
    stego_chain = [SpectrogramArtStyle(image_path="secret.png", duration=5.0), Normalizer()]

    # =============================================================
    # 总控开关：请解开对应行的注释以选择实验场景 (一次只选一个)
    # =============================================================

    # --- 选项 A: 复古风格综合演示 (默认) ---
    # [描述] 混合了调幅、频移、多普勒等多种效果，听起来像老旧电台。
    style_chain = vintage_chain
    experiment_name = "Original_Vintage"

    # --- 选项 B: 混叠效应 - 违反定理 ---
    # [原理] 强制降采样且不加滤波，导致高频折叠回低频。
    # [听感] 声音充满金属质感的“兹兹”杂音 (Robot Voice)。
    # style_chain = aliasing_broken_chain
    # experiment_name = "Aliasing_Broken_Test"

    # --- 选项 C: 混叠效应 - 遵守定理 ---
    # [原理] 先进行抗混叠滤波，再降采样。
    # [听感] 声音变闷（高频丢失），但非常干净，无杂音。
    # style_chain = aliasing_safe_chain
    # experiment_name = "Aliasing_Safe_Test"

    # --- 选项 D: 非均匀量化 - A律压扩 (优化方案) ---
    # [原理] 对小信号进行放大编码，模拟电话系统标准。
    # [听感] 在同样的 4-bit 低比特率下，信噪比显著提升，噪声更小。
    # style_chain = alaw_pcm_chain
    # experiment_name = "Companding_Alaw_Test"

    # --- 选项 E: 非均匀量化 - 均匀量化 (对比组) ---
    # [原理] 线性量化，小信号精度不足。
    # [听感] 声音有明显的颗粒感，小音量时有断续的门控噪声。
    # style_chain = linear_pcm_chain
    # experiment_name = "Companding_Linear_Test"

    # --- 选项 F: 黑科技 - 频谱画中音 ---
    # [原理] 将图片像素映射为频率，直接生成音频。
    # [注意] 请确保根目录下有 'secret.png' 图片！
    # style_chain = stego_chain
    # experiment_name = "Spectrogram_Art"

    # =============================================================

    # 执行处理
    print(f"🚀 运行链路: {experiment_name}")
    pipeline.run(
        input_path=wav_path,
        output_path=output_wav,
        pre_processors=clean_chain,
        main_effects=style_chain
    )

    # === 可视化分析 ===
    print("\n--- 正在进行信号分析 ---")
    try:
        with AudioFile(wav_path) as f:
            original_data = f.read(f.frames)[0]
            sr = f.samplerate
        with AudioFile(output_wav) as f:
            processed_data = f.read(f.frames)[0]

        snr = AudioAnalyzer.calculate_snr(original_data, processed_data)
        print(f"📈 信噪比 (SNR): {snr:.2f} dB")

        img_name = f"{experiment_name}_analysis.png"
        AudioAnalyzer.plot_comparison(
            original_data, processed_data, sr,
            title=f"{experiment_name} (SNR={snr:.1f}dB)",
            filename=img_name
        )
    except Exception as e:
        print(f"⚠️ 分析跳过 (可能是画中音导致长度不一致): {e}")

    # Step 3: 导出播放
    mp3_path = exporter.export_to_mp3(output_wav)
    exporter.browser_playback(mp3_path)


if __name__ == "__main__":
    main()