#!/usr/bin/env python3
"""
账户隔离的字幕处理流水线
每个账户只能在对应目录下操作
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Optional, Dict

# 添加评估系统路径
sys.path.insert(0, str(Path(__file__).parent.parent / '评估系统'))
from evaluator import evaluate_subtitle, format_report


class Account:
    """账户配置"""
    def __init__(self, config: Dict):
        self.id = config['id']
        self.name = config['name']
        self.home_dir = Path(config['home_dir'])
        self.output_dir = Path(config['output_dir'])
        self.allowed_formats = config.get('allowed_formats', ['mp4'])
        self.max_video_size_mb = config.get('max_video_size_mb', 500)
        self.whisper_model = config.get('whisper_model', 'small')
        self.enabled = config.get('enabled', True)

    def validate_video(self, video_path: Path) -> tuple[bool, str]:
        """验证视频是否在允许范围内"""
        if not self.enabled:
            return False, f"账户 {self.name} 已禁用"

        # 检查视频是否在home_dir内
        try:
            video_path.resolve().relative_to(self.home_dir.resolve())
        except ValueError:
            return False, f"视频必须在账户目录内: {self.home_dir}"

        # 检查文件是否存在
        if not video_path.exists():
            return False, f"视频文件不存在: {video_path}"

        # 检查文件大小
        size_mb = video_path.stat().st_size / (1024 * 1024)
        if size_mb > self.max_video_size_mb:
            return False, f"视频大小超过限制 ({size_mb:.1f}MB > {self.max_video_size_mb}MB)"

        # 检查格式
        ext = video_path.suffix.lower().lstrip('.')
        if ext not in self.allowed_formats:
            return False, f"不支持的格式: {ext} (允许: {', '.join(self.allowed_formats)})"

        return True, "OK"


class AccountPipeline(SubtitlePipeline):
    """支持账户隔离的流水线"""

    def __init__(self, account: Account):
        super().__init__(work_dir=str(account.output_dir))
        self.account = account

    def check_dependencies(self) -> bool:
        """检查系统依赖"""
        print("🔍 检查系统依赖...")

        deps = {'python3': 'python3 --version'}
        for name, cmd in deps.items():
            try:
                subprocess.run(cmd, shell=True, capture_output=True, check=True)
                print(f"  ✅ {name}")
            except subprocess.CalledProcessError:
                print(f"  ❌ {name} 未安装")
                return False

        python_deps = ['whisper', 'srt', 'pysrt', 'imageio_ffmpeg']
        for pkg in python_deps:
            try:
                __import__(pkg.replace('-', '_'))
                print(f"  ✅ {pkg}")
            except ImportError:
                print(f"  ❌ {pkg} 未安装")
                return False

        return True

    def run(self, video_path: str, output_format: str = "vtt") -> dict:
        """
        运行完整流水线（账户隔离版本）
        """
        video_path = Path(video_path).resolve()

        # 验证账户权限
        valid, msg = self.account.validate_video(video_path)
        if not valid:
            raise PermissionError(f"权限验证失败: {msg}")

        print("=" * 60)
        print(f"         视频字幕编辑流水线 - {self.account.name}")
        print("=" * 60)
        print(f"📁 工作目录: {self.account.output_dir}")
        print(f"🎯 Whisper模型: {self.account.whisper_model}")

        # 确保输出目录存在
        self.account.output_dir.mkdir(parents=True, exist_ok=True)

        # 执行流水线
        try:
            audio_path = self.step1_extract_audio(str(video_path))
            raw_subtitle = self.step2_transcribe(audio_path, self.account.whisper_model)
            aligned_subtitle = self.step3_align(raw_subtitle)
            self.step4_evaluate(aligned_subtitle)
            final_path = self.step5_export(aligned_subtitle, output_format)

            print("\n" + "=" * 60)
            print("         流水线执行完成!")
            print("=" * 60)
            print(f"\n📁 输出文件:")
            for key, path in self.results.items():
                if key != 'evaluation':
                    print(f"  {key}: {path}")

            return self.results

        except Exception as e:
            print(f"\n❌ 流水线执行失败: {e}")
            raise


class SubtitlePipelineManager:
    """流水线管理器 - 支持多账户"""
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'config' / 'accounts.json'
        self.config_path = Path(config_path)
        self.accounts = self._load_config()

    def _load_config(self) -> Dict[str, Account]:
        """加载账户配置"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        accounts = {}
        for acc_config in config['accounts']:
            acc = Account(acc_config)
            accounts[acc.id] = acc

        return accounts

    def list_accounts(self) -> list:
        """列出所有账户"""
        return [
            {
                'id': acc.id,
                'name': acc.name,
                'enabled': acc.enabled,
                'home_dir': str(acc.home_dir)
            }
            for acc in self.accounts.values()
        ]

    def get_account(self, account_id: str) -> Optional[Account]:
        """获取账户"""
        return self.accounts.get(account_id)

    def run_for_account(self, account_id: str, video_path: str,
                        output_format: str = "vtt") -> dict:
        """为指定账户运行流水线"""
        account = self.get_account(account_id)
        if not account:
            raise ValueError(f"账户不存在: {account_id}")

        pipeline = AccountPipeline(account)
        return pipeline.run(video_path, output_format)


def main():
    parser = argparse.ArgumentParser(description='账户隔离字幕流水线')
    parser.add_argument('video', help='视频文件路径')
    parser.add_argument('-a', '--account', required=True, help='账户ID')
    parser.add_argument('-f', '--format', default='vtt',
                        choices=['srt', 'vtt', 'json'],
                        help='输出格式')
    parser.add_argument('-c', '--config', help='账户配置文件路径')

    args = parser.parse_args()

    manager = SubtitlePipelineManager(config_path=args.config)
    try:
        result = manager.run_for_account(args.account, args.video, args.format)
        print("\n✅ 执行成功!")
    except PermissionError as e:
        print(f"\n❌ 权限错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()