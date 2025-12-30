import numpy as np
from scipy.signal import butter, lfilter, hilbert
from .base import AudioEffect

class FSKEffect(AudioEffect):
    """
    FSK（频移键控）调制解调音频处理器
    核心功能：模拟数字通信中的FSK调制（音频→数字比特→FSK载波）+ 解调（FSK载波→数字比特→音频）
    """

    def __init__(self):
        # 调用父类构造方法，指定效果名称
        super().__init__(name="FSK Effect")

        # 1. FSK核心参数（数字通信标准取值）
        self.freq0 = 1000  # 代表0比特的载波频率（1kHz）
        self.freq1 = 3000  # 代表1比特的载波频率（2kHz）
        self.bit_rate = 1200  # 比特率（1200bps，经典FSK通信速率）

        # 2. 音频处理参数
        self.bit_depth = 16  # 音频量化比特深度（16bit，标准音频格式）
        self.normalize = True  # 音频归一化（避免调制时幅度失真）
        self.noise_level = 0.001  # 模拟信道噪声强度（0~1）

    def _audio_to_bits(self, audio_wave, samplerate):
        """
        音频信号→数字比特流（数模转换核心步骤）
        知识点应用：抽样定理、量化编码、比特率匹配
        """
        # 1. 音频归一化（避免幅度超界）
        if self.normalize:
            audio_wave = audio_wave / np.max(np.abs(audio_wave))

        # 2. 计算每个比特对应的采样点数（比特率→采样点映射）
        samples_per_bit = int(samplerate / self.bit_rate)

        # 3. 音频信号分帧（每帧对应1个比特）
        # 补零使音频长度为samples_per_bit的整数倍
        pad_len = (samples_per_bit - len(audio_wave) % samples_per_bit) % samples_per_bit
        padded_wave = np.pad(audio_wave, (0, pad_len), mode='constant')

        # 4. 帧能量量化为比特（能量>0为1，≤0为0，简化版编码）
        frames = np.reshape(padded_wave, (-1, samples_per_bit))
        frame_energy = np.mean(np.abs(frames), axis=1)  # 计算每帧能量
        bits = (frame_energy > np.mean(frame_energy)).astype(int)  # 能量阈值分割为0/1

        return bits, samples_per_bit

    def _fsk_modulate(self, bits, samples_per_bit, samplerate):
        """
        FSK调制：数字比特流→FSK载波信号
        知识点应用：FSK调制公式 s(t) = A×cos(2πf_bit×t)
        """
        # 1. 生成时间轴（每个比特对应的时间点）
        t_bit = np.linspace(0, samples_per_bit / samplerate, samples_per_bit, endpoint=False)

        # 2. 生成FSK载波（逐比特拼接）
        modulated = []
        for bit in bits:
            # 选择对应频率的载波：0→freq0，1→freq1
            freq = self.freq0 if bit == 0 else self.freq1
            # 生成单比特载波信号
            bit_wave = np.cos(2 * np.pi * freq * t_bit)
            modulated.extend(bit_wave)

        # 3. 转换为numpy数组并添加信道噪声
        modulated_wave = np.array(modulated)
        noise = self.noise_level * np.random.randn(len(modulated_wave))  # 高斯白噪声
        modulated_wave += noise

        return modulated_wave

    def _fsk_demodulate(self, modulated_wave, samples_per_bit, samplerate):
        """
        FSK解调：FSK载波信号→数字比特流→还原音频
        知识点应用：希尔伯特变换提取瞬时频率、比特判决、数模还原
        """
        # 1. 希尔伯特变换提取解析信号（用于计算瞬时频率）
        analytic_signal = hilbert(modulated_wave)
        instantaneous_phase = np.unwrap(np.angle(analytic_signal))
        instantaneous_freq = np.diff(instantaneous_phase) / (2 * np.pi) * samplerate  # 瞬时频率

        # 补零使瞬时频率长度与原信号一致
        instantaneous_freq = np.pad(instantaneous_freq, (0, 1), mode='edge')

        # 2. 分帧判决比特（每帧平均频率靠近freq0为0，靠近freq1为1）
        frames = np.reshape(instantaneous_freq, (-1, samples_per_bit))
        frame_freq = np.mean(frames, axis=1)

        # 比特判决：计算与两个载波频率的距离
        dist0 = np.abs(frame_freq - self.freq0)
        dist1 = np.abs(frame_freq - self.freq1)
        bits = (dist1 < dist0).astype(int)

        # 3. 比特流→音频信号（简化版：1→正幅度，0→负幅度）
        reconstructed = []
        for bit in bits:
            # 生成单比特对应的音频帧
            bit_amp = 0.5 if bit == 1 else -0.5
            bit_wave = np.full(samples_per_bit, bit_amp)
            reconstructed.extend(bit_wave)

        # 4. 低通滤波还原音频（滤除载波高频）
        # 设计低通滤波器（截止频率=音频最高频率，此处取4kHz）
        b, a = butter(2, 4000, btype='lowpass', fs=samplerate)
        demodulated_wave = lfilter(b, a, np.array(reconstructed))

        # 5. 归一化并裁剪至原音频长度
        demodulated_wave = demodulated_wave / np.max(np.abs(demodulated_wave))
        demodulated_wave = demodulated_wave[:len(self._original_wave)]  # 匹配原音频长度

        return demodulated_wave

    # 核心process方法（严格匹配基类接口：audio, samplerate）
    def process(self, audio, samplerate):
        """
        对外统一接口：处理多通道音频的FSK调制解调
        :param audio: 输入音频波形，shape=(通道数, 采样点数)
        :param samplerate: 输入音频抽样率（Hz）
        :return: 处理后的音频波形，shape与输入一致
        """
        processed_wave = []
        self._original_wave = None  # 缓存原始波形（用于解调后长度匹配）

        # 对每个声道单独处理
        for chan in audio:
            self._original_wave = chan  # 缓存当前声道波形
            # 步骤1：音频→比特流
            bits, samples_per_bit = self._audio_to_bits(chan, samplerate)
            # 步骤2：比特流→FSK调制
            modulated = self._fsk_modulate(bits, samples_per_bit, samplerate)
            # 步骤3：FSK调制→还原音频
            demodulated = self._fsk_demodulate(modulated, samples_per_bit, samplerate)

            processed_wave.append(demodulated)

        # 转换为numpy数组，保持与输入一致的格式
        return np.array(processed_wave)

    def get_params(self):
        """获取FSK效果器参数（便于调试/参数调整）"""
        return {
            "fsk_freq0(Hz)": self.freq0,
            "fsk_freq1(Hz)": self.freq1,
            "bit_rate(bps)": self.bit_rate,
            "bit_depth": self.bit_depth,
            "noise_level": self.noise_level,
            "normalize_audio": self.normalize
        }

    def set_params(self, **kwargs):
        """动态调整FSK参数（带合理性约束）"""
        for param_name, param_value in kwargs.items():
            if hasattr(self, param_name):
                # 频率约束：载波频率需在音频可听域（20Hz~采样率/2）
                if param_name in ["freq0", "freq1"]:
                    nyquist = self.sample_rate / 2 if hasattr(self, 'sample_rate') else 20000
                    param_value = np.clip(param_value, 20, nyquist - 100)
                # 比特率约束：1200/2400/4800（经典FSK速率）
                elif param_name == "bit_rate":
                    valid_rates = [1200, 2400, 4800]
                    param_value = param_value if param_value in valid_rates else 1200
                # 噪声强度约束：0~0.1（避免噪声过强）
                elif param_name == "noise_level":
                    param_value = np.clip(param_value, 0, 0.1)

                setattr(self, param_name, param_value)