import numpy as np
from scipy.signal import butter, lfilter, hilbert
from .base import AudioEffect  # 适配effects文件夹的相对导入


class EnhancedAMEffect(AudioEffect):
    """
    增强版AM（调幅）调制解调音频处理器
    核心功能：支持标准AM、DSB-SC（双边带抑制载波）、SSB（单边带）三种调制模式，
             包含完整的“预处理→调制→信道噪声→解调→后处理”链路
    关联通信原理知识点：
    1. 模拟调制：AM/DSB-SC/SSB调制公式与频谱特性
    2. 载波同步：平方律检波载波恢复、相位调整
    3. 信道特性：信噪比（SNR）计算、高斯白噪声模拟
    4. 信号预处理：预加重/去加重（补偿信道高频损耗）
    """

    def __init__(self, **kwargs):  # 新增**kwargs 接收所有关键字参数
        super().__init__(name="Enhanced AM Effect")

        # 1. 初始化默认参数
        self.carrier_freq = 10000
        self.modulation_index = 0.7
        self.sample_rate = 44100
        self.am_mode = "standard"  # 默认调制模式
        self.noise_snr = 35
        self.carrier_sync_tol = 0.01
        self.pre_emphasis = True

        # 2. 从 kwargs 中提取参数并覆盖默认值（关键步骤）
        for key, value in kwargs.items():
            if hasattr(self, key):  # 只处理类中已定义的属性
                setattr(self, key, value)

    def _preprocess_audio(self, audio_wave):
        """
        音频预处理：归一化 + 预加重
        知识点应用：峰值归一化（避免过调制）、预加重（补偿信道高频衰减）
        """
        # 1. 峰值归一化（压缩到[-1,1]，防止过调制失真）
        peak = np.max(np.abs(audio_wave))
        if peak != 0:
            audio_wave = audio_wave / peak

        # 2. 预加重：一阶高通滤波（3kHz截止，提升高频分量）
        if self.pre_emphasis:
            b, a = butter(1, 3000, btype='highpass', fs=self.sample_rate)
            audio_wave = lfilter(b, a, audio_wave)

        return audio_wave

    def _generate_carrier(self, length):
        """
        生成带同步误差的载波信号
        知识点应用：正弦载波公式、载波同步误差模拟（频率/相位偏移）
        """
        # 生成时间轴（覆盖音频时长）
        t = np.linspace(0, length / self.sample_rate, length, endpoint=False)

        # 模拟载波同步误差：频率偏移（±1%）+ 相位偏移（0~2π）
        freq_offset = self.carrier_freq * self.carrier_sync_tol * np.random.uniform(-1, 1)
        phase_offset = np.random.uniform(0, 2 * np.pi)

        # 生成载波信号：c(t) = cos(2π(fc+Δf)t + φ)
        carrier = np.cos(2 * np.pi * (self.carrier_freq + freq_offset) * t + phase_offset)
        return carrier

    def _am_modulate(self, audio_wave):
        """
        多模式AM调制：standard/DSB-SC/SSB
        知识点应用：三种AM调制的核心公式，直接对应通信原理教材理论
        """
        length = len(audio_wave)
        carrier = self._generate_carrier(length)  # 生成载波

        # 1. 标准AM调制：s_AM(t) = (1 + m×s(t))×cos(2πfc t)
        if self.am_mode == "standard":
            modulated = (1 + self.modulation_index * audio_wave) * carrier

        # 2. DSB-SC（双边带抑制载波）：s_DSB(t) = m×s(t)×cos(2πfc t)
        elif self.am_mode == "dsb-sc":
            modulated = self.modulation_index * audio_wave * carrier

        # 3. SSB（单边带）：希尔伯特变换提取单边带（节省带宽）
        elif self.am_mode == "ssb":
            analytic_signal = hilbert(audio_wave)  # 希尔伯特变换获取解析信号
            dsb_modulated = self.modulation_index * analytic_signal * carrier
            # 低通滤波提取单边带（截止频率=载波频率）
            b, a = butter(2, self.carrier_freq, btype='lowpass', fs=self.sample_rate)
            modulated = lfilter(b, a, dsb_modulated).real

        # 2. 模拟信道噪声（基于SNR计算噪声功率）
        signal_power = np.mean(np.square(modulated))
        noise_power = signal_power / (10 ** (self.noise_snr / 10))  # SNR→噪声功率
        noise = np.sqrt(noise_power) * np.random.randn(length)  # 高斯白噪声
        modulated += noise

        return modulated

    def _carrier_recovery(self, modulated_wave):
        """
        载波恢复：平方律检波法（针对DSB-SC/SSB无载波信号）
        知识点应用：平方律检波提取2倍载波频率，二分频还原原始载波
        """
        # 1. 平方律检波：s²(t) = [m×s(t)×cos(2πfc t)]² = (m²s²(t)/2)×[1 + cos(4πfc t)]
        squared = np.square(modulated_wave)

        # 2. 窄带带通滤波：提取2fc分量（中心频率=2fc，带宽=200Hz）
        b, a = butter(2, [2 * self.carrier_freq - 100, 2 * self.carrier_freq + 100],
                      btype='bandpass', fs=self.sample_rate)
        filtered = lfilter(b, a, squared)

        # 3. 二分频：2fc→fc，恢复原始载波频率
        t = np.linspace(0, len(filtered) / self.sample_rate, len(filtered))
        recovered_carrier = np.cos(np.cumsum(2 * np.pi * 2 * self.carrier_freq * t) * 0.5)

        # 4. 相位调整：互相关找到最佳相位偏移
        cross_corr = np.correlate(modulated_wave, recovered_carrier, mode='same')
        phase_shift = np.argmax(cross_corr) * (2 * np.pi / len(cross_corr))
        recovered_carrier = np.cos(2 * np.pi * self.carrier_freq * t + phase_shift)

        return recovered_carrier

    def _am_demodulate(self, modulated_wave):
        """
        多模式AM解调：包络检波（standard）/同步检波（DSB-SC/SSB）
        知识点应用：包络检波（无需同步）、同步检波（无载波信号必备）
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

    # 核心process方法（严格匹配基类接口：audio, samplerate）
    def process(self, audio, samplerate):
        """
        对外统一接口：处理多通道音频的AM调制解调
        :param audio: 输入音频波形，shape=(通道数, 采样点数)
        :param samplerate: 输入音频抽样率（Hz）
        :return: 处理后的音频波形，shape与输入一致
        """
        self.sample_rate = samplerate  # 覆盖默认采样率
        processed_wave = []

        # 对每个声道单独处理
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
