"""统计 i18n 分支各语言的翻译覆盖率，并回写 README 的 STATS 标记区块。

用法：在仓库根目录执行 `python3 scripts/gen_stats.py`
需要 i18n 目录已存在于工作区（通常由 workflow 从 i18n 分支 checkout）。
"""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

README = Path("README.md")
I18N_ROOT = "i18n"
BAR_WIDTH = 30
MARKER = re.compile(r"(<!-- STATS:START -->\n)(.*?)(<!-- STATS:END -->)", re.S)


def scan(root: str = I18N_ROOT) -> list[dict]:
    """扫描 <root>/<版本>/<语言>.json，返回统计数据。"""
    rows: list[dict] = []
    for path in sorted(glob.glob(f"{root}/*/*.json")):
        if path.endswith(".rejected.json"):
            continue
        parts = Path(path).parts
        if len(parts) < 3:
            continue
        version, lang = parts[1], Path(path).stem
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"跳过 {path}: {e}", file=sys.stderr)
            continue
        total = sum(len(v) for v in data.values())
        if not total:
            continue
        filled = sum(1 for v in data.values() for t in v.values() if t.strip())
        rows.append(
            {
                "version": version,
                "lang": lang,
                "filled": filled,
                "total": total,
                "pct": filled / total * 100,
            }
        )
    return rows


def render(rows: list[dict]) -> str:
    """生成表格 + 字符进度条。"""
    if not rows:
        return "> 暂无翻译数据。"

    lines = [
        "| 语言 | 版本 | 已译 | 总条目 | 覆盖率 |",
        "|------|------|------|--------|--------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['lang']} | {r['version']} | {r['filled']:,} "
            f"| {r['total']:,} | {r['pct']:.1f}% |"
        )

    lines.append("")
    lines.append("```")
    width = max(len(r["lang"]) for r in rows)
    for r in rows:
        blocks = round(r["pct"] / 100 * BAR_WIDTH)
        bar = "█" * blocks + "░" * (BAR_WIDTH - blocks)
        lines.append(f"{r['lang']:<{width}}  {bar}  {r['pct']:.1f}%")
    lines.append("```")
    return "\n".join(lines)


def main() -> int:
    rows = scan()
    if not rows:
        print("未找到翻译数据，保持 README 不变", file=sys.stderr)
        return 1

    body = render(rows)
    text = README.read_text(encoding="utf-8")
    if not MARKER.search(text):
        print("README 中缺少 STATS 标记", file=sys.stderr)
        return 1

    README.write_text(
        MARKER.sub(lambda m: m.group(1) + body + "\n" + m.group(3), text),
        encoding="utf-8",
    )

    print(f"已更新 {len(rows)} 种语言:")
    for r in rows:
        print(f"  {r['lang']} {r['version']}: {r['filled']:,}/{r['total']:,} = {r['pct']:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
