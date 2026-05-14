#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
讯飞录音文件转写大模型 API 客户端
集成到字幕流水线
"""

import base64
import hmac
import json
import os
import time
import random
import string
import requests
import urllib.parse
import datetime
import warnings
import wave
from typing import Optional, List, Tuple
from pathlib import Path

# 忽略SSL验证警告
warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

# 讯飞API配置
LFASR_HOST = "https://office-api-ist-dx.iflyaisol.com"
API_UPLOAD = "/v2/upload"
API_GET_RESULT = "/v2/getResult"

# API凭证
APPID = "0c277684"
APIKey = "e79ab3d75dcbd0b7933769801c150df3"
APISecret = "ZDUxMzI1YzE5MmMwZDQzNGY4NmZkODVj"


class XfyunAsrClient:
    """讯飞录音文件转写客户端"""

    def __init__(self, appid: str, access_key_id: str, access_key_secret: str,
                 audio_file_path: str):
        self.appid = appid
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.audio_file_path = self._check_audio_path(audio_file_path)
        self.audio_duration = self._get_wav_duration_ms()
        self.order_id = None
        self.signature_random = self._generate_random_str()
        self.last_base_string = ""
        self.last_signature = ""

    def _check_audio_path(self, path: str) -> str:
        if not os.path.exists(path):
            raise FileNotFoundError(f"音频文件不存在：{path}")
        if not path.lower().endswith(".wav"):
            raise ValueError(f"当前代码仅支持WAV格式音频，您的文件格式为：{os.path.splitext(path)[1]}")
        return os.path.abspath(path)

    def _generate_random_str(self, length: int = 16) -> str:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def _get_local_time_with_tz(self) -> str:
        local_now = datetime.datetime.now()
        tz_offset = local_now.astimezone().strftime('%z')
        return f"{local_now.strftime('%Y-%m-%dT%H:%M:%S')}{tz_offset}"

    def _get_wav_duration_ms(self) -> int:
        try:
            with wave.open(self.audio_file_path, 'rb') as wav_file:
                n_frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                duration_ms = int(round(n_frames / sample_rate * 1000))
                return duration_ms
        except wave.Error as e:
            raise Exception(f"WAV文件解析失败：{str(e)}")

    def generate_signature(self, params: dict) -> str:
        sign_params = {k: v for k, v in params.items() if k != "signature"}
        sorted_params = sorted(sign_params.items(), key=lambda x: x[0])

        base_parts = []
        for k, v in sorted_params:
            if v is not None and str(v).strip() != "":
                encoded_key = urllib.parse.quote(k, safe='')
                encoded_value = urllib.parse.quote(str(v), safe='')
                base_parts.append(f"{encoded_key}={encoded_value}")

        self.last_base_string = "&".join(base_parts)

        hmac_obj = hmac.new(
            self.access_key_secret.encode("utf-8"),
            self.last_base_string.encode("utf-8"),
            digestmod="sha1"
        )
        self.last_signature = base64.b64encode(hmac_obj.digest()).decode("utf-8")
        return self.last_signature

    def upload_audio(self) -> dict:
        audio_size = str(os.path.getsize(self.audio_file_path))
        audio_name = os.path.basename(self.audio_file_path)
        date_time = self._get_local_time_with_tz()

        print(f"📤 正在上传音频到讯飞服务器...")
        print(f"   文件: {audio_name}")
        print(f"   大小: {int(audio_size)/1024:.1f} KB")
        print(f"   时长: {self.audio_duration}ms")

        url_params = {
            "appId": self.appid,
            "accessKeyId": self.access_key_id,
            "dateTime": date_time,
            "signatureRandom": self.signature_random,
            "fileSize": audio_size,
            "fileName": audio_name,
            "language": "autodialect",
            "duration": str(self.audio_duration)
        }

        signature = self.generate_signature(url_params)
        headers = {"Content-Type": "application/octet-stream", "signature": signature}

        encoded_params = []
        for k, v in url_params.items():
            encoded_key = urllib.parse.quote(k, safe='')
            encoded_v = urllib.parse.quote(str(v), safe='')
            encoded_params.append(f"{encoded_key}={encoded_v}")
        upload_url = f"{LFASR_HOST}{API_UPLOAD}?{'&'.join(encoded_params)}"

        with open(self.audio_file_path, "rb") as f:
            audio_data = f.read()

        try:
            response = requests.post(url=upload_url, headers=headers, data=audio_data,
                                    timeout=30, verify=False)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise Exception(f"上传请求网络失败：{str(e)}")

        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            raise Exception(f"API返回非JSON数据：{response.text}")

        if result.get("code") != "000000":
            raise Exception(f"上传失败：{result.get('descInfo', '未知错误')}")

        self.order_id = result["content"]["orderId"]
        print(f"   订单ID: {self.order_id}")
        return result

    def get_transcribe_result(self, poll_interval: int = 5, max_retries: int = 100) -> dict:
        if not self.order_id:
            raise Exception("未获取到订单ID")

        print(f"\n🔍 正在查询转写结果...")

        query_params = {
            "appId": self.appid,
            "accessKeyId": self.access_key_id,
            "dateTime": self._get_local_time_with_tz(),
            "orderId": self.order_id,
            "signatureRandom": self.signature_random
        }

        query_signature = self.generate_signature(query_params)
        query_headers = {"Content-Type": "application/json", "signature": query_signature}

        encoded_query_params = []
        for k, v in query_params.items():
            encoded_key = urllib.parse.quote(k, safe='')
            encoded_v = urllib.parse.quote(str(v), safe='')
            encoded_query_params.append(f"{encoded_key}={encoded_v}")
        query_url = f"{LFASR_HOST}{API_GET_RESULT}?{'&'.join(encoded_query_params)}"

        retry_count = 0
        while retry_count < max_retries:
            try:
                response = requests.post(url=query_url, headers=query_headers,
                                        data=json.dumps({}), timeout=15, verify=False)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                raise Exception(f"查询请求网络失败：{str(e)}")

            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                raise Exception(f"查询响应非JSON数据：{response.text}")

            if result.get("code") != "000000":
                raise Exception(f"查询失败：{result.get('descInfo', '未知错误')}")

            process_status = result["content"]["orderInfo"]["status"]
            if process_status == 4:
                print(f"✅ 转写完成！")
                return result
            elif process_status == -1:
                fail_type = result["content"]["orderInfo"].get("failType", 0)
                raise Exception(f"转写失败：failType={fail_type}")
            elif process_status == 3:
                retry_count += 1
                print(f"   处理中... ({retry_count}/{max_retries})")
                time.sleep(poll_interval)
            else:
                raise Exception(f"转写异常：状态码={process_status}")

        raise Exception(f"查询超时：已重试{max_retries}次")


def parse_order_result(result: dict) -> List[dict]:
    """解析讯飞转写结果，返回字幕段落列表"""
    try:
        order_result_str = result["content"]["orderResult"]
        order_result = json.loads(order_result_str)
        lattice = order_result.get("lattice", [])

        segments = []
        for item in lattice:
            json_1best_str = item.get("json_1best", "{}")
            try:
                json_1best = json.loads(json_1best_str)
                st = json_1best.get("st", {})

                # 获取时间戳（毫秒）
                bg = int(st.get("bg", 0))
                ed = int(st.get("ed", 0))

                # 提取词语
                words = []
                rt = st.get("rt", [])
                for r in rt:
                    ws = r.get("ws", [])
                    for w_item in ws:
                        cw_list = w_item.get("cw", [])
                        for cw in cw_list:
                            word = cw.get("w", "")
                            wp = cw.get("wp", "")
                            # wp: n=正常词, s=顺滑, p=标点, g=分段
                            if wp == "g":
                                # 分段符，结束当前句子
                                break
                            if word:
                                words.append(word)

                text = "".join(words)
                if text.strip():
                    segments.append({
                        "start": bg / 1000.0,  # 转换为秒
                        "end": ed / 1000.0,
                        "text": text.strip()
                    })
            except (json.JSONDecodeError, KeyError):
                continue

        # 合并相邻的段落
        merged = []
        for seg in segments:
            if merged and seg["start"] - merged[-1]["end"] < 0.3:
                merged[-1]["end"] = seg["end"]
                merged[-1]["text"] += seg["text"]
            else:
                merged.append(seg)

        return merged

    except Exception as e:
        raise Exception(f"解析结果失败：{str(e)}")


def generate_srt(segments: List[dict]) -> str:
    """将段落列表转换为SRT格式"""
    srt_lines = []
    for i, seg in enumerate(segments, 1):
        start = seg["start"]
        end = seg["end"]
        text = seg["text"]

        # 格式化时间戳
        start_str = format_timestamp(start)
        end_str = format_timestamp(end)

        srt_lines.append(f"{i}")
        srt_lines.append(f"{start_str} --> {end_str}")
        srt_lines.append(text)
        srt_lines.append("")

    return "\n".join(srt_lines)


def format_timestamp(seconds: float) -> str:
    """格式化时间戳为SRT格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def transcribe_with_iflytek(audio_path: str, output_srt_path: str = None) -> Tuple[str, List[dict]]:
    """
    使用讯飞API转写音频

    Args:
        audio_path: WAV音频文件路径
        output_srt_path: 输出SRT文件路径（可选）

    Returns:
        (srt_content, segments) 元组
    """
    # 确保是WAV格式
    audio_path = Path(audio_path)
    if audio_path.suffix.lower() != ".wav":
        raise ValueError("讯飞API仅支持WAV格式音频")

    # 创建客户端并转写
    client = XfyunAsrClient(
        appid=APPID,
        access_key_id=APIKey,
        access_key_secret=APISecret,
        audio_file_path=str(audio_path)
    )

    # 上传并获取结果
    client.upload_audio()
    result = client.get_transcribe_result()

    # 解析结果
    segments = parse_order_result(result)

    # 生成SRT
    srt_content = generate_srt(segments)

    # 保存文件
    if output_srt_path:
        with open(output_srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

    return srt_content, segments


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python iflytek_asr.py <音频.wav> [输出.srt]")
        sys.exit(1)

    audio_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        print("=" * 50)
        print("讯飞录音文件转写")
        print("=" * 50)

        srt_content, segments = transcribe_with_iflytek(audio_file, output_file)

        print("\n转写结果:")
        print("-" * 50)
        for seg in segments:
            print(f"[{seg['start']:.2f}-{seg['end']:.2f}] {seg['text']}")

        print("\n" + "=" * 50)
        print(f"共 {len(segments)} 段")
        if output_file:
            print(f"已保存到: {output_file}")
        print("=" * 50)

    except Exception as e:
        print(f"\n错误: {str(e)}")
        sys.exit(1)