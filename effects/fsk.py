import numpy as np
from base import AudioEffect

class FSKEffect(AudioEffect):
    def __init__(self):
        # FSK核心参数：可通过set_params动态调整
        self.freq0 = 1000    # 代表数字信号“0”的载波频率（Hz）
        self.freq1 = 2000    # 代表数字信号“1”的载波频率（Hz）
        self.bit_rate = 100  # 比特率（bps），决定每秒传输的比特数
        self.carrier_amp = 0.5  # 载波信号幅度，控制调制后信号强度
        self._original_wave = None  # 缓存原始波形，用于解调还原

    def _manual_butter_bandpass(self, low, high, sample_rate, order=2):
        """
        巴特沃斯带通滤波器（不调用scipy的butter封装）
        核心：通过模拟低通→频率迁移，手动计算滤波系数
        """
        # 1. 计算归一化截止频率（针对低通原型）
        nyq = 0.5 * sample_rate  # 奈奎斯特频率
        low_norm = low / nyq
        high_norm = high / nyq

        # 2. 设计低通巴特沃斯滤波器原型（计算极点）
        poles = []
        for k in range(1, order + 1):
            theta = np.pi * (2 * k - 1) / (2 * order)
            pole = -np.sin(theta) + 1j * np.cos(theta)
            poles.append(pole)
        poles = np.array(poles)

        # 3. 频率迁移：将低通原型转为带通滤波器
        # 计算带通滤波器的分子（b）和分母（a）系数
        b = np.ones(1)
        a = np.ones(1)
        for pole in poles:
            # 带通极点计算
            s1 = (high_norm - low_norm) * pole / 2
            s2 = np.sqrt(high_norm * low_norm)
            pole_bp = s1 + 1j * s2
            pole_bp_conj = s1 - 1j * s2
            # 累加分母系数（多项式展开）
            a = np.convolve(a, [1, -2 * pole_bp.real, pole_bp.real**2 + pole_bp.imag**2])
            # 累加分子系数（带通分子固定结构）
            b = np.convolve(b, [high_norm - low_norm, 0, -(high_norm - low_norm)])

        # 4. 系数归一化（保证直流增益为1）
        b = b / a[0]
        a = a / a[0]
        return b, a

    def _manual_lfilter(self, b, a, x):
        """手搓线性滤波（不调用scipy的lfilter），基于差分方程实现"""
        y = np.zeros_like(x)
        # 差分方程：y[n] = b0x[n] + b1x[n-1] + ... - a1y[n-1] - ... - any[n-n]
        for n in range(len(x)):
            # 计算输入项（b系数×x延迟项）
            input_sum = 0.0
            for k in range(len(b)):
                if n - k >= 0:
                    input_sum += b[k] * x[n - k]
            # 计算输出项（a系数×y延迟项，a[0]已归一化为1）
            output_sum = 0.0
            for k in range(1, len(a)):
                if n - k >= 0:
                    output_sum += a[k] * y[n - k]
            y[n] = input_sum - output_sum
        return y

    def _audio_to_bits(self, waveform, sample_rate):
        """手搓音频→比特流转换：基于幅度阈值量化"""
        # 1. 按比特率分割音频（每个比特对应一段音频）
        samples_per_bit = int(sample_rate / self.bit_rate)
        num_bits = len(waveform) // samples_per_bit
        # 2. 计算每段音频的平均幅度，大于阈值为1，否则为0
        threshold = np.max(np.abs(waveform)) * 0.1  # 动态阈值（10%最大幅度）
        bits = []
        for i in range(num_bits):
            seg_start = i * samples_per_bit
            seg_end = seg_start + samples_per_bit
            seg_avg = np.mean(np.abs(waveform[seg_start:seg_end]))
            bits.append(1 if seg_avg > threshold else 0)
        return np.array(bits), samples_per_bit

    def _fsk_modulate(self, bits, samples_per_bit, sample_rate):
        """FSK调制：根据比特值选择载波频率"""
        t = np.linspace(0, samples_per_bit / sample_rate, samples_per_bit, endpoint=False)
        modulated_wave = np.array([])
        for bit in bits:
            # 选择载波频率（1→freq1，0→freq0）
            carrier_freq = self.freq1 if bit == 1 else self.freq0
            # 生成载波信号（调幅：载波幅度×0.5避免过载）
            carrier = self.carrier_amp * np.sin(2 * np.pi * carrier_freq * t)
            modulated_wave = np.concatenate([modulated_wave, carrier])
        # 补零匹配原始波形长度（避免截断）
        if len(modulated_wave) < len(self._original_wave):
            pad_length = len(self._original_wave) - len(modulated_wave)
            modulated_wave = np.pad(modulated_wave, (0, pad_length), mode="constant")
        return modulated_wave

    def _fsk_demodulate(self, modulated_wave, samples_per_bit, sample_rate):
        """手搓FSK解调：带通滤波+能量比较还原比特流"""
        # 1. 手动设计两个带通滤波器（分别提取freq0和freq1）
        b0, a0 = self._manual_butter_bandpass(self.freq0 - 50, self.freq0 + 50, sample_rate)
        b1, a1 = self._manual_butter_bandpass(self.freq1 - 50, self.freq1 + 50, sample_rate)
        # 2. 手动滤波获取两个载波分量
        filt0 = self._manual_lfilter(b0, a0, modulated_wave)
        filt1 = self._manual_lfilter(b1, a1, modulated_wave)
        # 3. 按比特分割，比较两段滤波信号的能量（能量大的对应当前比特）
        num_bits = len(modulated_wave) // samples_per_bit
        bits = []
        for i in range(num_bits):
            seg_start = i * samples_per_bit
            seg_end = seg_start + samples_per_bit
            # 计算能量（平方和）
            energy0 = np.sum(np.square(filt0[seg_start:seg_end]))
            energy1 = np.sum(np.square(filt1[seg_start:seg_end]))
            bits.append(1 if energy1 > energy0 else 0)
        # 4. 从比特流还原音频（基于原始波形片段映射）
        demodulated_wave = np.array([])
        for i, bit in enumerate(bits):
            seg_start = i * samples_per_bit
            seg_end = seg_start + samples_per_bit
            # 提取原始波形片段，用比特值调整极性（增强辨识度）
            if seg_end <= len(self._original_wave):
                seg = self._original_wave[seg_start:seg_end]
                seg = seg * (1.2 if bit == 1 else 0.8)  # 1→增强，0→减弱
                demodulated_wave = np.concatenate([demodulated_wave, seg])
        # 补零匹配原始长度
        if len(demodulated_wave) < len(self._original_wave):
            pad_length = len(self._original_wave) - len(demodulated_wave)
            demodulated_wave = np.pad(demodulated_wave, (0, pad_length), mode="constant")
        return demodulated_wave

    def process(self, waveform, sample_rate):
        """FSK完整处理流程：音频→比特流→调制→解调→还原音频"""
        processed_wave = []
        # 多通道处理（兼容立体声/单声道）
        for chan in waveform:
            self._original_wave = chan  # 缓存当前通道原始波形
            # 1. 音频转比特流
            bits, samples_per_bit = self._audio_to_bits(chan, sample_rate)
            # 2. FSK调制
            modulated = self._fsk_modulate(bits, samples_per_bit, sample_rate)
            # 3. FSK解调
            demodulated = self._fsk_demodulate(modulated, samples_per_bit, sample_rate)
            processed_wave.append(demodulated)
        return np.array(processed_wave)

    def get_params(self):
        """获取当前FSK参数"""
        return {
            "freq0": self.freq0,
            "freq1": self.freq1,
            "bit_rate": self.bit_rate,
            "carrier_amp": self.carrier_amp
        }

    def set_params(self, **kwargs):
        """动态调整FSK参数（支持运行中修改）"""
        valid_keys = ["freq0", "freq1", "bit_rate", "carrier_amp"]
        for key, value in kwargs.items():
            if key in valid_keys and isinstance(value, (int, float)):
                # 参数合法性校验（避免无效值）
                if key in ["freq0", "freq1"] and 20 <= value <= 20000:  # 音频频率范围
                    setattr(self, key, value)
                elif key == "bit_rate" and 10 <= value <= 1000:  # 合理比特率范围
                    setattr(self, key, value)
                elif key == "carrier_amp" and 0.1 <= value <= 1.0:  # 幅度范围（避免过载）
                    setattr(self, key, value)
