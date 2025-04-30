"""
棒読みちゃん送信メッセージのログ保存ユーティリティ。
"""

import os
from pathlib import Path
import logging
from datetime import datetime

LOG_FILE_PATH = Path(__file__).parent.parent / "resources" / "message_log.txt"


def save_message_log(message: str) -> None:
    """
    メッセージ送信ログをファイルに追記保存します。
    Args:
        message: 送信したテキスト
    """
    try:
        LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{timestamp} {message}\n")
    except Exception as e:
        logging.getLogger(__name__).error(
            f"メッセージログ保存エラー: {e}", exc_info=True
        )
