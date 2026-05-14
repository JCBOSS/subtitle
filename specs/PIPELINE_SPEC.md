# 视频字幕编辑流水线 - 技术规格书

## 1. 项目概述

- **项目名称**: VideoSubtitle Pipeline
- **核心功能**: 自动视频字幕生成、编辑、评估一体化流水线
- **目标用户**: 视频编辑师、内容创作者

## 2. 技术栈

| 组件 | 技术 | 备注 |
|------|------|------|
| 语音识别 | Whisper Medium | openai/whisper |
| 字幕编辑 | python-srt + VTT处理 | SubtitleEdit替代方案 |
| 评估系统 | 多维度评分算法 | BLEU/编辑距离/时间对齐 |
| 流水线编排 | Claude Code Skills | 步骤串联 |

## 3. 流水线步骤

```
Step 1: 视频音频提取 → audio.wav
Step 2: Whisper语音识别 → raw_subtitles.srt
Step 3: 字幕时间轴校准 → aligned_subtitles.srt
Step 4: 字幕质量评估 → evaluation_report.json
Step 5: 字幕格式导出 → final_subtitles.{srt|vtt}
Step 6: 字幕烧录 + 音频导出 → {video}_subtitled.mp4 + extracted_audio.wav
```

## 4. 评估维度

| 维度 | 权重 | 评分范围 |
|------|------|----------|
| 准确率 (Accuracy) | 40% | 0-100 |
| 时间轴对齐 (Timing) | 30% | 0-100 |
| 格式规范 (Format) | 15% | 0-100 |
| 完整度 (Completeness) | 15% | 0-100 |

## 6. 字幕烧录说明

| 问题 | 解决方案 |
|------|----------|
| SRT直接烧录显示方块 | 转换为ASS格式，使用Arial字体 |
| 字幕位置偏移 | ASS格式Alignment=2 (底部居中) |
| 中文字符渲染 | Encoding=1 (UTF-8) |

### FFmpeg ASS烧录命令
```bash
ffmpeg -i input.mp4 -vf "ass='subtitle.ass'" -c:a copy output.mp4
```

| 风险项 | 级别 | 缓解措施 |
|--------|------|----------|
| 无GPU加速 | 🔴 高 | 使用CPU模式，fp16=False，模型用small/medium |
| Whisper模型大 | 🟡 中 | 分阶段下载，CPU用small模型(244MB) |
| 内存限制 | 🟡 中 | 限制音频chunk大小 |
| FFmpeg缺失 | 🟡 中 | 使用imageio-ffmpeg(内置FFmpeg) |

## 6. 输出格式

- SRT (SubRip)
- VTT (WebVTT)
- JSON (结构化数据)
