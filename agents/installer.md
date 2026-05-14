---
name: subtitle-installer
description: 安装字幕处理流水线所需依赖
type: agent
---

# Subtitle Installer Agent

## 职责
负责安装和配置 Whisper、ffmpeg 等依赖

## 执行步骤

### 1. 检查系统环境
```bash
# 检查Python版本
python3 --version  # 需要 >= 3.8

# 检查磁盘空间 (需要至少 5GB)
df -h

# 检查内存 (需要至少 8GB)
free -h
```

### 2. 安装系统依赖
```bash
# Ubuntu/Debian
apt-get update && apt-get install -y ffmpeg

# 或使用 conda
conda install -y ffmpeg
```

### 3. 安装Python依赖
```bash
pip install openai-whisper
pip install srt pysrt
pip install torch torchaudio  # 已安装可跳过
```

### 4. 下载Whisper模型
```python
import whisper
# 首次运行时会自动下载模型
model = whisper.load_model("medium")
```

## 风险提示
- Whisper Medium 模型约 1.5GB
- CPU推理速度慢 (1分钟音频约需 2-5分钟处理)
- 建议优先使用 small 模型测试
