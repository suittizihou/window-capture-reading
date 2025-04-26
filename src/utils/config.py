"""
環境設定を管理するモジュール。
"""

import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

def load_config() -> Dict[str, str]:
    """環境変数から設定を読み込みます。

    Returns:
        Dict[str, str]: 設定値の辞書
    """
    # .envファイルの読み込み
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    # 必要な設定値を取得
    config = {
        "TARGET_WINDOW_TITLE": os.getenv("TARGET_WINDOW_TITLE", "LDPlayer"),
        "CAPTURE_INTERVAL": os.getenv("CAPTURE_INTERVAL", "1.0"),
        "BOUYOMI_HOST": os.getenv("BOUYOMI_HOST", "127.0.0.1"),
        "BOUYOMI_PORT": os.getenv("BOUYOMI_PORT", "50001"),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "LOG_FILE": os.getenv("LOG_FILE", "app.log"),
    }
    
    return config
