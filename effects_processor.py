import numpy as np
from pedalboard import Pedalboard, Chorus, Reverb, Distortion, LowpassFilter, HighpassFilter, Compressor, Gain
from pedalboard.io import AudioFile
import os

class EffectsProcessor:
    def __init__(self):
        """
        初始化处理器。
        这里可以预加载一些资源，或者定义通用的参数。
        """
        pass

    def process(self, input_wav, output_wav, effect_chain):
        """
        核心处理管道。
        
        :param input_wav: 输入 WAV 路径
        :param output_wav: 输出 WAV 路径
        :param effect_chain: 一个列表，包含要按顺序执行的效果名称字符串
                             例如: ['add_white_noise', 'tape_style']
        """
        print(f"🔄 开始处理音频链: {' -> '.join(effect_chain)}")
        
        # 1. 读取音频 (Input)
        # Pedalboard 的 AudioFile 能非常方便地把音频读成 Numpy 数组
        with AudioFile(input_wav) as f:
            audio = f.read(f.frames)
            samplerate = f.samplerate

        # 2. 级联处理 (Processing Chain)
        # audio 变量在循环中不断被修改，就像信号流经一个个模块
        for effect_name in effect_chain:
            processor_func = getattr(self, f"_effect_{effect_name}", None)
            if processor_func:
                print(f"   ⚡️ 应用效果模块: {effect_name} ...")
                audio = processor_func(audio, samplerate)
            else:
                print(f"   ⚠️ 警告: 未找到效果模块 '{effect_name}'，跳过。")

        # 3. 写入文件 (Output)
        with AudioFile(output_wav, 'w', samplerate, audio.shape[0]) as f:
            f.write(audio)
        
        print(f"✅ 处理完成: {output_wav}")
        return output_wav

    # ==========================
    #  原子效果模块 (私有方法)
    # ==========================

    def _effect_tape(self, audio, samplerate):
        """
        [风格模拟] 磁带效果
        特点：抖动 (Wow/Flutter)，高频衰减，轻微失真
        """
        board = Pedalboard([
            # 1. 压缩：把动态压扁一点，模拟磁带的“胶水感”
            Compressor(threshold_db=-10, ratio=2.5),
            # 2. 合唱 (Chorus)：模拟磁带转速不稳导致的音高抖动 (Wow/Flutter)
            Chorus(rate_hz=1.5, depth=0.15, mix=0.5),
            # 3. 失真：模拟磁饱和
            Distortion(drive_db=3),
            # 4. 低通滤波：磁带通常记录不了极高频
            LowpassFilter(cutoff_frequency_hz=12000),
        ])
        return board(audio, samplerate)

    def _effect_vinyl(self, audio, samplerate):
        """
        [风格模拟] 黑胶唱片
        特点：温暖中频，Crackles (爆豆声)，Pops (大爆音)
        """
        # 1. 先用 Pedalboard 调整音色 (EQ)
        board = Pedalboard([
            # 切掉极低频 rumble
            HighpassFilter(cutoff_frequency_hz=30),
            # 衰减高频，制造“温暖”感
            LowpassFilter(cutoff_frequency_hz=10000),
            # 增加一点增益
            Gain(gain_db=2)
        ])
        audio = board(audio, samplerate)

        # 2. [通信原理考点] 使用 Numpy 注入脉冲噪声 (Impulse Noise) 模拟爆豆声
        # 生成一个和音频一样大的全零矩阵
        noise = np.zeros_like(audio)
        
        # 随机选择 0.1% 的采样点变成“爆音”
        crackles_indices = np.random.rand(*audio.shape) < 0.001
        # 赋予随机强度
        noise[crackles_indices] = np.random.uniform(-0.1, 0.1, np.sum(crackles_indices))
        
        # 叠加噪声 (加法干扰)
        return audio + noise

    def _effect_radio(self, audio, samplerate):
        """
        [风格模拟] 老式收音机 (AM 广播)
        特点：频带极窄 (300Hz-3400Hz)，大量白噪声
        """
        # 1. 频带限制 (Bandpass)
        board = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=300),
            LowpassFilter(cutoff_frequency_hz=3400),
            Distortion(drive_db=10) # 模拟接收机过载
        ])
        audio = board(audio, samplerate)

        # 2. [通信原理考点] 加性高斯白噪声 (AWGN)
        # 模拟信道底噪
        white_noise_level = 0.015
        noise = np.random.normal(0, white_noise_level, audio.shape)
        
        return audio + noise

    def _effect_normalize(self, audio, samplerate):
        """
        [工具] 归一化
        防止加上特效后爆音
        """
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            return audio / max_val * 0.9  # 保留 -1dB 余量
        return audio

# --- 单独测试代码 ---
if __name__ == "__main__":
    # 文档测试：确保没有语法错误
    # 这里不会真的跑，除非你有输入文件
    print("模块加载成功。请在 main.py 中调用。")