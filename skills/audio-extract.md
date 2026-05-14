---
name: audio-extract
description: 从视频文件中提取音频流
type: skill
---

# Audio Extract Skill

## 功能
从视频文件提取音频并转换为 WAV 格式

## 输入
- `video_path`: 视频文件路径 (mp4/avi/mov/mkv)

## 输出
- `audio_path`: 提取的音频文件路径

## 命令
```bash
ffmpeg -i {video_path} -vn -acodec pcm_s16le -ar 16000 -ac 1 {audio_path}
```

## 依赖检查
- ffmpeg 必须已安装

## 错误处理
- 视频文件不存在 → 报错退出
- ffmpeg 未安装 → 提示安装
