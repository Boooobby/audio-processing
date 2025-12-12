import numpy as np
from .base import AudioEffect  # 仅修正相对导入，适配项目结构


class HammingCodeEffect(AudioEffect):
    """
    基于汉明码(7,4)的信道编码音频处理器
    通信原理落地：模拟音频数字化后经带误码信道传输的纠错过程
    """

    def __init__(self):
        super().__init__(name="Hamming Code Effect")  # 仅新增父类初始化（满足项目规范）
        self.error_rate = 0.0001  # 信道误码率（模拟传输中的比特翻转概率）
        self.bit_depth = 16  # 音频采样量化位深（决定数字精度）
        self._quant_max = 2 ** (self.bit_depth - 1) - 1  # 量化最大值

    def _hamming_7_4_encode(self, data_bits):
        """
        手搓汉明码(7,4)编码（通信原理标准算法）
        输入：4位数据位 [d1,d2,d3,d4]
        输出：7位编码 [p1,p2,d1,p3,d2,d3,d4]（p为校验位）
        """
        if len(data_bits) != 4:
            raise ValueError("汉明码(7,4)仅支持4位数据位输入")
        d1, d2, d3, d4 = data_bits

        # 通信原理中汉明码校验位计算公式（奇偶校验）
        p1 = d1 ^ d2 ^ d4  # p1 = d1+d2+d4 (模2)
        p2 = d1 ^ d3 ^ d4  # p2 = d1+d3+d4 (模2)
        p3 = d2 ^ d3 ^ d4  # p3 = d2+d3+d4 (模2)

        return [p1, p2, d1, p3, d2, d3, d4]

    def _hamming_7_4_decode(self, coded_bits):
        """
        手搓汉明码(7,4)解码+纠错（通信原理核心纠错逻辑）
        输入：7位编码位（可能含1位误码）
        输出：4位纠正后的数据位 [d1,d2,d3,d4]
        """
        if len(coded_bits) != 7:
            raise ValueError("汉明码(7,4)仅支持7位编码位输入")
        p1, p2, d1, p3, d2, d3, d4 = coded_bits

        # 计算校验位（伴随式）
        s1 = p1 ^ d1 ^ d2 ^ d4
        s2 = p2 ^ d1 ^ d3 ^ d4
        s3 = p3 ^ d2 ^ d3 ^ d4

        # 定位错误位置（s3s2s1为二进制位置，转十进制）
        error_pos = s3 * 4 + s2 * 2 + s1 * 1
        if error_pos != 0:  # 有错误则翻转对应位
            coded_bits[error_pos - 1] = 1 - coded_bits[error_pos - 1]
            # 重新提取纠正后的数据位
            p1, p2, d1, p3, d2, d3, d4 = coded_bits

        return [d1, d2, d3, d4]

    def _audio2bits(self, audio):
        """极简版：音频转比特流"""
        # 归一化+量化为整数
        audio_quant = np.clip(audio * self._quant_max, -self._quant_max, self._quant_max).astype(np.int16)
        # 转二进制比特流（补零到指定位深）
        bits = []
        for val in audio_quant:
            bin_str = bin(val & 0xFFFF)[2:].zfill(self.bit_depth)  # 16位补码
            bits.extend([int(b) for b in bin_str])
        return np.array(bits)

    def _bits2audio(self, bits):
        """极简版：比特流转音频"""
        # 按位深拆分比特流
        bit_groups = np.reshape(bits[:len(bits) - (len(bits) % self.bit_depth)], (-1, self.bit_depth))
        audio = []
        for group in bit_groups:
            bin_str = ''.join([str(b) for b in group])
            val = int(bin_str, 2)
            if val >= 2**15:  # 处理符号位
                val -= 2**16
            audio.append(val / self._quant_max)
        return np.array(audio, dtype=np.float32)

    def _add_noise(self, bits):
        """极简版：模拟信道误码（比特翻转）"""
        noise = np.random.choice([0, 1], size=len(bits), p=[1-self.error_rate, self.error_rate])
        return (bits + noise) % 2  # 模2实现比特翻转

    # 仅补全process方法，匹配基类接口
    def process(self, audio, samplerate):
        """
        核心处理流程：音频→比特→编码→加噪→解码→还原音频
        :param audio: 输入音频（多通道），shape=(通道数, 采样点数)
        :param samplerate: 采样率（仅适配接口，无实际作用）
        :return: 处理后音频，shape与输入一致
        """
        processed = []
        for chan in audio:
            # 1. 音频转比特
            bits = self._audio2bits(chan)
            # 2. 补零使比特数为4的整数倍（适配汉明码4位分组）
            pad_len = (4 - len(bits) % 4) % 4
            bits_pad = np.pad(bits, (0, pad_len), 'constant')
            # 3. 汉明码编码（4→7位）
            coded = []
            for i in range(0, len(bits_pad), 4):
                coded.extend(self._hamming_7_4_encode(bits_pad[i:i+4].tolist()))
            # 4. 模拟信道误码
            coded_noise = self._add_noise(np.array(coded))
            # 5. 汉明码解码（7→4位）
            decoded = []
            for i in range(0, len(coded_noise), 7):
                decoded.extend(self._hamming_7_4_decode(coded_noise[i:i+7].tolist()))
            # 6. 去除补零+比特转音频
            decoded = decoded[:len(decoded)-pad_len] if pad_len else decoded
            chan_proc = self._bits2audio(np.array(decoded))
            # 裁剪到原长度（避免补零导致长度变化）
            processed.append(chan_proc[:len(chan)])
        return np.array(processed)
