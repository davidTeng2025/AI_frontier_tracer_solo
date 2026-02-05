from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from pydantic import BaseModel, ConfigDict, TypeAdapter

import utils


class CozeVideoItem(BaseModel):
    """GetVideoList 返回的单条视频元数据。"""

    model_config = ConfigDict(extra="forbid")

    aweme_id: str
    title: Optional[str] = None
    create_time: int
    url: str


_VideoListAdapter = TypeAdapter(list[CozeVideoItem])


class CozeApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class CozeClientConfig:
    # 仅 workflow 模式：复用 utils.py（cozepy）
    max_retries: int = 3
    backoff_initial_s: float = 0.6
    backoff_max_s: float = 8.0


@dataclass(frozen=True)
class VideoListPage:
    items: list[CozeVideoItem]
    has_more: bool
    next_cursor: Optional[int]


class CozeClient:
    """仅 workflow 模式：复用 utils.get_video_list / utils.get_video_content。"""

    def __init__(self, config: CozeClientConfig):
        self.config = config

    def get_video_list(self) -> list[CozeVideoItem]:
        # 兼容旧调用：只返回第一页的 items
        return self.get_video_list_page(max_cursor=0, count=20).items

    def get_video_list_page(self, *, max_cursor: int = 0, count: int = 20) -> VideoListPage:
        """
        获取一页视频列表（utils.get_video_list 每次默认抓取 count 条，并返回 has_more / max_cursor）。
        - max_cursor: 上一页返回的 max_cursor（初次传 0）
        - count: 每页条数（默认 20）
        """
        # utils.get_video_list 已内置 count=20；这里仍显式传入以满足“窗口可配置”
        raw = self._call_utils_with_retry(
            lambda: utils.get_video_list(max_cursor=max_cursor, count=count)
        )
        items, has_more, next_cursor = self._extract_video_list_page(raw)
        normalized: list[dict[str, Any]] = []
        for it in items:
            aweme_id = it.get("aweme_id") or it.get("item_id")
            url = it.get("url") or it.get("link")
            create_time = it.get("create_time")
            title = it.get("title") or it.get("caption")
            if not aweme_id or not url or create_time is None:
                continue
            normalized.append(
                {
                    "aweme_id": str(aweme_id),
                    "title": title,
                    "create_time": int(create_time),
                    "url": str(url),
                }
            )
        parsed_items = _VideoListAdapter.validate_python(normalized)
        return VideoListPage(items=parsed_items, has_more=has_more, next_cursor=next_cursor)

    def get_video_content(self, url: str) -> str:
        raw = self._call_utils_with_retry(lambda: utils.get_video_content(url))
        text = self._extract_content_text(raw)
        if not text.strip():
            raise CozeApiError(f"workflow 返回空文案 url={url}")
        return text

    def _call_utils_with_retry(self, fn):
        last_err: Optional[BaseException] = None
        for attempt in range(self.config.max_retries + 1):
            try:
                return fn()
            except Exception as e:  # noqa: BLE001
                last_err = e
                if attempt >= self.config.max_retries:
                    break
                self._sleep_backoff(attempt)
        raise CozeApiError("调用 utils workflow 失败") from last_err

    def _extract_video_list_page(self, raw: Any) -> Tuple[list[dict[str, Any]], bool, Optional[int]]:
        """
        utils.get_video_list() 的返回示例里，视频列表通常在：
        - raw["output"]["list"] 或 raw["code"]["list"]
        同时包含：
        - has_more: 是否还有下一页
        - max_cursor: 下一页入参
        """
        if isinstance(raw, dict):
            container = None
            for key in ("output", "code"):
                v = raw.get(key)
                if isinstance(v, dict) and isinstance(v.get("list"), list):
                    container = v
                    break
            if container is None and isinstance(raw.get("list"), list):
                container = raw

            if container is None:
                raise CozeApiError(f"无法从 workflow 返回中解析视频列表：{str(raw)[:500]}")

            items = [x for x in container.get("list", []) if isinstance(x, dict)]
            has_more = bool(container.get("has_more", False))
            next_cursor = container.get("max_cursor", None)
            try:
                next_cursor = int(next_cursor) if next_cursor is not None else None
            except Exception:  # noqa: BLE001
                next_cursor = None
            return items, has_more, next_cursor

        raise CozeApiError(f"无法从 workflow 返回中解析视频列表：{str(raw)[:500]}")

    def _extract_content_text(self, raw: Any) -> str:
        """
        utils.get_video_content() 的返回示例里，文案通常在：
        - raw["transcripts"][i]["text"]
        """
        if isinstance(raw, dict):
            if isinstance(raw.get("text"), str):
                return raw["text"]
            transcripts = raw.get("transcripts")
            if isinstance(transcripts, list):
                parts: list[str] = []
                for t in transcripts:
                    if isinstance(t, dict) and isinstance(t.get("text"), str) and t["text"].strip():
                        parts.append(t["text"].strip())
                return "\n".join(parts)
            output = raw.get("output")
            if isinstance(output, dict) and isinstance(output.get("text"), str):
                return output["text"]
        return ""

    def _sleep_backoff(self, attempt: int) -> None:
        # 指数退避 + 抖动
        base = min(
            self.config.backoff_max_s,
            self.config.backoff_initial_s * (2**attempt),
        )
        jitter = random.uniform(0, base * 0.2)
        time.sleep(base + jitter)

