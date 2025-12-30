import numpy as np
from scipy.signal import butter, lfilter, hilbert
from .base import AudioEffect

class EnhancedAMEffect(AudioEffect):
    """
    增强版AM（调幅）调制解调音频处理器
    核心功能：支持标准AM、DSB-SC（双边带抑制载波）、SSB（单边带）三种调制模式，
             包含完整的“预处理→调制→信道噪声→解调→后处理”链路
    """

    def __init__(self, **kwargs):
        super().__init__(name="Enhanced AM Effect")

        # 1. 初始化默认参数
        self.carrier_freq = 10000
        self.modulation_index = 0.7
        self.sample_rate = 44100
        self.am_mode = "standard"  # 默认调制模式
        self.noise_snr = 35
        self.carrier_sync_tol = 0.01
        self.pre_emphasis = True

        # 2. 从 kwargs 中提取参数并覆盖默认值
        for key, value in kwargs.items():
            if hasattr(self, key):  # 只处理类中已定义的属性
                setattr(self, key, value)

    def _preprocess_audio(self, audio_wave):
        """
        归一化 + 预加重
        """
        # 1. 峰值归一化
        peak = np.max(np.abs(audio_wave))
        if peak != 0:
            audio_wave = audio_wave / peak

        # 2. 预加重：一阶高通滤波
        if self.pre_emphasis:
            b, a = butter(1, 3000, btype='highpass', fs=self.sample_rate)
            audio_wave = lfilter(b, a, audio_wave)

        return audio_wave

    def _generate_carrier(self, length):
        """
        生成带同步误差的载波信号
        """
        # 生成时间轴
        t = np.linspace(0, length / self.sample_rate, length, endpoint=False)

        # 模拟载波同步误差
        freq_offset = self.carrier_freq * self.carrier_sync_tol * np.random.uniform(-1, 1)
        phase_offset = np.random.uniform(0, 2 * np.pi)

        # 生成载波信号
        carrier = np.cos(2 * np.pi * (self.carrier_freq + freq_offset) * t + phase_offset)
        return carrier

    def _am_modulate(self, audio_wave):
        """
        多模式AM调制：standard/DSB-SC/SSB
        """
        length = len(audio_wave)
        carrier = self._generate_carrier(length)  # 生成载波

        # 1. 标准AM调制
        if self.am_mode == "standard":
            modulated = (1 + self.modulation_index * audio_wave) * carrier

        # 2. DSB-SC
        elif self.am_mode == "dsb-sc":
            modulated = self.modulation_index * audio_wave * carrier

        # 3. SSB
        elif self.am_mode == "ssb":
            analytic_signal = hilbert(audio_wave)
            dsb_modulated = self.modulation_index * analytic_signal * carrier
            b, a = butter(2, self.carrier_freq, btype='lowpass', fs=self.sample_rate)
            modulated = lfilter(b, a, dsb_modulated).real

        signal_power = np.mean(np.square(modulated))
        noise_power = signal_power / (10 ** (self.noise_snr / 10))  # SNR→噪声功率
        noise = np.sqrt(noise_power) * np.random.randn(length)  # 高斯白噪声
        modulated += noise

        return modulated

    def _carrier_recovery(self, modulated_wave):
        """
        载波恢复：平方律检波法
        """
        squared = np.square(modulated_wave)

        b, a = butter(2, [2 * self.carrier_freq - 100, 2 * self.carrier_freq + 100],
                      btype='bandpass', fs=self.sample_rate)
        filtered = lfilter(b, a, squared)

        t = np.linspace(0, len(filtered) / self.sample_rate, len(filtered))
        recovered_carrier = np.cos(np.cumsum(2 * np.pi * 2 * self.carrier_freq * t) * 0.5)

        cross_corr = np.correlate(modulated_wave, recovered_carrier, mode='same')
        phase_shift = np.argmax(cross_corr) * (2 * np.pi / len(cross_corr))
        recovered_carrier = np.cos(2 * np.pi * self.carrier_freq * t + phase_shift)

        return recovered_carrier

    def _am_demodulate(self, modulated_wave):
        """
        多模式AM解调：包络检波/同步检波（DSB-SC/SSB）
        """
        # 1. 标准AM：包络检波（结构简单，无需同步载波）
        if self.am_mode == "standard":
            rectified = np.abs(modulated_wave)  # 半波整流提取包络
            # 低通滤波：提取包络（截止频率=5kHz，覆盖音频最高频率）
            b, a = butter(2, 5000, btype='lowpass', fs=self.sample_rate)
            demodulated = lfilter(b, a, rectified)
            demodulated -= np.mean(demodulated)  # 去除直流分量

        # 2. DSB-SC/SSB：同步检波（需先恢复载波）
        else:
            recovered_carrier = self._carrier_recovery(modulated_wave)
            multiplied = modulated_wave * recovered_carrier  # 相乘解调
            # 低通滤波提取低频调制分量
            b, a = butter(2, 5000, btype='lowpass', fs=self.sample_rate)
            demodulated = lfilter(b, a, multiplied)
            demodulated = demodulated * 2 / self.modulation_index  # 幅度补偿

        # 3. 去加重：补偿预加重，还原音频频响
        if self.pre_emphasis:
            b, a = butter(1, 3000, btype='lowpass', fs=self.sample_rate)
            demodulated = lfilter(b, a, demodulated)

        # 4. 归一化：避免幅度异常
        demodulated = demodulated / np.max(np.abs(demodulated))
        return demodulated

    def process(self, audio, samplerate):
        self.sample_rate = samplerate  # 覆盖默认采样率
        processed_wave = []

        for chan in audio:
            # 完整链路：预处理→调制→解调
            preprocessed = self._preprocess_audio(chan)
            modulated = self._am_modulate(preprocessed)
            demodulated = self._am_demodulate(modulated)

            processed_wave.append(demodulated)

        return np.array(processed_wave)

    def get_params(self):
        """获取AM效果器参数（便于调试/参数调整）"""
        return {
            "carrier_freq(Hz)": self.carrier_freq,
            "modulation_index(0-1)": self.modulation_index,
            "am_mode": self.am_mode,
            "channel_snr(dB)": self.noise_snr,
            "carrier_sync_tolerance(%)": self.carrier_sync_tol * 100,
            "pre_emphasis": self.pre_emphasis
        }

    def set_params(self, **kwargs):
        """动态调整AM参数（带合理性约束）"""
        for param_name, param_value in kwargs.items():
            if hasattr(self, param_name):
                # 调制度约束：0-1（>1过调制，<0无意义）
                if param_name == "modulation_index":
                    param_value = np.clip(param_value, 0, 1)
                # 信噪比约束：0-40dB（<0噪声过强，>40近似无噪声）
                elif param_name == "noise_snr":
                    param_value = np.clip(param_value, 0, 40)
                # 调制模式约束：仅支持预设三种
                elif param_name == "am_mode":
                    param_value = param_value if param_value in ["standard", "dsb-sc", "ssb"] else "standard"
                # 载波频率约束：20Hz~采样率/2（奈奎斯特准则）
                elif param_name == "carrier_freq" and self.sample_rate:
                    param_value = np.clip(param_value, 20, self.sample_rate / 2 - 100)

                setattr(self, param_name, param_value)
