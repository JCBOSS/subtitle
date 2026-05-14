---
name: export
description: 导出字幕为多种格式
type: skill
---

# Export Skill

## 功能
将字幕导出为多种格式

## 支持格式
- SRT (SubRip) - 默认
- VTT (WebVTT)
- JSON (结构化数据)
- ASS (Advanced SubStation Alpha)

## 输入
- `subtitle_path`: 字幕文件路径
- `output_format`: 导出格式 (srt/vtt/json/ass)
- `output_path`: 输出文件路径

## 命令
```python
# SRT → VTT 转换
# 简单时间戳格式转换
# 添加WEBVTT header
```

## 编码
- UTF-8 无 BOM
- 兼容中文显示

## 新增：字幕烧录 (Step 6)

### 功能
将字幕烧录到原视频，生成带字幕的新视频

### 输入
- `video_path`: 原始视频路径
- `subtitle_path`: SRT格式字幕路径

### 输出
- `{video_name}_subtitled.mp4`: 带字幕的视频
- `extracted_audio.wav`: 提取的音频文件

### FFmpeg命令
```bash
# 烧录字幕 (SRT格式)
ffmpeg -i input.mp4 -vf subtitles='subtitle.srt' -c:a copy output.mp4

# 烧录字幕 (ASS格式)
ffmpeg -i input.mp4 -vf ass='subtitle.ass' -c:a copy output.mp4
```

### 注意事项
- 字幕滤镜需要FFmpeg编译时支持libass
- 音频保持原始编码 COPY
- 视频编码为H.264
