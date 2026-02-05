from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field


PROCESS_STATUS = Literal["pending", "text_extracted", "analyzed", "error"]


SCHEMA_SQL = """
-- =========================
-- 新版：原始来源表 raw_sources
-- =========================
CREATE TABLE IF NOT EXISTS raw_sources (
    source_id TEXT PRIMARY KEY,       -- 来源唯一 ID（例如抖音 aweme_id）
    title TEXT,                       -- 标题
    publish_time INTEGER,             -- 发布时间戳
    source_url TEXT,                  -- 来源链接
    content_text TEXT,                -- 原始文案/正文（可为空，后续提取）
    process_status TEXT DEFAULT 'pending', -- pending, text_extracted, analyzed, error
    is_top INTEGER DEFAULT 0,         -- 1为置顶，0为普通
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_publish_time ON raw_sources(publish_time);

-- =========================
-- 新版：技术进化流表 tech_insights
-- =========================
CREATE TABLE IF NOT EXISTS tech_insights (
    insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT,
    dimension TEXT NOT NULL,
    project_name TEXT,
    tech_node TEXT,
    evolution_tag TEXT,
    impact_score INTEGER DEFAULT 1,
    summary TEXT,
    FOREIGN KEY (source_id) REFERENCES raw_sources(source_id)
);

-- 为维度和项目创建索引（时间轴排序通过 join raw_sources.publish_time 完成）
CREATE INDEX IF NOT EXISTS idx_dimension_time ON tech_insights(dimension);
CREATE INDEX IF NOT EXISTS idx_project ON tech_insights(project_name);

-- （可选）技术节点关系表：用于构建“脉络链接”
CREATE TABLE IF NOT EXISTS insight_links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_insight_id INTEGER,
    child_insight_id INTEGER,
    relation_type TEXT,
    FOREIGN KEY (parent_insight_id) REFERENCES tech_insights(insight_id),
    FOREIGN KEY (child_insight_id) REFERENCES tech_insights(insight_id)
);

-- =========================
-- 旧版表（保留，避免已有 DB 失效；新逻辑不再写入）
-- =========================
CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    title TEXT,
    create_time INTEGER,
    video_url TEXT,
    content_text TEXT,
    process_status TEXT DEFAULT 'pending',
    is_top INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT,
    tech_dimension TEXT,
    key_info TEXT,
    summary TEXT,
    FOREIGN KEY (video_id) REFERENCES videos(video_id)
);

CREATE INDEX IF NOT EXISTS idx_time ON videos(create_time);
CREATE INDEX IF NOT EXISTS idx_dim ON ai_skills(tech_dimension);
"""


class VideoMeta(BaseModel):
    """写入 videos 表的元数据（不包含分析结果）。"""

    model_config = ConfigDict(extra="forbid")

    video_id: str = Field(..., description="对应 aweme_id")
    title: Optional[str] = None
    create_time: int
    video_url: str
    content_text: Optional[str] = None
    process_status: PROCESS_STATUS = "pending"
    is_top: int = 0


class AiSkillRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    video_id: str
    tech_dimension: str
    key_info: str
    summary: str


class RawSourceMeta(BaseModel):
    """写入 raw_sources 表的元数据（对应阶段 1/2）。"""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    title: Optional[str] = None
    publish_time: int
    source_url: str
    content_text: Optional[str] = None
    process_status: PROCESS_STATUS = "pending"
    is_top: int = 0


class TechInsightRow(BaseModel):
    """写入 tech_insights 表的结构化洞察（对应阶段 3）。"""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    dimension: str
    project_name: Optional[str] = None
    tech_node: Optional[str] = None
    evolution_tag: Optional[str] = None
    impact_score: int = 1
    summary: Optional[str] = None


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


# =========================
# 新版：raw_sources / tech_insights
# =========================


def get_max_publish_time(conn: sqlite3.Connection) -> Optional[int]:
    row = conn.execute("SELECT MAX(publish_time) AS max_time FROM raw_sources").fetchone()
    if not row:
        return None
    max_time = row["max_time"]
    return int(max_time) if max_time is not None else None


def source_exists(conn: sqlite3.Connection, source_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM raw_sources WHERE source_id = ? LIMIT 1",
        (source_id,),
    ).fetchone()
    return row is not None


