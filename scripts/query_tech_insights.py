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
    since_ts: Optional[int] = None,
    until_ts: Optional[int] = None,
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
    """
    params: list[Any] = [dimension]
    if since_ts is not None:
        sql += " AND s.publish_time >= ?"
        params.append(since_ts)
    if until_ts is not None:
        sql += " AND s.publish_time <= ?"
        params.append(until_ts)
    sql += " ORDER BY s.publish_time ASC, i.insight_id ASC"
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


def _date_to_start_ts(date_str: str) -> int:
    """解析 YYYY-MM-DD，返回当日 00:00:00 的时间戳。"""
    dt = _dt.datetime.strptime(date_str.strip(), "%Y-%m-%d")
    return int(dt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())


def _date_to_end_ts(date_str: str) -> int:
    """解析 YYYY-MM-DD，返回当日 23:59:59 的时间戳。"""
    dt = _dt.datetime.strptime(date_str.strip(), "%Y-%m-%d")
    return int(dt.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp())


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
    parser.add_argument(
        "--months",
        type=int,
        default=None,
        help="仅查询最近 N 个月内的记录（与 --since/--until 同时存在时优先）",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="仅查询最近 N 天内的记录（与 --since/--until 同时存在时优先）",
    )
    parser.add_argument(
        "--since",
        default=None,
        metavar="YYYY-MM-DD",
        help="起始日期（闭区间，含当日 00:00:00）",
    )
    parser.add_argument(
        "--until",
        default=None,
        metavar="YYYY-MM-DD",
        help="结束日期（闭区间，含当日 23:59:59）",
    )
    args = parser.parse_args()

    if args.list_dimensions:
        print("\n".join(get_supported_dimensions()))
        return

    if not args.dimension:
        raise SystemExit("请提供 --dimension，或使用 --list-dimensions 查看可用维度。")

    since_ts: Optional[int] = None
    until_ts: Optional[int] = None
    now = _dt.datetime.now()
    if args.months is not None:
        since_ts = int((now - _dt.timedelta(days=args.months * 30)).timestamp())
        until_ts = int(now.timestamp())
    elif args.days is not None:
        since_ts = int((now - _dt.timedelta(days=args.days)).timestamp())
        until_ts = int(now.timestamp())
    else:
        if args.since is not None:
            since_ts = _date_to_start_ts(args.since)
        if args.until is not None:
            until_ts = _date_to_end_ts(args.until)

    items = fetch_dimension_timeline(
        db_path=args.db,
        dimension=args.dimension,
        limit=args.limit,
        since_ts=since_ts,
        until_ts=until_ts,
    )
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

