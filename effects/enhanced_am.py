import numpy as np
from scipy.signal import butter, lfilter, hilbert
from base import AudioEffect  # 继承项目统一抽象基类，保证OOP架构一致性


class EnhancedAMEffect(AudioEffect):
    """
    增强版AM调制解调音频处理器
    核心功能：覆盖标准AM、DSB-SC（双边带抑制载波）、SSB（单边带）三种模拟调制模式，
             包含完整的“预处理→调制→信道噪声→解调→后处理”链路
    关联通信原理知识点：
    1. 模拟调制解调：AM/DSB-SC/SSB调制公式、包络检波、同步检波
    2. 载波同步：平方律检波载波恢复、相位调整
    3. 信道特性：信噪比（SNR）计算、信道噪声模拟
    4. 信号预处理：预加重/去加重（补偿信道高频损耗）
    """

    def __init__(self):
        # 1. AM调制基础参数（贴合模拟调制理论定义）
        self.carrier_freq = 10000  # 载波频率（10kHz，模拟广播电台常用载波频段）
        self.modulation_index = 0.7  # 调制度（0-1，通信原理核心约束：>1会导致过调制失真）
        self.sample_rate = 44100  # 默认音频采样率（Hz，满足奈奎斯特准则：>2×载波频率）

        # 2. 增强功能参数（覆盖模拟通信系统关键环节）
        self.am_mode = "standard"  # 调制模式：standard(标准AM)/dsb-sc(双边带)/ssb(单边带)
        self.noise_snr = 20  # 信道信噪比（dB，模拟实际无线信道的噪声干扰）
        self.carrier_sync_tol = 0.01  # 载波同步误差容忍度（1%，模拟实际系统的同步偏差）

    def _preprocess_audio(self, waveform):
        """
        音频预处理：归一化+预加重
        知识点应用：
        1. 峰值归一化：避免调制时信号幅度超界，符合“调制信号需小于载波幅度”的理论要求
        2. 预加重：提升高频分量，补偿后续信道的高频损耗（模拟通信系统典型预处理步骤）
        """
        # 1. 峰值归一化：将音频幅度压缩到[-1,1]，防止调制时出现过调制失真
        peak = np.max(np.abs(waveform))
        if peak != 0:  # 避免除以零（空波形保护）
            waveform = waveform / peak

        # 2. 预加重：一阶高通滤波（3kHz截止），提升高频分量
        # 原理：信道通常对高频衰减更大，预加重可平衡整个频段的传输损耗
        b, a = butter(1, 3000, btype='highpass', fs=self.sample_rate)  # 一阶巴特沃斯高通滤波器
        return lfilter(b, a, waveform)  # 应用滤波

    def _generate_carrier(self, length):
        """
        生成载波信号，支持载波同步误差模拟
        知识点应用：
        1. 正弦载波生成：符合AM调制“高频载波”的理论定义（c(t) = A_c×cos(2πf_c t + φ)）
        2. 载波同步误差：模拟实际系统中载波的频率偏移（f_c±Δf）和相位偏移（φ±Δφ）
        """
        # 生成时间轴（s）：覆盖整个音频波形的时长
        t = np.linspace(0, length / self.sample_rate, length)

        # 模拟载波同步误差：频率偏移（±1%）+ 相位偏移（0~2π）
        freq_offset = self.carrier_freq * self.carrier_sync_tol * np.random.uniform(-1, 1)  # 频率偏差
        phase_offset = np.random.uniform(0, 2 * np.pi)  # 相位偏差

        # 生成带同步误差的载波信号（符合正弦载波公式）
        return np.cos(2 * np.pi * (self.carrier_freq + freq_offset) * t + phase_offset)

    def _am_modulate(self, waveform):
        """
        多模式AM调制：标准AM/DSB-SC/SSB
        知识点应用：三种模拟调制的核心公式，直接对应通信原理教材理论
        """
        length = len(waveform)  # 音频波形长度（采样点数）
        carrier = self._generate_carrier(length)  # 获取载波信号

        if self.am_mode == "standard":
            # 标准AM调制公式：s_AM(t) = (A_c + k_a×s(t))×cos(2πf_c t)
            # 此处简化：A_c=1，k_a=modulation_index，即 (1 + m×s(t))×c(t)
            # 特征：含载波分量（便于包络检波），带宽=2×调制信号最高频率
            modulated = (1 + self.modulation_index * waveform) * carrier

        elif self.am_mode == "dsb-sc":
            # DSB-SC（双边带抑制载波）调制公式：s_DSB(t) = k_a×s(t)×cos(2πf_c t)
            # 特征：无载波分量（节省功率），带宽=2×调制信号最高频率，需同步检波
            modulated = self.modulation_index * waveform * carrier

        elif self.am_mode == "ssb":
            # SSB（单边带）调制：通过希尔伯特变换提取单边带（节省带宽）
            # 知识点：SSB带宽=调制信号最高频率（仅为AM/DSB的1/2，频谱效率更高）
            analytic_signal = hilbert(waveform)  # 希尔伯特变换：获取调制信号的解析信号（含相位偏移）
            dsb_modulated = self.modulation_index * analytic_signal * carrier  # 先得到DSB信号
            # 低通滤波提取单边带（截止频率=载波频率，滤除上边带/下边带中的一个）
            b, a = butter(2, self.carrier_freq, btype='lowpass', fs=self.sample_rate)
            modulated = lfilter(b, a, dsb_modulated).real  # 取实部：还原实信号

        # 模拟信道噪声：根据信噪比（SNR）计算噪声功率，添加高斯白噪声
        # 知识点：SNR(dB) = 10×lg(信号功率/噪声功率)，此处反向计算噪声功率
        signal_power = np.mean(np.square(modulated))  # 计算调制信号功率
        noise_power = signal_power / (10 ** (self.noise_snr / 10))  # 由SNR推导噪声功率
        noise = np.sqrt(noise_power) * np.random.randn(length)  # 生成高斯白噪声
        return modulated + noise  # 噪声叠加：模拟实际信道传输

    def _carrier_recovery(self, modulated_wave):
        """
        载波恢复：从调制信号中提取同步载波（针对DSB-SC/SSB）
        知识点应用：平方律检波载波恢复法（模拟通信系统中无载波信号的核心同步技术）
        """
        # 1. 平方律检波：s²(t) = [m×s(t)×cos(2πf_c t)]² = (m²s²(t)/2)×[1 + cos(4πf_c t)]
        # 目的：提取出2倍载波频率（2f_c）的分量
        squared = np.square(modulated_wave)

        # 2. 窄带带通滤波：提取2f_c分量（滤除其他频率成分）
        b, a = butter(2, [2 * self.carrier_freq - 100, 2 * self.carrier_freq + 100],
                      btype='bandpass', fs=self.sample_rate)  # 中心频率=2f_c，带宽=200Hz
        filtered = lfilter(b, a, squared)

        # 3. 二分频：将2f_c分量转为原始载波频率f_c
        t = np.linspace(0, len(filtered) / self.sample_rate, len(filtered))  # 时间轴
        # 积分实现二分频：cos(2π×2f_c t) → cos(2πf_c t)
        recovered_carrier = np.cos(np.cumsum(2 * np.pi * 2 * self.carrier_freq * t) * 0.5)

        # 4. 相位调整：通过互相关找到最佳相位偏移，保证载波相位同步
        cross_corr = np.correlate(modulated_wave, recovered_carrier, mode='same')  # 计算互相关
        phase_shift = np.argmax(cross_corr) * (2 * np.pi / len(cross_corr))  # 找到最大相关对应的相位

        # 返回相位校正后的同步载波
        return np.cos(2 * np.pi * self.carrier_freq * t + phase_shift)

    def _am_demodulate(self, modulated_wave):
        """
        多模式AM解调：包络检波（标准AM）/同步检波（DSB-SC/SSB）
        知识点应用：两种解调方式的核心逻辑，对应不同调制模式的理论要求
        """
        if self.am_mode == "standard":
            # 标准AM：包络检波（结构简单，无需同步载波）
            # 原理：标准AM信号包络与调制信号一致，通过“整流+低通”即可提取
            rectified = np.abs(modulated_wave)  # 半波整流：保留信号正半周（包络信息）
            # 低通滤波：提取包络（截止频率=调制信号最高频率，此处取5kHz）
            b, a = butter(2, 5000, btype='lowpass', fs=self.sample_rate)
            demodulated = lfilter(b, a, rectified)
            # 去除直流分量：标准AM中的(1+...)引入直流，需减去均值还原原始调制信号
            demodulated = demodulated - np.mean(demodulated)

        else:
            # DSB-SC/SSB：同步检波（无载波，需先恢复同步载波）
            # 步骤1：恢复同步载波（调用载波恢复模块）
            recovered_carrier = self._carrier_recovery(modulated_wave)
            # 步骤2：相乘解调：s(t)×c(t) → 含低频调制分量和2f_c高频分量
            multiplied = modulated_wave * recovered_carrier
            # 步骤3：低通滤波：提取低频调制分量（滤除2f_c高频）
            b, a = butter(2, 5000, btype='lowpass', fs=self.sample_rate)
            demodulated = lfilter(b, a, multiplied)
            # 步骤4：幅度补偿：DSB-SC/SSB解调后幅度减半，需×2还原
            demodulated = demodulated * 2 / self.modulation_index

        # 去加重：补偿预加重的高频提升，还原音频原始频响
        # 原理：与预加重构成“加重-去加重”链路，抵消信道高频损耗
        b, a = butter(1, 3000, btype='lowpass', fs=self.sample_rate)  # 一阶巴特沃斯低通滤波器
        return lfilter(b, a, demodulated)

    def process(self, waveform, sample_rate):
        """
        对外统一接口：完整AM通信链路处理（多通道适配）
        链路流程：音频预处理 → AM调制 → 信道噪声 → AM解调 → 输出
        完全复现通信原理中“发送端→信道→接收端”的模拟通信系统架构
        """
        self.sample_rate = sample_rate  # 同步当前音频采样率
        processed_wave = []

        # 对每个声道单独处理（支持单声道/立体声音频）
        for chan in waveform:
            # 1. 音频预处理：归一化+预加重
            preprocessed = self._preprocess_audio(chan)
            # 2. AM调制：根据模式生成带噪声的调制信号
            modulated = self._am_modulate(preprocessed)
            # 3. AM解调：匹配调制模式，提取原始音频
            demodulated = self._am_demodulate(modulated)

            processed_wave.append(demodulated)

        return np.array(processed_wave)  # 返回处理后的多通道波形

    def get_params(self):
        """
        获取当前处理器参数（含通信原理关键理论参数）
        便于调试与报告展示，清晰映射理论知识点
        """
        return {
            "carrier_freq(Hz)": self.carrier_freq,  # 载波频率（模拟调制核心参数）
            "modulation_index(0-1)": self.modulation_index,  # 调制度（避免过调制的关键约束）
            "am_mode": self.am_mode,  # 调制模式（三种模拟调制对比）
            "channel_noise_snr(dB)": self.noise_snr,  # 信道信噪比（信道特性参数）
            "carrier_sync_tolerance(%)": self.carrier_sync_tol * 100  # 载波同步误差（同步性能参数）
        }

    def set_params(self, **kwargs):
        """
        动态调整处理器参数（工程化设计，支持实时测试）
        关键约束：保证参数符合通信原理理论要求，避免无效值
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                # 调制度约束：必须在0-1之间（>1会导致过调制，<0无意义）
                if key == "modulation_index":
                    value = np.clip(value, 0, 1)
                # 信噪比约束：避免极端值（<0dB噪声过强，>40dB近似无噪声）
                elif key == "noise_snr":
                    value = np.clip(value, 0, 40)
                # 调制模式约束：仅支持预设的三种模式
                elif key == "am_mode" and value not in ["standard", "dsb-sc", "ssb"]:
                    value = "standard"  # 非法模式默认切换为标准AM
                # 更新参数
                setattr(self, key, value)