def upsert_raw_source_meta(conn: sqlite3.Connection, source: RawSourceMeta) -> None:
    """
    如果 source_id 已存在则更新（含 is_top），否则插入。
    注意：updated_at 会被刷新为 CURRENT_TIMESTAMP。
    """
    source = RawSourceMeta.model_validate(source)
    conn.execute(
        """
        INSERT INTO raw_sources (source_id, title, publish_time, source_url, content_text, process_status, is_top)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET
            title = excluded.title,
            publish_time = excluded.publish_time,
            source_url = excluded.source_url,
            content_text = COALESCE(excluded.content_text, raw_sources.content_text),
            process_status = COALESCE(excluded.process_status, raw_sources.process_status),
            is_top = excluded.is_top,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            source.source_id,
            source.title,
            source.publish_time,
            source.source_url,
            source.content_text,
            source.process_status,
            int(source.is_top),
        ),
    )
    conn.commit()


def update_source_is_top(conn: sqlite3.Connection, source_id: str, is_top: int) -> None:
    conn.execute(
        "UPDATE raw_sources SET is_top = ?, updated_at = CURRENT_TIMESTAMP WHERE source_id = ?",
        (int(is_top), source_id),
    )
    conn.commit()


def update_source_content(
    conn: sqlite3.Connection,
    source_id: str,
    content_text: str,
    status: PROCESS_STATUS = "text_extracted",
) -> None:
    conn.execute(
        """
        UPDATE raw_sources
        SET content_text = ?, process_status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE source_id = ?
        """,
        (content_text, status, source_id),
    )
    conn.commit()


def update_source_status(
    conn: sqlite3.Connection,
    source_id: str,
    status: PROCESS_STATUS,
) -> None:
    conn.execute(
        "UPDATE raw_sources SET process_status = ?, updated_at = CURRENT_TIMESTAMP WHERE source_id = ?",
        (status, source_id),
    )
    conn.commit()


def clear_is_top_except_sources(conn: sqlite3.Connection, keep_source_ids: Sequence[str]) -> None:
    keep = [sid for sid in keep_source_ids if sid]
    if not keep:
        conn.execute(
            "UPDATE raw_sources SET is_top = 0, updated_at = CURRENT_TIMESTAMP WHERE is_top = 1"
        )
        conn.commit()
        return

    placeholders = ",".join(["?"] * len(keep))
    conn.execute(
        f"""
        UPDATE raw_sources
        SET is_top = 0, updated_at = CURRENT_TIMESTAMP
        WHERE is_top = 1 AND source_id NOT IN ({placeholders})
        """,
        tuple(keep),
    )
    conn.commit()


def list_sources_needing_text(
    conn: sqlite3.Connection,
    min_publish_time_exclusive: Optional[int] = None,
    limit: int = 100,
) -> list[sqlite3.Row]:
    """
    阶段 2：文案提取
    - content_text 为空 或 process_status = 'pending'
    - 排除 analyzed/error，避免死循环
    """
    if min_publish_time_exclusive is None:
        return conn.execute(
            """
            SELECT * FROM raw_sources
            WHERE (content_text IS NULL OR TRIM(content_text) = '' OR process_status = 'pending')
              AND process_status NOT IN ('analyzed', 'error')
            ORDER BY publish_time DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return conn.execute(
        """
        SELECT * FROM raw_sources
        WHERE (content_text IS NULL OR TRIM(content_text) = '' OR process_status = 'pending')
          AND process_status NOT IN ('analyzed', 'error')
          AND publish_time > ?
        ORDER BY publish_time DESC
        LIMIT ?
        """,
        (min_publish_time_exclusive, limit),
    ).fetchall()


def list_sources_needing_analysis(
    conn: sqlite3.Connection,
    min_publish_time_exclusive: Optional[int] = None,
    limit: int = 100,
) -> list[sqlite3.Row]:
    """
    阶段 3：LLM 分析
    默认分析 text_extracted；可通过 min_publish_time_exclusive 只分析“新增”来源。
    """
    if min_publish_time_exclusive is None:
        return conn.execute(
            """
            SELECT * FROM raw_sources
            WHERE process_status = 'text_extracted'
            ORDER BY publish_time DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return conn.execute(
        """
        SELECT * FROM raw_sources
        WHERE process_status = 'text_extracted'
          AND publish_time > ?
        ORDER BY publish_time DESC
        LIMIT ?
        """,
        (min_publish_time_exclusive, limit),
    ).fetchall()


def delete_tech_insights_for_source(conn: sqlite3.Connection, source_id: str) -> None:
    conn.execute("DELETE FROM tech_insights WHERE source_id = ?", (source_id,))
    conn.commit()


def insert_tech_insights(conn: sqlite3.Connection, rows: Sequence[TechInsightRow]) -> None:
    validated = [TechInsightRow.model_validate(r) for r in rows]
    conn.executemany(
        """
        INSERT INTO tech_insights
          (source_id, dimension, project_name, tech_node, evolution_tag, impact_score, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r.source_id,
                r.dimension,
                r.project_name,
                r.tech_node,
                r.evolution_tag,
                int(r.impact_score),
                r.summary,
            )
            for r in validated
        ],
    )
    conn.commit()


def get_max_create_time(conn: sqlite3.Connection) -> Optional[int]:
    row = conn.execute("SELECT MAX(create_time) AS max_time FROM videos").fetchone()
    if not row:
        return None
    max_time = row["max_time"]
    return int(max_time) if max_time is not None else None


def video_exists(conn: sqlite3.Connection, video_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM videos WHERE video_id = ? LIMIT 1",
        (video_id,),
    ).fetchone()
    return row is not None


