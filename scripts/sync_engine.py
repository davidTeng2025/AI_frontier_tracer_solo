from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import database as db
from coze_client import CozeClient


@dataclass(frozen=True)
class SyncResult:
    max_time_before: Optional[int]
    top_ids: list[str]
    inserted_incremental_ids: list[str]
    inserted_backfill_ids: list[str]
    updated_existing_count: int


class SyncEngine:
    """
    阶段 1：增量数据获取 (Data Ingestion)

    - 调用 Coze GetVideoList 获取列表
    - 置顶与重复过滤：
      - 已存在：只更新 is_top，跳过增量处理
      - 不存在：写入 videos；并根据 max_time_before 判断增量/补录
    - 置顶规则：
      - 当前列表前 3 个视为 top3（is_top=1）
      - 同时清理历史置顶：除 top3 外的 is_top 统一置 0
    """

    def __init__(
        self,
        conn,
        client: CozeClient,
        *,
        top_n: int = 3,
        window_size: int = 20,
        max_pages: Optional[int] = None,
    ):
        self.conn = conn
        self.client = client
        self.top_n = top_n
        self.window_size = window_size
        self.max_pages = max_pages

    def sync_video_list(self) -> SyncResult:
        # 新版以 raw_sources.publish_time 为准
        max_time_before = db.get_max_publish_time(self.conn)
        inserted_incremental: list[str] = []
        inserted_backfill: list[str] = []
        updated_existing = 0
        top_ids: list[str] = []

        # 翻页游标：utils.get_video_list 初次传 0；后续用返回的 max_cursor
        cursor = 0
        seen_cursors: set[int] = set()
        first_page = True
        pages_fetched = 0

        # 初次抓取（库为空）：持续翻页直到 has_more=false
        if max_time_before is None:
            while True:
                page = self.client.get_video_list_page(max_cursor=cursor, count=self.window_size)
                pages_fetched += 1
                if first_page:
                    top_ids = [it.aweme_id for it in page.items[: self.top_n]]
                    first_page = False

                for it in page.items:
                    desired_is_top = 1 if it.aweme_id in top_ids else 0

                    if db.source_exists(self.conn, it.aweme_id):
                        db.update_source_is_top(self.conn, it.aweme_id, desired_is_top)
                        updated_existing += 1
                        continue

                    meta = db.RawSourceMeta(
                        source_id=it.aweme_id,
                        title=it.title,
                        publish_time=it.create_time,
                        source_url=it.url,
                        content_text=None,
                        process_status="pending",
                        is_top=desired_is_top,
                    )
                    db.upsert_raw_source_meta(self.conn, meta)
                    inserted_incremental.append(it.aweme_id)

                if self.max_pages is not None and pages_fetched >= self.max_pages:
                    break
                if not page.has_more:
                    break
                if page.next_cursor is None:
                    break
                if page.next_cursor == cursor:
                    break
                if page.next_cursor in seen_cursors:
                    break
                seen_cursors.add(cursor)
                cursor = page.next_cursor

        # 增量抓取（库非空）：窗口默认 20；若窗口内全是老视频则认为无新视频
        else:
            while True:
                page = self.client.get_video_list_page(max_cursor=cursor, count=self.window_size)
                pages_fetched += 1
                if first_page:
                    top_ids = [it.aweme_id for it in page.items[: self.top_n]]
                    first_page = False

                # 由于列表按时间倒序，遇到老视频后即可视为到达边界
                any_new = False
                hit_old_boundary = False

                for it in page.items:
                    desired_is_top = 1 if it.aweme_id in top_ids else 0

                    if it.create_time <= max_time_before:
                        hit_old_boundary = True
                        # 窗口内的老视频：不插入，只做置顶标记更新（若该视频已存在）
                        if db.source_exists(self.conn, it.aweme_id):
                            db.update_source_is_top(self.conn, it.aweme_id, desired_is_top)
                            updated_existing += 1
                        continue

                    any_new = True

                    # 新视频：插入/更新
                    if db.source_exists(self.conn, it.aweme_id):
                        db.update_source_is_top(self.conn, it.aweme_id, desired_is_top)
                        updated_existing += 1
                        continue

                    meta = db.RawSourceMeta(
                        source_id=it.aweme_id,
                        title=it.title,
                        publish_time=it.create_time,
                        source_url=it.url,
                        content_text=None,
                        process_status="pending",
                        is_top=desired_is_top,
                    )
                    db.upsert_raw_source_meta(self.conn, meta)
                    inserted_incremental.append(it.aweme_id)

                # 窗口内全是老视频：认为没有新视频，结束（无需继续翻页）
                if cursor == 0 and not any_new:
                    break

                # 当前页已触达老视频边界：说明新视频已抓完，结束
                if hit_old_boundary:
                    break

                if self.max_pages is not None and pages_fetched >= self.max_pages:
                    break
                # 当前页全是新视频：可能新视频超过窗口，继续翻页直到遇到老视频
                if not page.has_more or page.next_cursor is None:
                    break
                if page.next_cursor == cursor or page.next_cursor in seen_cursors:
                    break
                seen_cursors.add(cursor)
                cursor = page.next_cursor

        # 清理历史置顶残留：除 top_ids 外都设为 0
        if top_ids:
            db.clear_is_top_except_sources(self.conn, top_ids)

        return SyncResult(
            max_time_before=max_time_before,
            top_ids=top_ids,
            inserted_incremental_ids=inserted_incremental,
            inserted_backfill_ids=inserted_backfill,
            updated_existing_count=updated_existing,
        )

