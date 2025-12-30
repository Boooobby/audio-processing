import numpy as np
from .base import AudioEffect

class HammingCodeEffect(AudioEffect):
    """基于汉明码(7,4)的信道编码音频处理器"""

    def __init__(self):
        super().__init__(name="Hamming Code Effect")
        self.error_rate = 0.0001
        self.bit_depth = 16
        self._int16_min = -32768
        self._int16_max = 32767
        self._chunk_size = 1000

    def _hamming_7_4_encode(self, data_bits):
        """汉明码(7,4)编码"""
        if len(data_bits) != 4:
            raise ValueError("汉明码(7,4)仅支持4位数据位输入")
        d1, d2, d3, d4 = data_bits

        p1 = d1 ^ d2 ^ d4
        p2 = d1 ^ d3 ^ d4
        p3 = d2 ^ d3 ^ d4

        return [p1, p2, d1, p3, d2, d3, d4]

    def _hamming_7_4_decode(self, coded_bits):
        """汉明码(7,4)解码+纠错"""
        if len(coded_bits) != 7:
            raise ValueError("汉明码(7,4)仅支持7位编码位输入")

        # 创建副本以避免修改原数据
        bits = coded_bits.copy()
        p1, p2, d1, p3, d2, d3, d4 = bits

        s1 = p1 ^ d1 ^ d2 ^ d4
        s2 = p2 ^ d1 ^ d3 ^ d4
        s3 = p3 ^ d2 ^ d3 ^ d4

        error_pos = s3 * 4 + s2 * 2 + s1 * 1
        if error_pos != 0 and error_pos <= 7:
            bits[error_pos - 1] = 1 - bits[error_pos - 1]
            # 重新赋值
            p1, p2, d1, p3, d2, d3, d4 = bits

        return [d1, d2, d3, d4]

    def _audio2bits_safe(self, audio):
        """音频转比特流 - 安全版本"""
        # 确保输入在有效范围内
        if audio.dtype == np.float32:
            audio = np.clip(audio, -1.0, 1.0).astype(np.float32)
            # 转换为int16范围
            audio_int = np.clip(audio * 32767, self._int16_min, self._int16_max).astype(np.int32)
        else:
            audio_int = np.clip(audio, self._int16_min, self._int16_max).astype(np.int32)

        bits = []
        # 分块处理避免内存溢出
        for i in range(0, len(audio_int), self._chunk_size):
            chunk = audio_int[i:i + self._chunk_size]
            chunk_bits = np.zeros((len(chunk), 16), dtype=np.uint8)

            # 向量化操作提高性能
            for j in range(16):
                chunk_bits[:, 15 - j] = (chunk >> j) & 1

            bits.extend(chunk_bits.flatten())

        return np.array(bits, dtype=np.uint8)

    def _bits2audio_safe(self, bits):
        """比特流转音频 - 安全版本"""
        # 确保比特数是16的倍数
        if len(bits) % 16 != 0:
            pad_len = 16 - (len(bits) % 16)
            bits = np.pad(bits, (0, pad_len), 'constant')

        num_samples = len(bits) // 16
        audio_int = np.zeros(num_samples, dtype=np.int32)

        # 向量化操作
        bits_reshaped = bits.reshape(-1, 16)

        for i in range(num_samples):
            bit_group = bits_reshaped[i]
            # 构建16位整数
            val = 0
            for bit in bit_group:
                val = (val << 1) | int(bit)

            # 转换为有符号整数
            if val & 0x8000:
                val -= 65536

            audio_int[i] = np.clip(val, self._int16_min, self._int16_max)

        # 转换为float32
        audio_float = audio_int.astype(np.float32) / 32768.0
        audio_float = np.clip(audio_float, -1.0, 1.0).astype(np.float32)

        return audio_float

    def _add_noise(self, bits):
        """模拟信道误码"""
        if self.error_rate <= 0:
            return bits.copy()

        noise = np.random.choice([0, 1], size=len(bits),
                                 p=[1 - self.error_rate, self.error_rate])
        return (bits + noise) % 2

    def process(self, audio, samplerate):
        """核心处理流程"""
        try:
            # 保存原始信息
            original_shape = audio.shape
            original_dtype = audio.dtype

            # 确保是二维数组
            if audio.ndim == 1:
                audio = audio.reshape(1, -1)

            processed_channels = []

            for chan_idx, chan in enumerate(audio):
                # 1. 音频转比特
                bits = self._audio2bits_safe(chan)

                # 2. 补零使比特数为4的整数倍
                orig_len = len(bits)
                pad_len = (4 - orig_len % 4) % 4
                bits_pad = np.pad(bits, (0, pad_len), 'constant')

                # 3. 汉明码编码
                coded = []
                num_groups = len(bits_pad) // 4
                for i in range(num_groups):
                    start_idx = i * 4
                    coded.extend(self._hamming_7_4_encode(bits_pad[start_idx:start_idx + 4].tolist()))

                # 4. 模拟信道误码
                coded_noise = self._add_noise(np.array(coded, dtype=np.uint8))

                # 5. 汉明码解码
                decoded = []
                num_coded_groups = len(coded_noise) // 7
                for i in range(num_coded_groups):
                    start_idx = i * 7
                    decoded.extend(self._hamming_7_4_decode(coded_noise[start_idx:start_idx + 7].tolist()))

                # 6. 去除补零
                decoded = decoded[:orig_len]

                # 7. 比特转音频
                chan_proc = self._bits2audio_safe(np.array(decoded, dtype=np.uint8))

                # 裁剪到原长度
                target_len = min(len(chan_proc), len(chan))
                processed_channels.append(chan_proc[:target_len])

            # 合并通道
            if len(processed_channels) == 1:
                result = processed_channels[0]
            else:
                result = np.vstack(processed_channels)

            # 恢复原始形状
            if len(original_shape) == 1:
                result = result.flatten()

            # 确保输出类型和长度匹配
            result = result.astype(np.float32)
            if result.shape != original_shape:
                result = result.reshape(original_shape)

            return result

        except Exception as e:
            print(f"汉明码处理错误：{e}，返回原始音频")
            return audio.astype(np.float32) if audio.dtype != np.float32 else audio


