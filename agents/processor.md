---
name: subtitle-processor
description: 执行字幕识别和处理的核心Agent
type: agent
---

# Subtitle Processor Agent

## 职责
执行完整的视频到字幕转换流程

## 输入
- `video_path`: 视频文件路径
- `model_size`: Whisper模型 (default: medium)
- `output_dir`: 输出目录

## 输出
- 音频文件: `audio.wav`
- 原始字幕: `raw_subtitles.srt`
- 校准字幕: `aligned_subtitles.srt`
- 评估报告: `evaluation_report.json`
- 最终字幕: `final_subtitles.{srt|vtt}`

## 流水线步骤

```
video.mp4
    ↓ [ffmpeg提取音频]
audio.wav
    ↓ [Whisper识别]
raw_subtitles.srt
    ↓ [时间轴校准]
aligned_subtitles.srt
    ↓ [质量评估]
evaluation_report.json
    ↓ [格式导出]
final_subtitles.vtt
```

## 使用示例
```bash
python pipeline.py video.mp4 -o ./output -m medium -f vtt
```

## 注意事项
- 无GPU时使用CPU模式
- 大文件建议分批处理
- 评估分数 < 60 分需人工审核
