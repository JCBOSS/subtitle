---
name: evaluate
description: 多维度评估字幕质量
type: skill
---

# Evaluate Skill - 字幕质量评估系统

## 功能
对生成的字幕进行多维度质量评估

## 评估维度

### 1. 准确率 (Accuracy) - 权重 40%
- 使用编辑距离(Levenshtein)计算文本相似度
- 评分公式: `100 * (1 - edit_distance / max_len)`

### 2. 时间轴对齐 (Timing) - 权重 30%
- 检查字幕时间戳是否连续
- 检测字幕时长是否合理 (0.5s - 10s)
- 评分: 异常字幕数量占比

### 3. 格式规范 (Format) - 权重 15%
- 检查SRT/VTT格式正确性
- 验证时间戳格式
- 检查中文字符编码

### 4. 完整度 (Completeness) - 权重 15%
- 检测空白/静音字幕片段
- 计算实际字幕覆盖率

## 输出
```json
{
  "total_score": 85.5,
  "dimensions": {
    "accuracy": 88.2,
    "timing": 82.0,
    "format": 95.0,
    "completeness": 78.5
  },
  "issues": ["字幕#23时长过短", "字幕#45存在重叠"]
}
```

## 综合评分公式
```
total = accuracy*0.4 + timing*0.3 + format*0.15 + completeness*0.15
```
