"""
環境設定を管理するモジュール。
"""

import os
import re
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
        # ウィンドウ設定
        "TARGET_WINDOW_TITLE": os.getenv("TARGET_WINDOW_TITLE", "LDPlayer"),
        
        # キャプチャ設定
        "CAPTURE_INTERVAL": clean_value(os.getenv("CAPTURE_INTERVAL", "1.0")),
        
        # OCR設定
        "TESSERACT_PATH": os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        "OCR_LANGUAGE": os.getenv("OCR_LANGUAGE", "jpn"),
        "OCR_CONFIG": os.getenv("OCR_CONFIG", "--psm 6"),
        "OCR_PREPROCESSING_ENABLED": os.getenv("OCR_PREPROCESSING_ENABLED", "True"),
        
        # 棒読みちゃん設定
        "BOUYOMI_HOST": os.getenv("BOUYOMI_HOST", "127.0.0.1"),
        "BOUYOMI_PORT": os.getenv("BOUYOMI_PORT", "50001"),
        
        # メッセージ検出設定
        "MAX_MESSAGE_CACHE": os.getenv("MAX_MESSAGE_CACHE", "1000"),
        "CACHE_CLEAN_THRESHOLD": os.getenv("CACHE_CLEAN_THRESHOLD", "1200"),
        "MIN_MESSAGE_LENGTH": os.getenv("MIN_MESSAGE_LENGTH", "2"),
        
        # 棒読みちゃん設定（拡張）
        "BOUYOMI_ENABLED": os.getenv("BOUYOMI_ENABLED", "true"),
        "BOUYOMI_RETRY_INTERVAL": os.getenv("BOUYOMI_RETRY_INTERVAL", "5"),
        "BOUYOMI_VOICE_TYPE": os.getenv("BOUYOMI_VOICE_TYPE", "0"),
        "BOUYOMI_VOICE_SPEED": os.getenv("BOUYOMI_VOICE_SPEED", "-1"),
        "BOUYOMI_VOICE_TONE": os.getenv("BOUYOMI_VOICE_TONE", "-1"),
        "BOUYOMI_VOICE_VOLUME": os.getenv("BOUYOMI_VOICE_VOLUME", "-1"),
        
        # ログ設定
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "LOG_FILE": os.getenv("LOG_FILE", "app.log"),
    }
    
    return config

def clean_value(value: str) -> str:
    """環境変数の値からコメントを取り除きます。

    Args:
        value: 環境変数の値

    Returns:
        str: コメントを取り除いた値
    """
    if value is None:
        return ""
    
    # '#'以降の文字列を取り除く
    return re.sub(r'#.*$', '', value).strip()

class Config(dict):
    """
    環境設定を辞書として管理するクラス。
    """
    def __init__(self):
        super().__init__(**load_config())

    def get(self, key: str, default=None):
        return super().get(key, default)