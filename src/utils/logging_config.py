import logging
import sys
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.utils.config import Config


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


def reconfigure_logging(config: "Config") -> None:
    """
    設定に基づいてロギング設定を再構成する。

    Args:
        config: 設定オブジェクト
    """
    # PyInstallerでビルドされているか検出
    is_frozen = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")

    # ログフォーマット
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(log_format)

    # ルートロガーを取得
    root_logger = logging.getLogger()

    # 既存のハンドラをすべて削除
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)

    # ログレベルの設定
    if not is_frozen:
        # 開発環境では常にDEBUGレベル
        log_level = logging.DEBUG
    else:
        # 製品版: enable_verbose_logに基づいて設定
        log_level = logging.DEBUG if config.enable_verbose_log else logging.WARNING

    root_logger.setLevel(log_level)

    # ハンドラの作成
    handlers: List[logging.Handler] = []

    # コンソールハンドラ（開発環境のみ）
    if not is_frozen:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    # ファイルハンドラ（設定で有効な場合のみ）
    if config.enable_log_file:
        file_handler = logging.FileHandler("app.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # ハンドラを追加
    for handler in handlers:
        root_logger.addHandler(handler)
