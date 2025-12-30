## 🛠 环境复现指南 (Environment Setup)

本项目推荐使用 **Conda** 进行一键配置，确保音频处理依赖（如 `ffmpeg`）及 Python 版本的兼容性。

### 基于 environment.yml 一键复现
请确保您已安装 Miniconda 或 Anaconda，并在项目根目录下执行：

```bash
# 1. 根据配置文件创建环境（这将自动处理 Python 3.9 及 ffmpeg 等所有依赖）
conda env create -f environment.yml

# 2. 激活环境
conda activate commscape
```

---

## 🚀 如何运行 (Usage)

**启动程序**：

```bash
python main.py
```
