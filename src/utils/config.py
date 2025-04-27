"""
環境設定を管理するモジュール。
"""

import os
import re
from pathlib import Path
from typing import Dict
import json

from dotenv import load_dotenv

SETTINGS_JSON_PATH = Path(__file__).parent.parent.parent / "config" / "settings.json"

DEFAULT_CONFIG = {
    "TARGET_WINDOW_TITLE": "LDPlayer",
    "CAPTURE_INTERVAL": "1.0",
    "BOUYOMI_PORT": "50001",
    "BOUYOMI_VOICE_TYPE": "0",
    # 必要に応じて他のデフォルト値もここに追加
}

def load_config() -> Dict[str, str]:
    """JSONファイルから設定を読み込みます。"""
    if SETTINGS_JSON_PATH.exists():
        with open(SETTINGS_JSON_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = DEFAULT_CONFIG.copy()
    # デフォルト値で埋める
    for k, v in DEFAULT_CONFIG.items():
        config.setdefault(k, v)
    return config

def save_config(config: Dict[str, str]) -> None:
    """設定をJSONファイルに保存します。"""
    SETTINGS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

class Config(dict):
    """
    環境設定を辞書として管理するクラス。
    """
    def __init__(self):
        super().__init__(**load_config())

    def get(self, key: str, default=None):
        return super().get(key, default)

    def save(self) -> None:
        save_config(self)