class CRC32Effect(AudioEffect):
    """CRC32冗余校验器"""

    def __init__(self):
        super().__init__(name="CRC32 Check")
        self.polynomial = 0xEDB88320
        self.crc_length = 32
        self.error_rate = 0.0001
        self._int16_min = -32768
        self._int16_max = 32767
        self.bit_depth = 16
        self._chunk_size = 1000

    def _crc32_encode(self, data_bits):
        """对数据比特流附加32位CRC校验位"""
        crc = 0xFFFFFFFF
        for bit in data_bits:
            bit_int = int(bit)
            crc = (crc >> 1) ^ self.polynomial if ((crc ^ bit_int) & 1) else crc >> 1
        crc ^= 0xFFFFFFFF

        crc_bits = [(crc >> i) & 1 for i in range(self.crc_length - 1, -1, -1)]
        return np.concatenate([data_bits, crc_bits])

    def _crc32_check(self, coded_bits):
        """校验CRC校验位"""
        if len(coded_bits) < self.crc_length:
            return False, coded_bits

        data_bits = coded_bits[:-self.crc_length]
        crc_bits = coded_bits[-self.crc_length:]

        # 重新计算CRC
        crc = 0xFFFFFFFF
        for bit in data_bits:
            bit_int = int(bit)
            crc = (crc >> 1) ^ self.polynomial if ((crc ^ bit_int) & 1) else crc >> 1
        crc ^= 0xFFFFFFFF

        computed_crc = [(crc >> i) & 1 for i in range(self.crc_length - 1, -1, -1)]
        is_valid = np.array_equal(computed_crc, crc_bits)
        return is_valid, data_bits

    def _add_noise(self, bits):
        """模拟信道误码"""
        if self.error_rate <= 0:
            return bits.copy()

        noise = np.random.choice([0, 1], size=len(bits),
                                 p=[1 - self.error_rate, self.error_rate])
        return (bits + noise) % 2

    def _audio2bits_safe(self, audio):
        """音频转比特流：安全版"""
        if audio.dtype == np.float32:
            audio = np.clip(audio, -1.0, 1.0).astype(np.float32)
            audio_int = np.clip(audio * 32767, self._int16_min, self._int16_max).astype(np.int32)
        else:
            audio_int = np.clip(audio, self._int16_min, self._int16_max).astype(np.int32)

        bits = []
        for i in range(0, len(audio_int), self._chunk_size):
            chunk = audio_int[i:i + self._chunk_size]
            chunk_bits = np.zeros((len(chunk), 16), dtype=np.uint8)

            for j in range(16):
                chunk_bits[:, 15 - j] = (chunk >> j) & 1

            bits.extend(chunk_bits.flatten())

        return np.array(bits, dtype=np.uint8)

    def _bits2audio_safe(self, bits):
        """比特流转音频"""
        if len(bits) % 16 != 0:
            pad_len = 16 - (len(bits) % 16)
            bits = np.pad(bits, (0, pad_len), 'constant')

        num_samples = len(bits) // 16
        audio_int = np.zeros(num_samples, dtype=np.int32)

        bits_reshaped = bits.reshape(-1, 16)

        for i in range(num_samples):
            bit_group = bits_reshaped[i]
            val = 0
            for bit in bit_group:
                val = (val << 1) | int(bit)

            if val & 0x8000:
                val -= 65536

            audio_int[i] = np.clip(val, self._int16_min, self._int16_max)

        audio_float = audio_int.astype(np.float32) / 32768.0
        audio_float = np.clip(audio_float, -1.0, 1.0).astype(np.float32)

        return audio_float

    def process(self, audio, samplerate):
        """CRC32处理流程"""
        try:
            original_shape = audio.shape

            if audio.ndim == 1:
                audio = audio.reshape(1, -1)

            processed_channels = []

            for chan in audio:
                bits = self._audio2bits_safe(chan)
                crc_coded = self._crc32_encode(bits)
                coded_noise = self._add_noise(crc_coded)
                is_valid, after_crc = self._crc32_check(coded_noise)

                if not is_valid:
                    print("CRC校验失败，存在未纠正错误")

                chan_proc = self._bits2audio_safe(after_crc)
                # 确保输出长度匹配
                target_len = min(len(chan_proc), len(chan))
                processed_channels.append(chan_proc[:target_len])

            if len(processed_channels) == 1:
                result = processed_channels[0]
            else:
                result = np.vstack(processed_channels)

            if len(original_shape) == 1:
                result = result.flatten()

            result = result.astype(np.float32)
            # 确保形状匹配
            if result.shape != original_shape:
                result = result.reshape(original_shape)

            return result

        except Exception as e:
            print(f"CRC32处理错误：{e}，返回原始音频")
            return audio.astype(np.float32) if audio.dtype != np.float32 else audio


