from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import database as db
from analyzer import LlmError, OpenAIAnalyzer
from coze_client import CozeClient, CozeClientConfig
from config import load_config
from sync_engine import SyncEngine


def main() -> None:
    # --- 基础配置（skill 独立：默认 DB 在上级 assets/data.db）---
    base_dir = Path(__file__).resolve().parent
    default_db = base_dir.parent / "assets" / "data.db"
    db_path = Path(os.getenv("DB_PATH", str(default_db)))
    cfg = load_config()
    test_mode = bool(cfg.test_mode)

    # --- 初始化数据库 ---
    conn = db.connect(db_path)
    db.init_db(conn)

    # --- 初始化客户端/引擎 ---
    coze = CozeClient(CozeClientConfig())
    window_size = int(
        getattr(cfg, "window_size", None) or os.getenv("WINDOW_SIZE", "20")
    )
    engine = SyncEngine(
        conn,
        coze,
        window_size=window_size,
        max_pages=(1 if test_mode else None),
    )

    # 阶段 1：同步列表（增量 + 置顶）
    sync_res = engine.sync_video_list()
    max_time_before = sync_res.max_time_before or 0
    print(
        f"[sync] max_time_before={sync_res.max_time_before} "
        f"top_ids={sync_res.top_ids} "
        f"inserted_incremental={len(sync_res.inserted_incremental_ids)} "
        f"inserted_backfill={len(sync_res.inserted_backfill_ids)} "
        f"updated_existing={sync_res.updated_existing_count}"
    )

    # 阶段 2：文案提取（批处理循环：处理完再进入下一阶段）
    extract_limit = int(
        getattr(cfg, "extract_limit", None) or os.getenv("EXTRACT_LIMIT", "200")
    )
    extract_workers = max(1, int(getattr(cfg, "extract_workers", 5) or 5))
    extracted_ok = 0
    extracted_err = 0
    while True:
        to_extract = db.list_sources_needing_text(
            conn,
            min_publish_time_exclusive=max_time_before,
            limit=extract_limit,
        )
        if not to_extract:
            break

        print(
            f"[extract] batch_size={len(to_extract)} limit={extract_limit} "
            f"(publish_time > {max_time_before}) workers={extract_workers}"
        )

        # 测试模式：阶段2只提取 1 条
        if test_mode:
            to_extract = to_extract[:1]

        # 并发请求外部接口（Coze），但 DB 更新保持在主线程串行执行
        if extract_workers == 1 or len(to_extract) <= 1:
            for row in to_extract:
                sid = row["source_id"]
                url = row["source_url"]
                try:
                    text = coze.get_video_content(url)
                    db.update_source_content(conn, sid, text, status="text_extracted")
                    extracted_ok += 1
                    print(f"[extract] ok source_id={sid} text_len={len(text)}")
                except Exception as e:  # noqa: BLE001
                    db.update_source_status(conn, sid, "error")
                    extracted_err += 1
                    print(f"[extract] error source_id={sid} err={e}")
        else:
            with ThreadPoolExecutor(max_workers=extract_workers) as ex:
                future_map = {
                    ex.submit(coze.get_video_content, row["source_url"]): row["source_id"]
                    for row in to_extract
                }
                for fut in as_completed(future_map):
                    sid = future_map[fut]
                    try:
                        text = fut.result()
                        db.update_source_content(conn, sid, text, status="text_extracted")
                        extracted_ok += 1
                        print(f"[extract] ok source_id={sid} text_len={len(text)}")
                    except Exception as e:  # noqa: BLE001
                        db.update_source_status(conn, sid, "error")
                        extracted_err += 1
                        print(f"[extract] error source_id={sid} err={e}")

    print(f"[extract] done ok={extracted_ok} error={extracted_err}")

    # 阶段 3：LLM 结构化分析（只分析新增 create_time > max_time_before）
    try:
        analyzer = OpenAIAnalyzer.from_config(
            api_key=cfg.openai_api_key,
            base_url=cfg.openai_base_url,
            model=cfg.openai_model,
        )
    except LlmError as e:
        print(f"[analyze] skip: {e}")
        conn.close()
        return

    # 阶段 3：LLM 分析（批处理循环：分析完再结束）
    analyze_limit = int(os.getenv("ANALYZE_LIMIT", "200"))
    analyze_workers = max(1, int(getattr(cfg, "analyze_workers", 5) or 5))
    analyzed_ok = 0
    analyzed_err = 0

    # 每个线程持有独立的 OpenAIAnalyzer（requests.Session 非严格线程安全）
    _tls = threading.local()

    def _analyze_one(title: str, content_text: str):
        if not hasattr(_tls, "analyzer"):
            _tls.analyzer = OpenAIAnalyzer.from_config(
                api_key=cfg.openai_api_key,
                base_url=cfg.openai_base_url,
                model=cfg.openai_model,
            )
        return _tls.analyzer.analyze(title=title, content_text=content_text)

    # 先处理所有待分析的视频（包括历史遗留数据）
    print(f"[analyze] 处理所有待分析的视频（包括历史数据）...")
    while True:
        to_analyze = db.list_sources_needing_analysis(
            conn,
            min_publish_time_exclusive=None,  # 处理所有待分析的视频
            limit=analyze_limit,
        )
        if not to_analyze:
            break

        print(
            f"[analyze] batch_size={len(to_analyze)} limit={analyze_limit} "
            f"(publish_time > {max_time_before}) workers={analyze_workers}"
        )

        # 测试模式：阶段3最多分析 1 条（通常阶段2也只提取 1 条）
        if test_mode:
            to_analyze = to_analyze[:1]

        # 并发调用 LLM，但 DB 写入在主线程串行执行
        if analyze_workers == 1 or len(to_analyze) <= 1:
            for row in to_analyze:
                sid = row["source_id"]
                title = row["title"] or ""
                content_text = row["content_text"] or ""
                if not content_text.strip():
                    db.update_source_status(conn, sid, "error")
                    analyzed_err += 1
                    print(f"[analyze] error source_id={sid} empty_content")
                    continue

                try:
                    res = analyzer.analyze(title=title, content_text=content_text)
                    db.delete_tech_insights_for_source(conn, sid)
                    db.insert_tech_insights(conn, res.to_db_rows(source_id=sid))
                    db.update_source_status(conn, sid, "analyzed")
                    analyzed_ok += 1
                    print(f"[analyze] ok source_id={sid} insights={len(res.items)}")
                except Exception as e:  # noqa: BLE001
                    db.update_source_status(conn, sid, "error")
                    analyzed_err += 1
                    print(f"[analyze] error source_id={sid} err={e}")
        else:
            with ThreadPoolExecutor(max_workers=analyze_workers) as ex:
                future_map = {}
                for row in to_analyze:
                    sid = row["source_id"]
                    title = row["title"] or ""
                    content_text = row["content_text"] or ""
                    if not content_text.strip():
                        db.update_source_status(conn, sid, "error")
                        analyzed_err += 1
                        print(f"[analyze] error source_id={sid} empty_content")
                        continue
                    future_map[ex.submit(_analyze_one, title, content_text)] = sid

                for fut in as_completed(future_map):
                    sid = future_map[fut]
                    try:
                        res = fut.result()
                        db.delete_tech_insights_for_source(conn, sid)
                        db.insert_tech_insights(conn, res.to_db_rows(source_id=sid))
                        db.update_source_status(conn, sid, "analyzed")
                        analyzed_ok += 1
                        print(f"[analyze] ok source_id={sid} insights={len(res.items)}")
                    except Exception as e:  # noqa: BLE001
                        db.update_source_status(conn, sid, "error")
                        analyzed_err += 1
                        print(f"[analyze] error source_id={sid} err={e}")

    print(f"[analyze] done ok={analyzed_ok} error={analyzed_err}")

    conn.close()


if __name__ == "__main__":
    main()

