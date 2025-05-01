"""
メモリ監視のダミークラス（本来の実装がない場合の暫定対応）
"""

from typing import Dict, Any
from src.utils.config import Config


class MemoryWatcher:
    """
    メモリ監視のダミークラス。本来の機能が必要な場合は実装を追加してください。
    """

    def __init__(self, config: Config) -> None:
        """
        メモリウォッチャーを初期化します。

        Args:
            config: 設定オブジェクト
        """
        self.config = config

    def start(self) -> None:
        """
        メモリ監視を開始します。
        """
        pass

    def stop(self) -> None:
        """
        メモリ監視を停止します。
        """
        pass
