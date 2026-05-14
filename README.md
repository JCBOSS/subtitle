# 视频字幕编辑流水线

基于 Whisper + 评估系统的自动化字幕处理流水线

## 目录结构

```
subtitle/
├── specs/                  # 技术规格文档
│   └── PIPELINE_SPEC.md
├── skills/                 # Skill定义 (可被Claude Code调用)
│   ├── audio-extract.md    # 音频提取技能
│   ├── whisper-transcribe.md # Whisper识别技能
│   ├── subtitle-align.md   # 时间轴校准技能
│   ├── evaluate.md         # 质量评估技能
│   └── export.md           # 格式导出技能
├── agents/                 # Agent定义
│   ├── installer.md        # 安装Agent
│   ├── processor.md        # 处理Agent
│   └── evaluator_agent.md  # 评估Agent
├── 评估系统/
│   └── evaluator.py        # 评估算法实现
└── 流水线/
    └── pipeline.py          # 流水线主程序
```

## 快速开始

### 1. 安装依赖

```bash
# 安装系统依赖
apt-get install ffmpeg

# 安装Python依赖
pip install openai-whisper srt pysrt
```

### 2. 运行流水线

```bash
# 基本用法
python 流水线/pipeline.py video.mp4 -o ./output

# 指定模型和格式
python 流水线/pipeline.py video.mp4 -m medium -f vtt
```

### 3. 查看评估结果

```bash
cat output/evaluation_report.json
```

## 流水线步骤

| 步骤 | Skill | 说明 |
|------|-------|------|
| 1 | audio-extract | ffmpeg 提取音频 |
| 2 | whisper-transcribe | Whisper 语音识别 |
| 3 | subtitle-align | 时间轴校准 |
| 4 | evaluate | 质量评估 |
| 5 | export | 格式导出 |

## 评估系统

评分公式:
```
总分 = 准确率×0.4 + 时间轴×0.3 + 格式×0.15 + 完整度×0.15
```

评分等级:
- A (90-100): 优秀
- B (75-89): 良好
- C (60-74): 一般
- D (<60): 较差

## 风险提示

1. **无GPU**: 当前服务器无NVIDIA GPU，使用CPU模式速度较慢
2. **模型大小**: Medium模型约1.5GB，首次运行需下载
3. **处理时间**: 1分钟视频约需2-5分钟处理
