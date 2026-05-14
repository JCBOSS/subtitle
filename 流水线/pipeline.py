#!/usr/bin/env python3
"""
视频字幕编辑流水线
整合所有Skill步骤
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path

# 添加评估系统路径
sys.path.insert(0, str(Path(__file__).parent.parent / '评估系统'))
from evaluator import evaluate_subtitle, format_report


class SubtitlePipeline:
    """字幕处理流水线"""

    def __init__(self, work_dir: str = "./output"):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.steps = []
        self.results = {}

    def check_dependencies(self) -> bool:
        """检查系统依赖"""
        print("🔍 检查系统依赖...")

        deps = {
            'python3': 'python3 --version'
        }

        missing = []
        for name, cmd in deps.items():
            try:
                subprocess.run(cmd, shell=True, capture_output=True, check=True)
                print(f"  ✅ {name}")
            except subprocess.CalledProcessError:
                print(f"  ❌ {name} 未安装")
                missing.append(name)

        # 检查Python包
        python_deps = ['whisper', 'srt', 'pysrt', 'imageio_ffmpeg']
        for pkg in python_deps:
            try:
                __import__(pkg.replace('-', '_').replace('imageio_ffmpeg', 'imageio_ffmpeg'))
                print(f"  ✅ {pkg}")
            except ImportError:
                print(f"  ❌ {pkg} 未安装")
                missing.append(pkg)

        if missing:
            print(f"\n请安装缺失依赖: pip install {' '.join(missing)}")
            return False
        return True

    def step1_extract_audio(self, video_path: str) -> str:
        """Step 1: 提取音频 (使用imageio-ffmpeg，CPU模式)"""
        print("\n📥 Step 1: 提取音频...")
        video_path = Path(video_path)
        audio_path = self.work_dir / "audio.wav"

        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        cmd = [
            ffmpeg_path, '-i', str(video_path),
            '-vn', '-acodec', 'pcm_s16le',
            '-ar', '16000', '-ac', '1',
            '-y', str(audio_path)
        ]

        print(f"  使用FFmpeg: {ffmpeg_path}")
        print(f"  命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"音频提取失败: {result.stderr}")

        print(f"  ✅ 音频已保存: {audio_path}")
        self.results['audio_path'] = str(audio_path)
        return str(audio_path)

    def step2_transcribe(self, audio_path: str, model_size: str = "small") -> str:
        """Step 2: Whisper语音识别 (使用CLI避免内存问题)"""
        print("\n🎤 Step 2: Whisper语音识别...")
        print(f"  ⚠️ 使用 {model_size} 模型 (CPU模式)")

        import subprocess

        output_dir = self.work_dir
        cmd = [
            'whisper', audio_path,
            '--model', model_size,
            '--device', 'cpu',
            '--output_dir', str(output_dir),
            '--output_format', 'srt',
            '--fp16', 'False',
            '--beam_size', '1',
            '--best_of', '1'
        ]

        print(f"  命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Whisper识别失败: {result.stderr}")

        # 查找生成的srt文件
        srt_files = list(output_dir.glob("*.srt"))
        if not srt_files:
            raise RuntimeError("Whisper未生成字幕文件")

        # 重命名为标准名称
        subtitle_path = output_dir / "raw_subtitles.srt"
        srt_files[0].rename(subtitle_path)

        print(f"  ✅ 原始字幕已保存: {subtitle_path}")
        self.results['raw_subtitle_path'] = str(subtitle_path)
        return str(subtitle_path)

    def _generate_srt(self, segments) -> str:
        """生成SRT格式字幕"""
        srt_lines = []
        for i, seg in enumerate(segments, 1):
            start = self._format_timestamp(seg['start'])
            end = self._format_timestamp(seg['end'])
            text = seg['text'].strip()

            srt_lines.append(f"{i}\n{start} --> {end}\n{text}\n")

        return '\n'.join(srt_lines)

    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳为SRT格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def step3_align(self, subtitle_path: str, video_duration: float = None) -> str:
        """Step 3: 字幕时间轴校准"""
        print("\n⏱️ Step 3: 字幕时间轴校准...")

        import srt

        with open(subtitle_path, 'r', encoding='utf-8') as f:
            subtitles = list(srt.parse(f.read()))

        aligned = []
        for sub in subtitles:
            # 修复过短字幕
            if sub.end - sub.start < 0.5:
                sub = sub._replace(end=sub.start + 0.5)

            # 合并过近字幕
            if aligned and sub.start - aligned[-1].end < 0.3:
                aligned[-1] = aligned[-1]._replace(
                    end=sub.end,
                    content=aligned[-1].content + ' ' + sub.content
                )
            else:
                aligned.append(sub)

        aligned_path = self.work_dir / "aligned_subtitles.srt"
        with open(aligned_path, 'w', encoding='utf-8') as f:
            f.write(srt.compose(aligned))

        print(f"  ✅ 校准后字幕已保存: {aligned_path}")
        self.results['aligned_subtitle_path'] = str(aligned_path)
        return str(aligned_path)

    def step4_evaluate(self, subtitle_path: str, video_duration: float = None) -> dict:
        """Step 4: 字幕质量评估"""
        print("\n📊 Step 4: 字幕质量评估...")

        with open(subtitle_path, 'r', encoding='utf-8') as f:
            content = f.read()

        result = evaluate_subtitle(content, video_duration)
        report = format_report(result)
        print(report)

        # 保存评估报告
        report_path = self.work_dir / "evaluation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                'total_score': result.total_score,
                'dimensions': result.dimensions,
                'issues': result.issues
            }, f, ensure_ascii=False, indent=2)

        print(f"  📄 评估报告已保存: {report_path}")
        self.results['evaluation'] = result
        return result

    def step5_export(self, subtitle_path: str, output_format: str = "vtt") -> str:
        """Step 5: 导出字幕"""
        print(f"\n📤 Step 5: 导出{output_format.upper()}格式...")

        output_path = self.work_dir / f"final_subtitles.{output_format}"

        with open(subtitle_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if output_format == 'vtt':
            # 转换为VTT
            vtt_content = "WEBVTT\n\n"
            vtt_content += content.replace(',', '.')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(vtt_content)
        elif output_format == 'json':
            import srt
            subtitles = list(srt.parse(content))
            json_data = [{
                'index': sub.index,
                'start': sub.start.total_seconds(),
                'end': sub.end.total_seconds(),
                'text': sub.content
            } for sub in subtitles]
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
        else:
            # SRT/ASS 直接复制
            import shutil
            shutil.copy(subtitle_path, output_path)

        print(f"  ✅ 导出完成: {output_path}")
        self.results['final_path'] = str(output_path)
        return str(output_path)

    def step6_burn_subtitles(self, video_path: str, subtitle_path: str) -> str:
        """Step 6: 将字幕烧录到视频中"""
        print("\n🔥 Step 6: 字幕烧录到视频...")

        video_path = Path(video_path)
        output_video = self.work_dir / f"{video_path.stem}_subtitled{video_path.suffix}"
        subtitle_path = Path(subtitle_path)

        # 使用subtitles滤镜（支持force_style指定中文字体）
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-vf', f"subtitles='{subtitle_path}':force_style='FontName=Noto Sans CJK SC,FontSize=14,Outline=2,Shadow=2'",
            '-c:a', 'copy',
            '-y', str(output_video)
        ]

        print(f"  命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"字幕烧录失败: {result.stderr}")

        print(f"  ✅ 带字幕视频已保存: {output_video}")
        self.results['burned_video_path'] = str(output_video)

        # 复制音频到输出目录
        audio_output = self.work_dir / "extracted_audio.wav"
        import shutil
        shutil.copy(self.results['audio_path'], audio_output)
        print(f"  ✅ 提取的音频已保存: {audio_output}")
        self.results['extracted_audio_path'] = str(audio_output)

        return str(output_video)

    def _generate_ass(self, subtitles: list) -> str:
        """生成ASS格式字幕（使用中文字体）"""
        ass = '''[Script Info]
Title: Generated Subtitle
ScriptType: v4.00+
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK SC,28,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,1,2,2,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''

        def format_time(seconds: float) -> str:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            centisecs = int((seconds % 1) * 100)
            return f'{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}'

        for sub in subtitles:
            start = sub.start.total_seconds()
            end = sub.end.total_seconds()
            text = sub.content.replace('\n', ' ').replace('\r', '')
            ass += f'Dialogue: 0,{format_time(start)},{format_time(end)},Default,,0,0,0,,{text}\\N\n'

        return ass

    def run(self, video_path: str, model_size: str = "medium",
            output_format: str = "vtt", burn_subtitles: bool = True) -> dict:
        """
        运行完整流水线

        Args:
            video_path: 视频文件路径
            model_size: Whisper模型大小 (tiny/base/small/medium/large)
            output_format: 输出格式 (srt/vtt/json)

        Returns:
            流水线结果字典
        """
        print("=" * 60)
        print("         视频字幕编辑流水线")
        print("=" * 60)

        # 检查依赖
        if not self.check_dependencies():
            raise RuntimeError("依赖检查失败")

        # 执行流水线
        try:
            audio_path = self.step1_extract_audio(video_path)
            raw_subtitle = self.step2_transcribe(audio_path, model_size)
            aligned_subtitle = self.step3_align(raw_subtitle)
            self.step4_evaluate(aligned_subtitle)
            final_path = self.step5_export(aligned_subtitle, output_format)

            # Step 6: 字幕烧录
            if burn_subtitles:
                self.step6_burn_subtitles(video_path, aligned_subtitle)

            print("\n" + "=" * 60)
            print("         流水线执行完成!")
            print("=" * 60)
            print(f"\n📁 输出文件:")
            for key, path in self.results.items():
                if key != 'evaluation':
                    print(f"  {key}: {path}")

            print("\n📋 流水线步骤:")
            print("  1. ✅ 音频提取 (audio.wav)")
            print("  2. ✅ Whisper语音识别 (raw_subtitles.srt)")
            print("  3. ✅ 时间轴校准 (aligned_subtitles.srt)")
            print("  4. ✅ 质量评估 (evaluation_report.json)")
            print("  5. ✅ 格式导出 (final_subtitles.{})".format(output_format))
            print("  6. ✅ 字幕烧录 (带字幕视频 + 原音频)")
            return self.results

        except Exception as e:
            print(f"\n❌ 流水线执行失败: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description='视频字幕编辑流水线')
    parser.add_argument('video', help='视频文件路径')
    parser.add_argument('-o', '--output', default='./output', help='输出目录')
    parser.add_argument('-m', '--model', default='medium',
                        choices=['tiny', 'base', 'small', 'medium', 'large'],
                        help='Whisper模型大小')
    parser.add_argument('-f', '--format', default='vtt',
                        choices=['srt', 'vtt', 'json'],
                        help='输出格式')

    args = parser.parse_args()

    pipeline = SubtitlePipeline(work_dir=args.output)
    pipeline.run(args.video, model_size=args.model, output_format=args.format)


if __name__ == "__main__":
    main()
