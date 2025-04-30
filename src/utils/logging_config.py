import logging
import sys


def setup_logging() -> None:
    """
    アプリケーション全体のロギング設定を行う。
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