class CombinedChannelCodeEffect(AudioEffect):
    """组合信道编码：汉明码（前向纠错）+ CRC（结尾校验）"""

    def __init__(self):
        super().__init__(name="Hamming + CRC Code")
        self.hamming = HammingCodeEffect()
        self.crc = CRC32Effect()
        self._int16_min = -32768
        self._int16_max = 32767
        self.error_rate = 0.0001

    def process(self, audio, samplerate):
        try:
            original_shape = audio.shape

            if audio.ndim == 1:
                audio = audio.reshape(1, -1)

            processed_channels = []

            for chan in audio:
                # 1. 音频转比特
                bits = self.hamming._audio2bits_safe(chan)

                # 2. 汉明码编码
                orig_len = len(bits)
                pad_len = (4 - orig_len % 4) % 4
                bits_pad = np.pad(bits, (0, pad_len), 'constant')

                hamming_coded = []
                num_groups = len(bits_pad) // 4
                for i in range(num_groups):
                    start_idx = i * 4
                    hamming_coded.extend(self.hamming._hamming_7_4_encode(bits_pad[start_idx:start_idx + 4].tolist()))
                hamming_coded = np.array(hamming_coded, dtype=np.uint8)

                # 3. CRC编码
                crc_coded = self.crc._crc32_encode(hamming_coded)

                # 4. 加噪
                noise = np.random.choice([0, 1], size=len(crc_coded),
                                         p=[1 - self.error_rate, self.error_rate])
                coded_noise = (crc_coded + noise) % 2

                # 5. CRC校验
                is_valid, after_crc = self.crc._crc32_check(coded_noise)
                if not is_valid:
                    print("CRC校验失败")

                # 6. 汉明码解码
                decoded = []
                num_coded_groups = len(after_crc) // 7
                for i in range(num_coded_groups):
                    start_idx = i * 7
                    decoded.extend(self.hamming._hamming_7_4_decode(after_crc[start_idx:start_idx + 7].tolist()))

                # 确保解码后的长度正确
                decoded = decoded[:orig_len]

                # 7. 转回音频
                chan_proc = self.hamming._bits2audio_safe(np.array(decoded, dtype=np.uint8))

                # 裁剪到原长度
                target_len = min(len(chan_proc), len(chan))
                processed_channels.append(chan_proc[:target_len])

            if len(processed_channels) == 1:
                result = processed_channels[0]
            else:
                result = np.vstack(processed_channels)

            if len(original_shape) == 1:
                result = result.flatten()

            result = result.astype(np.float32)
            if result.shape != original_shape:
                result = result.reshape(original_shape)

            return result

        except Exception as e:
            print(f"组合编码处理错误：{e}，返回原始音频")
            return audio.astype(np.float32) if audio.dtype != np.float32 else audio


