"""
媒体处理模块 (Media Processor)

负责外部链接解析、元数据抓取、音频提取和字幕获取。
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from ..models import AudioFile, Metadata, SourcePlatform, TranscriptSegment


def _ytdlp_base_args() -> list[str]:
    """公共 yt-dlp 选项，尽量避免 YouTube 403/SABR 问题"""
    args = [
        "--no-playlist",
        "--no-check-certificates",
        "--extractor-args",
        "youtube:player_client=android",
    ]
    cookies_from = os.getenv("YTDLP_COOKIES_FROM_BROWSER")
    if cookies_from:
        args += ["--cookies-from-browser", cookies_from]
    return args


def _get_ytdlp_path() -> str:
    """获取 yt-dlp 可执行文件路径"""
    # 优先使用虚拟环境中的 yt-dlp
    venv_ytdlp = Path(sys.executable).parent / "yt-dlp.exe"
    if venv_ytdlp.exists():
        return str(venv_ytdlp)
    # 否则尝试系统 PATH
    system_ytdlp = shutil.which("yt-dlp")
    if system_ytdlp:
        return system_ytdlp
    raise RuntimeError("yt-dlp 未安装，请运行: pip install yt-dlp")


def detect_platform(url: str) -> SourcePlatform:
    """检测视频来源平台"""
    if "bilibili.com" in url or "b23.tv" in url:
        return SourcePlatform.BILIBILI
    elif "youtube.com" in url or "youtu.be" in url:
        return SourcePlatform.YOUTUBE
    else:
        return SourcePlatform.LOCAL


def fetch_metadata(url: str) -> Metadata:
    """
    获取视频元数据
    
    Args:
        url: B站/YouTube URL
        
    Returns:
        Metadata: 包含标题、作者、时长、封面图、原始语言等信息
    """
    import json
    
    platform = detect_platform(url)
    
    # 使用 yt-dlp 获取元数据
    cmd = [
        _get_ytdlp_path(),
        *_ytdlp_base_args(),
        "--dump-json",
        "--no-download",
        url
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            check=True,
        )
        # 处理 Windows 编码问题
        stdout = result.stdout.decode('utf-8', errors='replace')
        info = json.loads(stdout)
        
        # 检测语言
        language = info.get("language") or "zh"
        if platform == SourcePlatform.YOUTUBE:
            # YouTube 视频通常有语言标记
            language = info.get("language") or "en"
        
        return Metadata(
            title=info.get("title", "Unknown"),
            author=info.get("uploader", info.get("channel", "Unknown")),
            duration=float(info.get("duration", 0)),
            thumbnail_url=info.get("thumbnail"),
            original_language=language,
            platform=platform,
            url=url,
            description=info.get("description", ""),
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
        raise RuntimeError(f"获取视频元数据失败: {stderr}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"解析视频元数据失败: {e}") from e


def extract_audio(url: str, output_dir: Optional[Path] = None) -> AudioFile:
    """
    提取视频音频
    
    若无现成字幕，下载高压缩率音频流（16k mono），准备 ASR。
    
    Args:
        url: 视频 URL
        output_dir: 输出目录，默认为临时目录
        
    Returns:
        AudioFile: 音频文件信息
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp())
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成输出文件名
    output_path = output_dir / "audio.wav"
    
    # 使用 yt-dlp 下载并转换音频
    cmd = [
        _get_ytdlp_path(),
        *_ytdlp_base_args(),
        "-x",  # 仅提取音频
        "--audio-format", "wav",
        "--audio-quality", "0",
        "--postprocessor-args", "ffmpeg:-ar 16000 -ac 1",  # 16kHz 单声道
        "-o", str(output_path),
        url
    ]
    
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            check=True,
        )
        
        # 获取音频时长
        duration = _get_audio_duration(output_path)
        
        return AudioFile(
            file_path=str(output_path),
            sample_rate=16000,
            channels=1,
            duration=duration,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
        raise RuntimeError(f"提取音频失败: {stderr}") from e


def get_subtitle(url: str) -> list[TranscriptSegment]:
    """
    获取视频字幕
    
    优先抓取官方 CC 字幕或自动生成字幕。
    
    Args:
        url: 视频 URL
        
    Returns:
        list[TranscriptSegment]: 字幕片段列表，若无字幕则返回空列表
    """
    import json
    
    platform = detect_platform(url)
    
    # 尝试获取可用字幕列表
    cmd = [
        _get_ytdlp_path(),
        *_ytdlp_base_args(),
        "--list-subs",
        "--dump-json",
        "--no-download",
        url
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
        )
        
        if result.returncode != 0:
            return []
        
        # 处理 Windows 编码问题
        stdout = result.stdout.decode('utf-8', errors='replace')
        info = json.loads(stdout)
        
        # 检查是否有字幕
        subtitles = info.get("subtitles", {})
        automatic_captions = info.get("automatic_captions", {})
        
        # 优先选择手动字幕，其次是自动字幕
        available_subs = subtitles or automatic_captions
        if not available_subs:
            return []
        
        # 选择语言（优先中文，其次英文）
        lang_priority = ["zh-Hans", "zh", "zh-CN", "zh-TW", "en", "en-US"]
        selected_lang = None
        for lang in lang_priority:
            if lang in available_subs:
                selected_lang = lang
                break
        
        if not selected_lang:
            selected_lang = list(available_subs.keys())[0]
        
        # 下载字幕
        return _download_subtitle(url, selected_lang, platform)
        
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []


def _download_subtitle(url: str, lang: str, platform: SourcePlatform) -> list[TranscriptSegment]:
    _ = platform  # 保留参数以兼容调用方
    """下载并解析字幕"""
    import json
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "subtitle"
        
        cmd = [
            _get_ytdlp_path(),
            *_ytdlp_base_args(),
            "--write-sub",
            "--write-auto-sub",
            "--sub-lang", lang,
            "--sub-format", "json3",
            "--skip-download",
            "-o", str(output_path),
            url
        ]
        
        try:
            subprocess.run(
                cmd,
                capture_output=True,
                check=True,
            )
            
            # 查找下载的字幕文件
            subtitle_files = list(Path(tmpdir).glob("*.json3")) + list(Path(tmpdir).glob("*.json"))
            
            if not subtitle_files:
                # 尝试 vtt 格式
                return _download_subtitle_vtt(url, lang, tmpdir)
            
            # 解析 JSON3 格式字幕
            with open(subtitle_files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
            
            segments = []
            for event in data.get("events", []):
                if "segs" not in event:
                    continue
                
                text = "".join(seg.get("utf8", "") for seg in event["segs"])
                text = text.strip()
                
                if text:
                    start_time = event.get("tStartMs", 0) / 1000
                    duration = event.get("dDurationMs", 0) / 1000
                    
                    segments.append(TranscriptSegment(
                        start_time=start_time,
                        end_time=start_time + duration,
                        text=text,
                    ))
            
            return segments
            
        except subprocess.CalledProcessError:
            return []


def _download_subtitle_vtt(url: str, lang: str, tmpdir: str) -> list[TranscriptSegment]:
    """下载 VTT 格式字幕并解析"""
    output_path = Path(tmpdir) / "subtitle"
    
    cmd = [
        _get_ytdlp_path(),
        *_ytdlp_base_args(),
        "--write-sub",
        "--write-auto-sub",
        "--sub-lang", lang,
        "--sub-format", "vtt",
        "--skip-download",
        "-o", str(output_path),
        url
    ]
    
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            check=True,
        )
        
        vtt_files = list(Path(tmpdir).glob("*.vtt"))
        if not vtt_files:
            return []
        
        return _parse_vtt(vtt_files[0])
        
    except subprocess.CalledProcessError:
        return []


def _parse_vtt(vtt_path: Path) -> list[TranscriptSegment]:
    """解析 VTT 字幕文件"""
    segments = []
    
    with open(vtt_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # VTT 时间戳格式: 00:00:00.000 --> 00:00:00.000
    pattern = r"(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*\n(.+?)(?=\n\n|\Z)"
    
    for match in re.finditer(pattern, content, re.DOTALL):
        start_str, end_str, text = match.groups()
        
        start_time = _parse_timestamp(start_str)
        end_time = _parse_timestamp(end_str)
        
        # 清理文本
        text = re.sub(r"<[^>]+>", "", text)  # 移除 HTML 标签
        text = text.strip()
        
        if text:
            segments.append(TranscriptSegment(
                start_time=start_time,
                end_time=end_time,
                text=text,
            ))
    
    return segments


def _parse_timestamp(ts: str) -> float:
    """将时间戳字符串转换为秒"""
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    elif len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    else:
        return float(ts)


def _get_audio_duration(audio_path: Path) -> float:
    """获取音频文件时长"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            check=True
        )
        stdout = result.stdout.decode('utf-8', errors='replace')
        return float(stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return 0.0
