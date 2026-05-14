---
name: subtitle-evaluator
description: 评估字幕质量并生成报告
type: agent
---

# Subtitle Evaluator Agent

## 职责
对生成的字幕进行多维度质量评估

## 评估维度

| 维度 | 权重 | 说明 |
|------|------|------|
| accuracy | 40% | 文本准确率 (编辑距离) |
| timing | 30% | 时间轴对齐度 |
| format | 15% | 格式规范正确性 |
| completeness | 15% | 字幕完整度 |

## 评分标准

| 分数范围 | 等级 | 建议 |
|----------|------|------|
| 90-100 | A | 优秀，无需修改 |
| 75-89 | B | 良好，少量优化 |
| 60-74 | C | 一般，需审核 |
| <60 | D | 较差，需重做 |

## 输出格式
```json
{
  "total_score": 85.5,
  "grade": "B",
  "dimensions": {
    "accuracy": 88.2,
    "timing": 82.0,
    "format": 95.0,
    "completeness": 78.5
  },
  "issues": [
    "字幕#23时长过短",
    "字幕#45存在重叠"
  ],
  "recommendations": [
    "建议人工检查时间轴跳跃段落",
    "部分专业术语可能识别错误"
  ]
}
```

## 调用方式
```python
from evaluator import evaluate_subtitle, format_report

with open('subtitles.srt', 'r') as f:
    result = evaluate_subtitle(f.read(), video_duration=120.0)

print(format_report(result))
```
