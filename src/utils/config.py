"""
環境設定を管理するモジュール。
"""

import os
import re
from pathlib import Path
from typing import Dict
import json
import sys

from dotenv import load_dotenv

def get_settings_json_path() -> Path:
    """
    実行環境に応じて設定ファイルの保存パスを返す。
    exe化（PyInstaller）されている場合はexeと同じ階層のconfig/に保存。
    それ以外は従来通りプロジェクトルートのconfig/。
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # PyInstallerでexe化されている場合
        exe_dir = Path(sys.executable).parent
        return exe_dir / "config" / "settings.json"
    else:
        # 通常のスクリプト実行
        return Path(__file__).parent.parent.parent / "config" / "settings.json"

DEFAULT_CONFIG = {
    "TARGET_WINDOW_TITLE": "LDPlayer",
    "CAPTURE_INTERVAL": "1.0",
    "BOUYOMI_PORT": "50001",
    "BOUYOMI_VOICE_TYPE": "0",
    # 必要に応じて他のデフォルト値もここに追加
}

def load_config() -> Dict[str, str]:
    """JSONファイルから設定を読み込みます。"""
    settings_path = get_settings_json_path()
    if settings_path.exists():
        with open(settings_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = DEFAULT_CONFIG.copy()
    # デフォルト値で埋める
    for k, v in DEFAULT_CONFIG.items():
        config.setdefault(k, v)
    return config

def save_config(config: Dict[str, str]) -> None:
    """設定をJSONファイルに保存します。"""
    settings_path = get_settings_json_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "w", encoding="utf-8") as f:
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