def upsert_video_meta(conn: sqlite3.Connection, video: VideoMeta) -> None:
    """
    如果 video_id 已存在则更新（含 is_top），否则插入。
    注意：updated_at 会被刷新为 CURRENT_TIMESTAMP。
    """
    video = VideoMeta.model_validate(video)
    conn.execute(
        """
        INSERT INTO videos (video_id, title, create_time, video_url, content_text, process_status, is_top)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
            title = excluded.title,
            create_time = excluded.create_time,
            video_url = excluded.video_url,
            content_text = COALESCE(excluded.content_text, videos.content_text),
            process_status = COALESCE(excluded.process_status, videos.process_status),
            is_top = excluded.is_top,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            video.video_id,
            video.title,
            video.create_time,
            video.video_url,
            video.content_text,
            video.process_status,
            int(video.is_top),
        ),
    )
    conn.commit()


def update_is_top(conn: sqlite3.Connection, video_id: str, is_top: int) -> None:
    conn.execute(
        "UPDATE videos SET is_top = ?, updated_at = CURRENT_TIMESTAMP WHERE video_id = ?",
        (int(is_top), video_id),
    )
    conn.commit()


def update_video_content(
    conn: sqlite3.Connection,
    video_id: str,
    content_text: str,
    status: PROCESS_STATUS = "text_extracted",
) -> None:
    conn.execute(
        """
        UPDATE videos
        SET content_text = ?, process_status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE video_id = ?
        """,
        (content_text, status, video_id),
    )
    conn.commit()


def update_video_status(
    conn: sqlite3.Connection,
    video_id: str,
    status: PROCESS_STATUS,
) -> None:
    conn.execute(
        "UPDATE videos SET process_status = ?, updated_at = CURRENT_TIMESTAMP WHERE video_id = ?",
        (status, video_id),
    )
    conn.commit()


def clear_is_top_except(conn: sqlite3.Connection, keep_video_ids: Sequence[str]) -> None:
    """
    将除 keep_video_ids 外的所有置顶标记清空（is_top=0）。
    用于“置顶位随列表变化”的场景，避免历史置顶残留。
    """
    keep = [vid for vid in keep_video_ids if vid]
    if not keep:
        conn.execute("UPDATE videos SET is_top = 0, updated_at = CURRENT_TIMESTAMP WHERE is_top = 1")
        conn.commit()
        return

    placeholders = ",".join(["?"] * len(keep))
    conn.execute(
        f"""
        UPDATE videos
        SET is_top = 0, updated_at = CURRENT_TIMESTAMP
        WHERE is_top = 1 AND video_id NOT IN ({placeholders})
        """,
        tuple(keep),
    )
    conn.commit()


def list_videos_needing_text(
    conn: sqlite3.Connection,
    min_create_time_exclusive: Optional[int] = None,
    limit: int = 100,
) -> list[sqlite3.Row]:
    """
    阶段 2：文案提取
    - content_text 为空 或 process_status = 'pending'
    """
    if min_create_time_exclusive is None:
        return conn.execute(
            """
            SELECT * FROM videos
            WHERE (content_text IS NULL OR TRIM(content_text) = '' OR process_status = 'pending')
              AND process_status NOT IN ('analyzed', 'error')
            ORDER BY create_time DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return conn.execute(
        """
        SELECT * FROM videos
        WHERE (content_text IS NULL OR TRIM(content_text) = '' OR process_status = 'pending')
          AND process_status NOT IN ('analyzed', 'error')
          AND create_time > ?
        ORDER BY create_time DESC
        LIMIT ?
        """,
        (min_create_time_exclusive, limit),
    ).fetchall()


def list_videos_needing_analysis(
    conn: sqlite3.Connection,
    min_create_time_exclusive: Optional[int] = None,
    limit: int = 100,
) -> list[sqlite3.Row]:
    """
    阶段 3：LLM 分析
    默认分析 text_extracted 的视频；可通过 min_create_time_exclusive 只分析“新增”视频。
    """
    if min_create_time_exclusive is None:
        return conn.execute(
            """
            SELECT * FROM videos
            WHERE process_status = 'text_extracted'
            ORDER BY create_time DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return conn.execute(
        """
        SELECT * FROM videos
        WHERE process_status = 'text_extracted'
          AND create_time > ?
        ORDER BY create_time DESC
        LIMIT ?
        """,
        (min_create_time_exclusive, limit),
    ).fetchall()


def insert_ai_skill(conn: sqlite3.Connection, row: AiSkillRow) -> None:
    row = AiSkillRow.model_validate(row)
    conn.execute(
        """
        INSERT INTO ai_skills (video_id, tech_dimension, key_info, summary)
        VALUES (?, ?, ?, ?)
        """,
        (row.video_id, row.tech_dimension, row.key_info, row.summary),
    )
    conn.commit()


def insert_ai_skills_for_video(
    conn: sqlite3.Connection,
    video_id: str,
    dimensions: Sequence[str],
    key_info: str,
    summary: str,
) -> None:
    rows = [
        AiSkillRow(
            video_id=video_id,
            tech_dimension=dim,
            key_info=key_info,
            summary=summary,
        )
        for dim in dimensions
    ]
    conn.executemany(
        """
        INSERT INTO ai_skills (video_id, tech_dimension, key_info, summary)
        VALUES (?, ?, ?, ?)
        """,
        [(r.video_id, r.tech_dimension, r.key_info, r.summary) for r in rows],
    )
    conn.commit()

