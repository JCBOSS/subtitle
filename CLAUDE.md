# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## 项目概述

这是一个 **视频字幕自动生成流水线**，通过 Whisper 语音识别自动生成字幕并烧录到视频中。

### 核心功能

1. 视频音频提取 (ffmpeg)
2. Whisper 语音识别 → SRT 字幕
3. 字幕时间轴校准
4. 字幕质量评估
5. 字幕烧录到视频

---

## 飞书(cc-connect)集成

### `/subtitle` - 显示帮助

当收到 `/subtitle` 消息时，返回帮助信息：
```
字幕处理机器人使用说明：
1. 发送视频文件 → 自动添加字幕
2. 支持格式：mp4, avi, mov
3. 输出：带字幕的mp4视频
```

### 视频处理流程

当收到视频文件时：
1. 下载视频到 `/data/chunjiang/VideoEdit/subtitle/Input/`
2. 执行处理：
   ```bash
   cd /data/chunjiang/VideoEdit/subtitle && python pipeline.py <视频路径>
   ```
3. 找到输出视频 (`*_subtitled.mp4`) 并上传到飞书

### 文件大于 20MB

飞书限制单文件 20MB，超过时：
1. 使用飞书分片上传 API
2. 或提示用户压缩视频

---

## 常用命令

```bash
# 运行字幕流水线
python pipeline.py <视频文件路径>

# 仅提取音频
ffmpeg -i video.mp4 -vn -acodec pcm_s16le audio.wav

# 仅做语音识别
python -c "from skills.whisper_transcribe import transcribe; transcribe('audio.wav')"
```

---

## 流水线步骤

```
Step 1: 视频音频提取 → audio.wav
Step 2: Whisper语音识别 → raw_subtitles.srt
Step 3: 字幕时间轴校准 → aligned_subtitles.srt
Step 4: 字幕质量评估 → evaluation_report.json
Step 5: 字幕格式导出 → final_subtitles.srt
Step 6: 字幕烧录 + 音频导出 → *_subtitled.mp4
```

---

## 输出文件位置

处理完成后，视频保存在：`Audio/<原始文件名>_output/`
- `*_subtitled.mp4` - 带字幕的视频
- `*.srt` - 字幕文件
- `evaluation_report.json` - 质量评估报告

---

## 注意事项

- Whisper 模型首次使用会下载 (~500MB)
- 中文字幕使用 ASS 格式避免方块字
- FFmpeg 使用 imageio-ffmpeg 内置版本
