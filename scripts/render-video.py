#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SRT_TIME = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")


def seconds(value: str) -> float:
    match = SRT_TIME.fullmatch(value.strip())
    if not match:
        raise ValueError(f"无效时间: {value}")
    h, m, s, ms = map(int, match.groups())
    return h * 3600 + m * 60 + s + ms / 1000


def read_srt(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
    pattern = re.compile(
        r"(?:^|\n\n)(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> "
        r"(\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n\d+\n|\Z)",
        re.S,
    )
    cues = []
    for match in pattern.finditer(text):
        cues.append({"start": seconds(match[2]), "end": seconds(match[3]), "text": match[4].strip()})
    if not cues:
        raise SystemExit("SRT 中没有有效字幕。")
    return cues


def probe(video: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-show_entries", "format=duration",
            "-of", "json", str(video),
        ],
        check=True, capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "duration": float(data["format"]["duration"]),
    }


def find_font() -> Path:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            return path
    raise SystemExit("找不到中文字体，请安装 Noto Sans CJK 或 PingFang SC。")


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for char in paragraph:
            trial = current + char
            if current and draw.textbbox((0, 0), trial, font=font)[2] > max_width:
                lines.append(current.rstrip())
                current = char.lstrip()
            else:
                current = trial
        lines.append(current.rstrip() or " ")
    return lines


def make_overlay(cue: dict, width: int, height: int, font_path: Path, position: str, index: int, temp: Path) -> Path:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font_size = max(22, min(48, round(30 * height / 720)))
    font = ImageFont.truetype(str(font_path), font_size, index=0)
    max_text_width = int(width * 0.82)
    lines = wrap_text(draw, cue["text"], font, max_text_width)
    line_height = round(font_size * 1.42)
    text_width = max(draw.textbbox((0, 0), line, font=font)[2] for line in lines)
    padding_x = max(20, round(width * 0.018))
    padding_y = max(12, round(height * 0.018))
    box_width = min(width - 32, text_width + padding_x * 2)
    box_height = len(lines) * line_height + padding_y * 2 - round(font_size * 0.35)
    margin = max(20, round(height * 0.035))
    left = (width - box_width) // 2
    top = margin if position == "top" else height - margin - box_height
    draw.rounded_rectangle(
        (left, top, left + box_width, top + box_height),
        radius=max(10, round(height * 0.016)),
        fill=(18, 24, 32, 225),
    )
    y = top + padding_y
    for line in lines:
        line_width = draw.textbbox((0, 0), line, font=font)[2]
        draw.text(((width - line_width) // 2, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_height
    output = temp / f"caption-{index:03}.png"
    image.save(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="把录屏、烧录字幕并添加可选背景音乐，输出兼容性较好的 MP4。")
    parser.add_argument("--video", required=True, help="原始网页录屏")
    parser.add_argument("--srt", help="UTF-8 SRT 字幕；不传则仅转码")
    parser.add_argument("--output", required=True, help="输出 MP4")
    parser.add_argument("--music", default="builtin", help="音乐路径；builtin 使用随技能提供的默认配乐，none 关闭音乐")
    parser.add_argument("--volume", type=float, default=0.12, help="背景音乐音量，默认 0.12")
    parser.add_argument("--subtitle-position", choices=["bottom", "top"], default="bottom")
    parser.add_argument("--crf", type=int, default=20, help="H.264 画质参数，默认 20")
    args = parser.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("需要 ffmpeg 和 ffprobe。")
    video = Path(args.video).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not video.is_file():
        raise SystemExit(f"找不到视频: {video}")
    output.parent.mkdir(parents=True, exist_ok=True)
    info = probe(video)

    music = None
    if args.music != "none":
        music = (
            Path(__file__).resolve().parent.parent / "assets/music/tutorial-loop.mp3"
            if args.music == "builtin" else Path(args.music).expanduser().resolve()
        )
        if not music.is_file():
            raise SystemExit(f"找不到背景音乐: {music}")

    cue_files = []
    with tempfile.TemporaryDirectory(prefix="tutorial-captions-") as temp_name:
        temp = Path(temp_name)
        cues = read_srt(Path(args.srt).expanduser().resolve()) if args.srt else []
        font = find_font() if cues else None
        for index, cue in enumerate(cues, 1):
            cue["end"] = min(cue["end"], info["duration"])
            if cue["end"] <= cue["start"]:
                raise SystemExit(f"第 {index} 条字幕超出视频时长。")
            cue_files.append(
                (cue, make_overlay(cue, info["width"], info["height"], font, args.subtitle_position, index, temp))
            )

        command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video)]
        for _, image in cue_files:
            command += ["-loop", "1", "-i", str(image)]
        if music:
            command += ["-stream_loop", "-1", "-i", str(music)]
        else:
            command += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]

        filters = []
        last = "0:v:0"
        for index, (cue, _) in enumerate(cue_files, 1):
            if index == 1:
                last = "[0:v]"
            filters.append(f"[{index}:v]format=rgba[c{index}]")
            filters.append(
                f"{last}[c{index}]overlay=0:0:enable='between(t,{cue['start']:.3f},{cue['end']:.3f})'[v{index}]"
            )
            last = f"[v{index}]"

        audio_index = len(cue_files) + 1
        fade = min(1.5, info["duration"] / 5)
        fade_out = max(0.0, info["duration"] - fade)
        filters.append(
            f"[{audio_index}:a]atrim=0:{info['duration']:.3f},asetpts=PTS-STARTPTS,"
            f"volume={args.volume:.4f},afade=t=in:st=0:d={fade:.3f},"
            f"afade=t=out:st={fade_out:.3f}:d={fade:.3f}[a]"
        )
        music_credit = (
            "Background music: Meditation Impromptu 02 by Kevin MacLeod "
            "(incompetech.com), CC BY 4.0" if music else "No background music"
        )
        command += [
            "-filter_complex", ";".join(filters),
            "-map", last, "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", "-t", f"{info['duration']:.3f}",
            "-metadata", f"comment={music_credit}",
            str(output),
        ]
        subprocess.run(command, check=True)

    result = probe(output)
    print(json.dumps({"output": str(output), **result, "music": str(music) if music else None}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
