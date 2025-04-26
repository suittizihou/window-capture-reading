"""
ロギング設定を管理するモジュール。
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict

def setup_logger(config: Dict[str, str]) -> None:
    """アプリケーション全体で使用するロガーを設定します。

    Args:
        config: 環境設定の辞書
    """
    log_level = getattr(logging, config.get("LOG_LEVEL", "INFO"))
    log_file = config.get("LOG_FILE", "app.log")
    
    # ロガーの基本設定
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # フォーマッターの作成
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # コンソールハンドラーの設定
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラーの設定
    log_path = Path(log_file)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10_000_000,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