class HammingEncoder(AudioEffect):
    """独立汉明编码器：音频 → 编码比特流"""

    def __init__(self, error_rate=0.0001):
        super().__init__(name="Hamming Encoder")
        self.error_rate = error_rate
        self._int16_min = -32768
        self._int16_max = 32767
        self._chunk_size = 1000

    def _audio2bits(self, audio):
        """音频转比特流"""
        if audio.dtype == np.float32:
            audio = np.clip(audio, -1.0, 1.0).astype(np.float32)
            audio_int = np.clip(audio * 32767, self._int16_min, self._int16_max).astype(np.int32)
        else:
            audio_int = np.clip(audio, self._int16_min, self._int16_max).astype(np.int32)

        bits = []
        for i in range(0, len(audio_int), self._chunk_size):
            chunk = audio_int[i:i + self._chunk_size]
            chunk_bits = np.zeros((len(chunk), 16), dtype=np.uint8)

            for j in range(16):
                chunk_bits[:, 15 - j] = (chunk >> j) & 1

            bits.extend(chunk_bits.flatten())

        return np.array(bits, dtype=np.uint8)

    def _hamming_encode_only(self, bits):
        """只编码，不添加噪声"""
        orig_len = len(bits)
        pad_len = (4 - orig_len % 4) % 4
        bits_pad = np.pad(bits, (0, pad_len), 'constant')

        coded = []
        num_groups = len(bits_pad) // 4
        for i in range(num_groups):
            start_idx = i * 4
            d1, d2, d3, d4 = bits_pad[start_idx:start_idx + 4]
            p1 = d1 ^ d2 ^ d4
            p2 = d1 ^ d3 ^ d4
            p3 = d2 ^ d3 ^ d4
            coded.extend([p1, p2, d1, p3, d2, d3, d4])

        # 计算实际输出长度
        output_len = orig_len * 7 // 4
        return np.array(coded[:output_len], dtype=np.uint8)

    def process(self, audio, samplerate):
        """输入音频，输出编码后的比特流"""
        print("🔢 汉明编码器：音频 → 编码比特流")
        bits = self._audio2bits(audio.flatten())
        encoded = self._hamming_encode_only(bits)
        print(f"   编码完成：{len(bits)}位 → {len(encoded)}位")
        return encoded


class HammingDecoder(AudioEffect):
    """独立汉明解码器：编码比特流 → 音频"""

    def __init__(self, error_rate=0.0001):
        super().__init__(name="Hamming Decoder")
        self.error_rate = error_rate
        self._chunk_size = 1000
        self._int16_min = -32768
        self._int16_max = 32767

    def _hamming_decode_only(self, coded_bits):
        """只解码，不添加噪声"""
        decoded = []

        # 确保输入长度是7的倍数
        if len(coded_bits) % 7 != 0:
            pad_len = 7 - (len(coded_bits) % 7)
            coded_bits = np.pad(coded_bits, (0, pad_len), 'constant')

        num_groups = len(coded_bits) // 7
        for i in range(num_groups):
            start_idx = i * 7
            group = coded_bits[start_idx:start_idx + 7]

            if len(group) < 7:
                break

            p1, p2, d1, p3, d2, d3, d4 = group

            # 计算伴随式
            s1 = p1 ^ d1 ^ d2 ^ d4
            s2 = p2 ^ d1 ^ d3 ^ d4
            s3 = p3 ^ d2 ^ d3 ^ d4

            # 纠错
            error_pos = s3 * 4 + s2 * 2 + s1 * 1
            if error_pos != 0 and error_pos <= 7:
                # 在本地副本上纠错
                group = group.copy()
                group[error_pos - 1] = 1 - group[error_pos - 1]
                p1, p2, d1, p3, d2, d3, d4 = group

            decoded.extend([d1, d2, d3, d4])

        return np.array(decoded, dtype=np.uint8)

    def _bits2audio(self, bits):
        """比特流转音频"""
        if len(bits) % 16 != 0:
            pad_len = 16 - (len(bits) % 16)
            bits = np.pad(bits, (0, pad_len), 'constant')

        num_samples = len(bits) // 16
        audio = np.zeros(num_samples, dtype=np.float32)

        bits_reshaped = bits.reshape(-1, 16)

        for i in range(num_samples):
            bit_group = bits_reshaped[i]
            val = 0
            for bit in bit_group:
                val = (val << 1) | int(bit)

            if val & 0x8000:
                val -= 65536

            audio[i] = np.clip(val / 32768.0, -1.0, 1.0)

        return audio

    def process(self, coded_bits, samplerate):
        """输入编码比特流，输出解码音频"""
        print("汉明解码器：编码比特流 → 音频")
        decoded_bits = self._hamming_decode_only(coded_bits)
        audio = self._bits2audio(decoded_bits)
        print(f"   解码完成：{len(coded_bits)}位 → {len(audio)}采样点")
        return audio