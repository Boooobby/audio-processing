import numpy as np
from scipy.signal import firwin, lfilter
from .base import AudioEffect  # 注意相对导入（effects文件夹内）


class DopplerEffect(AudioEffect):
    """
    多普勒效应
    """

    def __init__(self, **kwargs):
        super().__init__(name="Doppler Effect")

        self.speed = 30.0
        self.sound_speed = 343.0
        self.oversample_enable = True  # 过采样开关
        self.oversample_rate = 4  # 过采样倍数
        self.freq_shift_range = (20, 15000)  # 频率范围

        # 动态覆盖参数
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def _validate_freq_range(self, freq):
        """
        基于数字基带系统的奈奎斯特准则，约束频移后的频率范围
        逻辑：频移后信号最高频率 ≤ 奈奎斯特频率，避免混叠失真
        """
        # 计算当前抽样率下的奈奎斯特频率（数字基带系统的带宽上限）
        nyquist_freq = self.sample_rate / 2
        # 基础频率范围：下限为音频可听域（20Hz），上限初步限制为初始设定值
        valid_lower = max(self.freq_shift_range[0], 20)
        valid_upper = self.freq_shift_range[1]

        # 关键约束1：处理频率上限不得超过奈奎斯特频率（留1Hz余量，避免边界混叠）
        valid_upper = min(valid_upper, nyquist_freq - 1)

        # 关键约束2：预判频移后频率是否超界（多普勒因子可能导致频率放大）
        doppler_factor = self.sound_speed / (self.sound_speed - self.speed)
        max_shifted_freq = valid_upper * doppler_factor  # 频移后的最高频率
        if max_shifted_freq > nyquist_freq:
            # 动态降低处理频率上限，确保频移后仍符合奈奎斯特准则
            valid_upper = nyquist_freq / doppler_factor

        # 生成频率掩码：仅对符合奈奎斯特约束的频段进行处理
        freq_mask = np.logical_and(freq >= valid_lower, freq <= valid_upper)
        return freq_mask

    def _oversample(self, waveform):
        """
        数字基带系统的过采样处理
        工程逻辑：先升采样（插入零值），再低通滤波（滤除镜像频率）
        """
        # 1. 升采样：在原抽样点间插入（过采样倍数-1）个零值，抽样率提升至原倍数
        oversampled_len = len(waveform) * self.oversample_rate
        oversampled_wave = np.zeros(oversampled_len)
        oversampled_wave[::self.oversample_rate] = waveform  # 每隔N个点放置原抽样值

        # 2. 抗混叠低通滤波（基带系统核心步骤）
        # 截止频率：归一化频率 = 1/过采样倍数（确保仅保留原始信号频段）
        cutoff = 1 / self.oversample_rate
        # 设计FIR低通滤波器（汉明窗，31阶-兼顾滤波效果与计算效率）
        fir_filter = firwin(numtaps=31, cutoff=cutoff, window='hamming')
        # 应用滤波，去除升采样引入的镜像频率（避免后续处理混叠）
        filtered_wave = lfilter(fir_filter, 1, oversampled_wave)

        return filtered_wave

    def _downsample(self, waveform):
        """
        数字基带系统的降采样处理
        核心逻辑：每隔（过采样倍数）个点取一个值，丢弃冗余抽样点
        """
        return waveform[::self.oversample_rate]

    def _doppler_freq_shift(self, waveform):
        """
        多普勒频移核心算法：基于傅里叶变换的频域频率缩放
        """
        # 1. 离散傅里叶变换（DFT）：时域波形转换为频域复数谱（获取频率特征）
        fft_wave = np.fft.fft(waveform)
        freq_axis = np.fft.fftfreq(len(waveform), 1 / self.sample_rate)

        # 2. 计算多普勒频率缩放因子（通信原理多普勒频移公式变形）
        doppler_factor = self.sound_speed / (self.sound_speed - self.speed)

        # 3. 生成频率掩码（基于奈奎斯特准则约束的有效频段）
        freq_mask = self._validate_freq_range(freq_axis)

        # 4. 频域频率缩放（实现多普勒频移的核心步骤）
        scaled_indices = np.round(np.arange(len(fft_wave)) * doppler_factor).astype(int)
        valid_indices = np.logical_and(scaled_indices >= 0, scaled_indices < len(fft_wave))

        shifted_fft = np.zeros_like(fft_wave, dtype=np.complex128)
        shifted_fft[scaled_indices[valid_indices]] = fft_wave[valid_indices] * freq_mask[valid_indices]

        # 5. 逆离散傅里叶变换（IDFT）：频域谱转换回时域波形（可听音频信号）
        shifted_wave = np.fft.ifft(shifted_fft).real

        return shifted_wave

    def process(self, audio, samplerate):
        """
        对外统一接口：处理多通道音频（支持单声道/立体声）
        完整流程：过采样→频移处理→降采样→输出
        :param audio: 输入音频波形，shape=(通道数, 采样点数)
        :param samplerate: 输入音频抽样率（Hz）
        :return: 处理后的音频波形，shape与输入一致
        """
        self.sample_rate = samplerate  # 缓存当前音频抽样率
        processed_channels = []

        # 对每个声道单独处理（适配多通道音频）
        for chan in audio:
            # 1：过采样处理（若开启）- 数字基带系统抗混叠前置操作
            if self.oversample_enable:
                self.sample_rate *= self.oversample_rate
                oversampled_chan = self._oversample(chan)
                current_chan = oversampled_chan
            else:
                current_chan = chan

            # 2：多普勒频移核心处理（基于奈奎斯特约束的频域缩放）
            shifted_chan = self._doppler_freq_shift(current_chan)

            # 3：降采样处理（若开启）- 还原为原始抽样率，匹配音频输出
            if self.oversample_enable:
                downsampled_chan = self._downsample(shifted_chan)
                # 抽样率恢复为原始值，避免影响后续处理
                self.sample_rate /= self.oversample_rate
                processed_chan = downsampled_chan
            else:
                processed_chan = shifted_chan

            processed_channels.append(processed_chan)

        return np.array(processed_channels)

    def get_params(self):
        """
        获取当前处理器所有参数（含数字基带系统关键参数）
        """
        return {
            # 多普勒效应参数
            "relative_speed(m/s)": self.speed,
            "sound_speed(m/s)": self.sound_speed,
            "initial_freq_range(Hz)": self.freq_shift_range,
            # 数字基带系统参数（重点标注）
            "oversample_enable": self.oversample_enable,
            "oversample_rate": self.oversample_rate,
            "nyquist_freq(Hz)": self.sample_rate / 2 if self.sample_rate else None  # 奈奎斯特频率实时计算
        }

    def set_params(self, **kwargs):
        """
        动态调整处理器参数（支持运行中修改）
        """
        for param_name, param_value in kwargs.items():
            if hasattr(self, param_name):
                # 对关键参数添加合理性约束
                if param_name == "speed":
                    # 相对速度限制在±100m/s
                    param_value = np.clip(param_value, -100, 100)
                elif param_name == "oversample_rate":
                    # 过采样倍数限制为2的幂次
                    valid_rates = [1, 2, 4, 8, 16]
                    param_value = param_value if param_value in valid_rates else 4
                setattr(self, param_name, param_value)
