from __future__ import annotations

import argparse
import datetime as _dt
from pathlib import Path
from typing import Any, Optional

import database as db


SUPPORTED_DIMENSIONS: list[str] = [
    "LLM",
    "VLM",
    "视频生成",
    "音频/TTS/ASR",
    "具身智能",
    "AI编程/Vibe Coding",
    "AI应用",
]


def get_supported_dimensions() -> list[str]:
    """
    输出系统支持的“技术维度”列表（用于用户不知道有哪些维度的情况）。
    """
    return list(SUPPORTED_DIMENSIONS)


def fetch_dimension_timeline(
    *,
    db_path: str | Path,
    dimension: str,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    """
    指定技术维度，并按时间顺序（从旧到新）拉取数据，展示技术脉络。

    返回字段：
    - publish_time, source_url
    - project_name, tech_node, evolution_tag, impact_score, summary
    """
    conn = db.connect(db_path)
    db.init_db(conn)  # 确保表存在

    sql = """
    SELECT
        s.publish_time,
        s.source_url,
        i.project_name,
        i.tech_node,
        i.evolution_tag,
        i.impact_score,
        i.summary
    FROM tech_insights i
    JOIN raw_sources s ON i.source_id = s.source_id
    WHERE i.dimension = ?
    ORDER BY s.publish_time ASC, i.insight_id ASC
    """
    params: list[Any] = [dimension]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(int(limit))

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return [dict(r) for r in rows]


def _fmt_ts(ts: int | None) -> str:
    if not ts:
        return "-"
    try:
        return _dt.datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:  # noqa: BLE001
        return str(ts)


def main() -> None:
    parser = argparse.ArgumentParser(description="查询 tech_insights 技术脉络（按维度时间轴）")
    parser.add_argument(
        "--db",
        default=str(Path(__file__).resolve().parent.parent / "assets" / "data.db"),
        help="SQLite 文件路径（默认当前目录 data.db）",
    )
    parser.add_argument(
        "--list-dimensions",
        action="store_true",
        help="输出支持的技术维度列表",
    )
    parser.add_argument(
        "--dimension",
        default=None,
        help="要查询的维度名称（例如：AI编程/Vibe Coding）",
    )
    parser.add_argument("--limit", type=int, default=None, help="最多返回多少条（默认不限制）")
    args = parser.parse_args()

    if args.list_dimensions:
        print("\n".join(get_supported_dimensions()))
        return

    if not args.dimension:
        raise SystemExit("请提供 --dimension，或使用 --list-dimensions 查看可用维度。")

    items = fetch_dimension_timeline(db_path=args.db, dimension=args.dimension, limit=args.limit)
    if not items:
        print(f"未找到维度={args.dimension!r} 的记录。")
        return

    for idx, it in enumerate(items, start=1):
        print(f"{idx:03d} | {_fmt_ts(it.get('publish_time'))} | {it.get('project_name') or '-'}")
        print(f"      tech_node: {it.get('tech_node') or '-'}")
        print(f"      tag/score: {(it.get('evolution_tag') or '-')} / {it.get('impact_score') or 1}")
        if it.get("summary"):
            print(f"      summary  : {it.get('summary')}")
        if it.get("source_url"):
            print(f"      url      : {it.get('source_url')}")
        print()


if __name__ == "__main__":
    main()

