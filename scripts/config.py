from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AppConfig(BaseModel):
    """
    统一配置入口（优先从本地 config.json 读取，避免要求用户设置环境变量）。
    """

    model_config = ConfigDict(extra="ignore")

    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias="OPENAI_BASE_URL",
    )
    openai_model: str = Field(default="gpt-4o", validation_alias="OPENAI_MODEL")
    test_mode: bool = Field(default=False, validation_alias="TEST_MODE")
    extract_workers: int = Field(default=5, validation_alias="EXTRACT_WORKERS")
    analyze_workers: int = Field(default=5, validation_alias="ANALYZE_WORKERS")
    extract_limit: int = Field(default=200, validation_alias="EXTRACT_LIMIT")
    window_size: int = Field(default=20, validation_alias="WINDOW_SIZE")


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """
    读取 config.json。
    - 默认路径：与本文件同目录的 config.json
    - 可通过 CONFIG_PATH 覆盖
    """
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH")
    path = Path(config_path) if config_path else Path(__file__).resolve().parent / "config.json"

    if not path.exists():
        raise FileNotFoundError(
            f"未找到配置文件：{path}。请创建该文件并填写 OPENAI_API_KEY / OPENAI_BASE_URL / TEST_MODE。"
        )

    data = json.loads(path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(data)

