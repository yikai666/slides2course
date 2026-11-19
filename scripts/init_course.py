#!/usr/bin/env python3
"""初始化课程视频工程骨架。

用法:
    python init_course.py ./random-signal --title "随机信号分析" --episodes 12
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

DIRS = [
    "content/lectures",
    "tooling",
    "plan",
    "manuscript",
    "reviews",
    "video",
    "delivery",
]

COURSE_YAML = """# 课程契约。不确定的写 待定，并列进 open_questions，不要自己编。
title: {title}
slug: {slug}
audience:
  baseline: 刚高考完
  prerequisites_retained: 0.2   # 先修只保留 20%，其余要在稿子里重建
  math_level: 高中数学 + 本课重建
prerequisites:
  declared: []
  rebuild_policy: 每个先修点首次出现时 2 分钟内重建
delivery:
  platform: bilibili
  episode_minutes: {minutes}
  tolerance_minutes: 8
  captions: true
  resolution: 1920x1080
  fps: 30
  voice: zh-CN-XiaoxiaoNeural
  output_dir: video
open_questions: []
"""

EPISODES_YAML = """# 分集表。先填 id 与知识点，minutes 在 S3 算完预算后补。
episodes:
  - id: EP01
    title: 待定
    knowledge: []
    prerequisites: []
    minutes: null
    objectives: []
"""

PROGRESS_JSON = {
    "course": "",
    "updated": "",
    "episodes": {},
}

EPISODE_STUB = """# {ep} 教学目标

## 可测目标（3–5 条，用「能算出 / 能判断 / 能解释 / 能画出」开头）

1. 待定

## 知识点

- 待定

## 画面清单

| 时间 | 画面类型 | 内容 | 知识点 |
| --- | --- | --- | --- |
| 00:00 | 待定 | 待定 | 待定 |

## 开头钩子

待定

## 结尾钩子（指向下一集）

待定
"""


def slugify(text: str) -> str:
    # 只保留 ASCII 字母数字，中文标题交给 --slug 指定
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip()).strip("-").lower()
    return slug or "course"


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化课程视频工程")
    parser.add_argument("root", help="工程目录")
    parser.add_argument("--title", required=True, help="课程名")
    parser.add_argument("--slug", default=None, help="英文标识，默认由标题生成")
    parser.add_argument("--episodes", type=int, default=0, help="预建集数")
    parser.add_argument("--minutes", type=int, default=45, help="单集目标时长")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的文件")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    slug = args.slug or slugify(args.title)
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")

    root.mkdir(parents=True, exist_ok=True)
    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)

    written, skipped = [], []

    def emit(path: Path, text: str) -> None:
        if path.exists() and not args.force:
            skipped.append(path)
            return
        path.write_text(text, encoding="utf-8")
        written.append(path)

    emit(
        root / "course.yaml",
        COURSE_YAML.replace("{title}", args.title)
        .replace("{slug}", slug)
        .replace("{minutes}", str(args.minutes)),
    )
    emit(root / "plan" / "episodes.yaml", EPISODES_YAML)

    episodes = {}
    for i in range(1, args.episodes + 1):
        ep = f"EP{i:02d}"
        episodes[ep] = {
            "stage": "S0",
            "gates": {},
            "rounds": {"learner": 0, "watch": 0},
            "blocking": [],
            "artifacts": {},
        }
        emit(root / "plan" / f"{ep}.md", EPISODE_STUB.replace("{ep}", ep))
        (root / "manuscript" / ep).mkdir(parents=True, exist_ok=True)
        (root / "manuscript" / ep / ".gitkeep").write_text("", encoding="utf-8")

    progress = dict(PROGRESS_JSON)
    progress["course"] = slug
    progress["updated"] = now
    progress["episodes"] = episodes
    emit(root / "progress.json", json.dumps(progress, ensure_ascii=False, indent=2) + "\n")

    (root / ".gitignore").write_text(
        "video/*.mp4\nvideo/*.wav\nvideo/frames/\n__pycache__/\n.DS_Store\n",
        encoding="utf-8",
    )

    print(f"工程: {root}")
    print(f"课程: {args.title} ({slug})")
    if slug == "course" and not args.slug:
        print("  [提示] 标题含中文，slug 回落为 course；建议加 --slug random-signal-analysis")
    for p in written:
        print(f"  [OK]   {p.relative_to(root)}")
    for p in skipped:
        print(f"  [SKIP] {p.relative_to(root)}")
    if args.episodes:
        print(f"预建 {args.episodes} 集")
    print("\n下一步: S1 拆课 -> 填 content/knowledge-map.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
