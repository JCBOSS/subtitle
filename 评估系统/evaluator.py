#!/usr/bin/env python3
"""
字幕质量评估系统
多维度评分算法
"""

import re
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class EvaluationResult:
    total_score: float
    dimensions: Dict[str, float]
    issues: List[str]


def levenshtein_distance(s1: str, s2: str) -> int:
    """计算两个字符串之间的编辑距离"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def parse_srt(content: str) -> List[Dict]:
    """解析SRT字幕文件"""
    subtitles = []
    blocks = re.split(r'\n\n+', content.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                index = int(lines[0])
                timecode = lines[1]
                text = '\n'.join(lines[2:])

                # 解析时间码: 00:00:00,000 --> 00:00:00,000
                match = re.match(
                    r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})',
                    timecode
                )
                if match:
                    start = (int(match.group(1))*3600 + int(match.group(2))*60 +
                            int(match.group(3)) + int(match.group(4))/1000)
                    end = (int(match.group(5))*3600 + int(match.group(6))*60 +
                          int(match.group(7)) + int(match.group(8))/1000)

                    subtitles.append({
                        'index': index,
                        'start': start,
                        'end': end,
                        'duration': end - start,
                        'text': text
                    })
            except (ValueError, IndexError):
                continue

    return subtitles


def evaluate_accuracy(subtitles: List[Dict], reference: str = None) -> Tuple[float, List[str]]:
    """评估准确率"""
    issues = []

    # 检查字幕文本是否为空
    for sub in subtitles:
        if not sub['text'].strip():
            issues.append(f"字幕#{sub['index']} 文本为空")

    if not subtitles:
        return 0.0, ["无字幕数据"]

    # 基础评分：文本完整性
    empty_count = sum(1 for sub in subtitles if not sub['text'].strip())
    completeness_ratio = 1 - (empty_count / len(subtitles))
    score = completeness_ratio * 100

    return round(score, 2), issues


def evaluate_timing(subtitles: List[Dict]) -> Tuple[float, List[str]]:
    """评估时间轴对齐"""
    issues = []
    total = len(subtitles)

    if total == 0:
        return 0.0, ["无字幕数据"]

    abnormal_count = 0

    for i, sub in enumerate(subtitles):
        # 检查时长是否合理 (0.5s - 10s)
        if sub['duration'] < 0.5:
            issues.append(f"字幕#{sub['index']} 时长过短 ({sub['duration']:.2f}s)")
            abnormal_count += 1
        elif sub['duration'] > 10:
            issues.append(f"字幕#{sub['index']} 时长过长 ({sub['duration']:.2f}s)")
            abnormal_count += 1

        # 检查是否与下一字幕重叠
        if i < total - 1:
            next_sub = subtitles[i + 1]
            if sub['end'] > next_sub['start']:
                issues.append(f"字幕#{sub['index']} 与 #{next_sub['index']} 时间重叠")
                abnormal_count += 1

    normal_ratio = 1 - (abnormal_count / total)
    score = normal_ratio * 100

    return round(score, 2), issues


def evaluate_format(content: str) -> Tuple[float, List[str]]:
    """评估格式规范"""
    issues = []

    # 检查SRT基本格式
    blocks = re.findall(r'\d+\n\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}', content)

    if not blocks:
        return 0.0, ["未找到有效的SRT时间码格式"]

    # 检查是否有连续的索引号
    indices = re.findall(r'^(?=\d)[\s]*(\d+)', content, re.MULTILINE)
    expected = list(range(1, len(indices) + 1))
    actual = [int(i) for i in indices]

    if actual != expected:
        issues.append("字幕索引号不连续")

    # 检查编码（基本ASCII检查）
    try:
        content.encode('utf-8')
    except UnicodeEncodeError:
        issues.append("编码错误")

    score = max(0, 100 - len(issues) * 20)
    return round(score, 2), issues


def evaluate_completeness(subtitles: List[Dict], video_duration: float = None) -> Tuple[float, List[str]]:
    """评估完整度"""
    issues = []

    if not subtitles:
        return 0.0, ["无字幕数据"]

    # 计算字幕总时长
    total_sub_duration = sum(sub['duration'] for sub in subtitles)

    # 如果知道视频总时长，计算覆盖率
    if video_duration and video_duration > 0:
        coverage = (total_sub_duration / video_duration) * 100
        if coverage < 50:
            issues.append(f"字幕覆盖率过低 ({coverage:.1f}%)")
        score = min(100, coverage * 1.2)  # 放大系数使评分更合理
    else:
        # 基于平均字幕时长的评分
        avg_duration = total_sub_duration / len(subtitles)
        score = min(100, avg_duration * 20)

    return round(score, 2), issues


def evaluate_subtitle(content: str, video_duration: float = None) -> EvaluationResult:
    """
    综合评估字幕质量

    Args:
        content: SRT字幕文件内容
        video_duration: 视频总时长(秒)，可选

    Returns:
        EvaluationResult: 包含总分、各维度得分和问题列表
    """
    subtitles = parse_srt(content)

    # 各维度评估
    accuracy, a_issues = evaluate_accuracy(subtitles)
    timing, t_issues = evaluate_timing(subtitles)
    format_score, f_issues = evaluate_format(content)
    completeness, c_issues = evaluate_completeness(subtitles, video_duration)

    # 收集所有问题
    all_issues = a_issues + t_issues + f_issues + c_issues

    # 计算加权总分
    total_score = (
        accuracy * 0.4 +
        timing * 0.3 +
        format_score * 0.15 +
        completeness * 0.15
    )

    return EvaluationResult(
        total_score=round(total_score, 2),
        dimensions={
            'accuracy': accuracy,
            'timing': timing,
            'format': format_score,
            'completeness': completeness
        },
        issues=all_issues
    )


def format_report(result: EvaluationResult) -> str:
    """格式化评估报告"""
    report = []
    report.append("=" * 50)
    report.append("          字幕质量评估报告")
    report.append("=" * 50)
    report.append(f"\n综合评分: {result.total_score}/100")
    report.append("\n各维度得分:")
    for dim, score in result.dimensions.items():
        report.append(f"  - {dim}: {score}/100")
    report.append("\n问题列表:")
    if result.issues:
        for issue in result.issues:
            report.append(f"  ⚠ {issue}")
    else:
        report.append("  ✓ 未发现问题")
    report.append("=" * 50)
    return "\n".join(report)


if __name__ == "__main__":
    # 测试代码
    sample_srt = """1
00:00:00,000 --> 00:00:03,500
欢迎观看本期视频

2
00:00:03,500 --> 00:00:07,200
今天我们将介绍

3
00:00:07,200 --> 00:00:12,000
人工智能的最新发展
"""
    result = evaluate_subtitle(sample_srt, video_duration=12.0)
    print(format_report(result))
    print("\nJSON格式:")
    print(json.dumps({
        'total_score': result.total_score,
        'dimensions': result.dimensions,
        'issues': result.issues
    }, ensure_ascii=False, indent=2))
