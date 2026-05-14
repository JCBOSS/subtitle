---
name: subtitle-align
description: 校准字幕时间轴确保与视频同步
type: skill
---

# Subtitle Align Skill

## 功能
检查并校准字幕时间轴，确保与视频同步

## 输入
- `subtitle_path`: 原始字幕文件
- `video_path`: 原始视频文件（用于参考）

## 输出
- `aligned_subtitle_path`: 校准后的字幕文件

## 校准规则
1. 检测字幕是否超出视频时长
2. 检查字幕间隔是否合理 (>0.3s)
3. 合并过短的字幕片段 (<1s)
4. 修复重叠时间轴

## 依赖
- pysrt
- srt 库
