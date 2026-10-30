#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def srt_time(seconds: float) -> str:
    milliseconds = max(0, round(float(seconds) * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def main() -> None:
    parser = argparse.ArgumentParser(description="把录屏元数据中的字幕条目生成 UTF-8 SRT。")
    parser.add_argument("input", help="record-browser.mjs 输出的 JSON，或字幕条目数组 JSON")
    parser.add_argument("output", help="输出 SRT 路径")
    parser.add_argument("--shift", type=float, default=0.0, help="整体平移秒数，可传负数")
    parser.add_argument("--max-duration", type=float, help="限制最后一条字幕的结束时间")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    captions = data.get("captions", []) if isinstance(data, dict) else data
    if not captions:
        raise SystemExit("没有找到字幕条目。")

    blocks = []
    previous_end = 0.0
    for index, item in enumerate(captions, 1):
        start = max(0.0, float(item["start"]) + args.shift)
        end = float(item.get("end", start + 2)) + args.shift
        if args.max_duration is not None:
            end = min(end, args.max_duration)
        if end <= start:
            raise SystemExit(f"第 {index} 条字幕结束时间必须晚于开始时间。")
        if start < previous_end:
            raise SystemExit(f"第 {index} 条字幕与前一条重叠。")
        previous_end = end
        text = str(item["text"]).strip()
        if not text:
            raise SystemExit(f"第 {index} 条字幕为空。")
        blocks.append(f"{index}\n{srt_time(start)} --> {srt_time(end)}\n{text}")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
