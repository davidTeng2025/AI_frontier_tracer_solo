from __future__ import annotations

import argparse
import os
from pathlib import Path

import database as db


def clear_data(db_path: Path) -> None:
    conn = db.connect(db_path)
    # 确保表存在（不会影响既有表结构）
    db.init_db(conn)

    # 先清子表再清主表，避免外键约束问题
    conn.execute("DELETE FROM insight_links;")
    conn.execute("DELETE FROM tech_insights;")
    conn.execute("DELETE FROM raw_sources;")

    # 兼容旧表（如果你仍保留旧数据，也一并清掉）
    conn.execute("DELETE FROM ai_skills;")
    conn.execute("DELETE FROM videos;")

    # 重置自增序列（可选但通常更符合“清空”直觉）
    conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('ai_skills', 'tech_insights', 'insight_links');")
    conn.commit()
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="清空 SQLite 数据（保留表结构）")
    parser.add_argument(
        "--db",
        dest="db_path",
        default=os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "assets" / "data.db")),
        help="SQLite 文件路径（默认读取 DB_PATH，否则使用当前目录 data.db）",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        raise SystemExit(f"数据库文件不存在：{db_path}")

    clear_data(db_path)
    print(f"已清空数据（表保留）：{db_path}")


if __name__ == "__main__":
    main()

