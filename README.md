# 🎵 RetroAudio FX - 音频风格化处理工具

> **通信原理课程设计项目** | 基于 Python 的数字音频信号处理 (DSP) 原型工具

本项目是一个模块化的音频处理流水线（Pipeline），旨在模拟模拟时代（Analog Era）的音频特征。通过数字信号处理算法（DSP），将现代高清数字音频转换为具有 **磁带（Tape）**、**黑胶（Vinyl）** 或 **老式广播（AM Radio）** 风格的音频。

---

## ✨ 项目亮点

*   **OOP 架构设计**：采用**策略模式（Strategy Pattern）**与**多态**，每个效果器均为独立原子模块，高内聚低耦合。
*   **通信原理实践**：
    *   使用 **AWGN (加性高斯白噪声)** 模拟信道底噪。
    *   使用 **脉冲噪声 (Impulse Noise)** 模拟黑胶爆豆声。
    *   使用 **带通滤波** 模拟信道带宽受限。
*   **混合处理引擎**：结合了 **Numpy** (纯数学矩阵运算) 与 **Pedalboard** (VST 级别的音频插件算法)。
*   **灵活的流水线**：支持 `Pre-processing` (前处理/去水印) 与 `Post-processing` (风格化) 分离。

---

## 📂 项目结构

```text
Project/
├── main.py              # 程序入口 / 配置中心
├── pipeline.py          # 核心流水线管理器 (Pipeline Manager)
├── audio_loader.py      # 音频解码 (MP3 -> WAV)
├── audio_exporter.py    # 音频编码与导出 (WAV -> MP3 -> HTML)
├── modules/             # [核心算法包]
│   ├── base.py          # 抽象基类 (Interface)
│   ├── styles.py        # 风格化效果 (Tape, Vinyl, Radio Class)
│   ├── cleaners.py      # 清理效果 (去水印/降噪)
│   └── normalizer.py    # 归一化工具 (安全限制器)
├── temp_audio/          # 过程文件临时存储
├── output_audio/        # 处理结果输出
└── environment.yml      # 依赖环境配置
```

---

## 🛠️ 安装与配置

### 1. 环境依赖

本项目依赖 `ffmpeg` 进行音频编解码，请确保系统已安装。

*   **Python 依赖**:见 `environment.yml`
    *   `numpy`: 矩阵运算与噪声生成
    *   `pedalboard`: 音频效果链
    *   `pydub`: 音频格式转换

### 2. 安装步骤

```bash
# 1. 克隆项目
git clone [your-repo-url]

# 2. 创建并激活环境 (推荐使用 Conda)
conda env create -f environment.yml
conda activate audio-dsp

# 3. 确保系统安装了 FFmpeg (必须)
# Mac: brew install ffmpeg
# Windows: 下载 ffmpeg 并配置环境变量
```

---

## 🚀 快速开始 (Usage)

### 1. 运行主程序
将你的测试音频放入项目目录（或让程序自动生成静音测试），然后运行：

```bash
python main.py
```

程序将自动完成：解码 -> 前处理 -> 风格化 -> 归一化 -> 编码 -> 打开浏览器试听。

### 2. 自定义处理链 (在 `main.py` 中)

你可以像搭积木一样组合不同的效果：

```python
from effects.styles import TapeStyle, VinylStyle, RadioStyle
from effects.cleaners import VocalSuppressor
from effects.normalizer import Normalizer

# ...

# Step 1: 想要什么风格？
style_chain = [
    # 模拟一台很旧的收音机，然后被录到了磁带上
    RadioStyle(noise_level=0.02),
    TapeStyle(flutter=0.3),
    
    # 永远在最后加上归一化，防止爆音
    Normalizer(target_db=-1.0)
]

# Step 2: 需要去水印吗？
clean_chain = [
    VocalSuppressor() # 尝试压低人声频段的水印
]

# Step 3: 开始运行
pipeline.run(..., pre_processors=clean_chain, main_effects=style_chain)
```

---

## 🧠 核心原理实现

### 1. 磁带风格 (Tape Style)
*   **物理现象**：磁带电机转速不稳、磁粉饱和、高频丢失。
*   **DSP 实现**：
    *   利用 `Chorus` (合唱效果) 的 LFO 调制延迟时间，模拟 **Wow/Flutter (抖动)**。
    *   利用 `Distortion` (失真) 模拟 **磁饱和**。

### 2. 黑胶风格 (Vinyl Style)
*   **物理现象**：表面灰尘导致的随机爆音 (Crackles & Pops)。
*   **DSP 实现**：
    *   利用 **NumPy** 生成稀疏矩阵（随机脉冲）。
    *   数学模型：$y(t) = x(t) + n_{impulse}(t)$

### 3. AM 收音机 (Radio Style)
*   **通信原理**：信道带宽受限、热噪声。
*   **DSP 实现**：
    *   **带通滤波**：截取 300Hz - 3400Hz (典型电话/AM 频段)。
    *   **AWGN**：$y(t) = x(t) + \mathcal{N}(0, \sigma^2)$。

---

## 🔮 未来计划

*   [ ] **Web UI**: 使用 Flask/FastAPI 封装后端，提供可视化参数调节。
*   [ ] **AI 去水印**: 引入 Spleeter 或 Demucs 模型替代简单的 EQ 抑制，实现完美人声分离。
*   [ ] **频谱分析仪**: 在网页端实时展示处理前后的频谱图对比。
