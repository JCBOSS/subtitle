---
name: whisper-transcribe
description: 使用Whisper Medium进行语音识别生成字幕
type: skill
---

# Whisper Transcribe Skill

## 功能
使用 OpenAI Whisper Medium 模型将音频转为字幕

## 输入
- `audio_path`: 音频文件路径 (wav/mp3)

## 输出
- `subtitle_path`: SRT 格式字幕文件路径

## 模型配置
- model: medium
- device: cpu (无GPU环境)
- language: auto-detect

## 命令
```python
import whisper
model = whisper.load_model("medium")
result = model.transcribe(audio_path)
# 保存为SRT格式
```

## 依赖
- openai-whisper
- ffmpeg

## 风险
- 模型文件约 1.5GB
- CPU推理约需 10-30 分钟（取决于音频长度）
