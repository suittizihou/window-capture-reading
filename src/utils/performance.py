"""パフォーマンス最適化のためのユーティリティモジュール。"""

import time
import logging
from typing import Any, Callable, Dict, Optional, TypeVar
from functools import wraps

T = TypeVar("T")


class PerformanceMonitor:
    """パフォーマンスモニタリングクラス。"""

    def __init__(self):
        """パフォーマンスモニターを初期化します。"""
        self.logger = logging.getLogger(__name__)
        self._metrics: Dict[str, float] = {}

    def measure_time(self, func_name: Optional[str] = None) -> Callable:
        """関数の実行時間を計測するデコレータ。

        Args:
            func_name: 関数の識別名（Noneの場合は関数名を使用）

        Returns:
            Callable: デコレータ関数
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                name = func_name or func.__name__
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.perf_counter()
                    execution_time = end_time - start_time
                    self._metrics[name] = execution_time
                    self.logger.debug(f"実行時間 {name}: {execution_time:.3f}秒")

            return wrapper

        return decorator

    def get_metrics(self) -> Dict[str, float]:
        """計測されたメトリクスを取得します。

        Returns:
            Dict[str, float]: 関数名と実行時間のマッピング
        """
        return self._metrics.copy()

    def clear_metrics(self) -> None:
        """メトリクスをクリアします。"""
        self._metrics.clear()


class Cache:
    """シンプルなメモリキャッシュ実装。"""

    def __init__(self, max_size: int = 100):
        """キャッシュを初期化します。

        Args:
            max_size: キャッシュの最大サイズ
        """
        self._cache: Dict[str, Any] = {}
        self._max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        """キャッシュからデータを取得します。

        Args:
            key: キャッシュキー

        Returns:
            Optional[Any]: キャッシュされた値。存在しない場合はNone
        """
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """データをキャッシュに保存します。

        Args:
            key: キャッシュキー
            value: キャッシュする値
        """
        if len(self._cache) >= self._max_size:
            # 最も古いエントリを削除
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = value

    def clear(self) -> None:
        """キャッシュをクリアします。"""
        self._cache.clear()


# シングルトンインスタンス
performance_monitor = PerformanceMonitor()
cache = Cache()
