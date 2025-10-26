import logging
import sys
from typing import List


def setup_logging() -> None:
    """
    アプリケーション全体のロギング設定を行う。

    製品ビルド時: INFOレベル、ファイル出力のみ
    開発環境: DEBUGレベル、コンソール+ファイル出力
    """
    # PyInstallerでビルドされているか検出
    is_frozen = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")

    # ログフォーマット
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handlers: List[logging.Handler]
    if is_frozen:
        # 製品ビルド: INFOレベル、ファイル出力のみ
        handlers = [
            logging.FileHandler("app.log", encoding="utf-8"),
        ]
        log_level = logging.INFO
    else:
        # 開発環境: DEBUGレベル、コンソール+ファイル出力
        handlers = [
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("app.log", encoding="utf-8"),
        ]
        log_level = logging.DEBUG

    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)
