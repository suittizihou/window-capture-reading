"""メッセージ検出機能を提供するモジュール。

OCRで認識されたテキストから新規メッセージを検出します。
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple

class MessageDetector:
    """メッセージ検出クラス。
    
    OCRで認識されたテキストを処理し、新規メッセージのみを検出します。
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """メッセージ検出クラスを初期化します。
        
        Args:
            config: 環境設定の辞書
        """
        self.logger = logging.getLogger(__name__)
        
        # 過去のメッセージを保持するキャッシュ
        self._message_cache: Set[str] = set()
        
        # 最大キャッシュサイズ（設定可能）
        self._max_cache_size = int(config.get("MAX_MESSAGE_CACHE", "10"))
        
        # キャッシュクリーニングのしきい値
        self._cache_clean_threshold = int(config.get("CACHE_CLEAN_THRESHOLD", "12"))
        
        # 最後に検出したテキスト全体
        self._last_text: str = ""
    
    def detect_new_messages(self, text: str) -> List[str]:
        """認識されたテキストから新規メッセージを検出します。
        
        Args:
            text: OCRで認識されたテキスト
            
        Returns:
            List[str]: 検出された新規メッセージのリスト
        """
        if not text:
            return []
        
        # テキストを行に分割し、前処理
        lines = self._preprocess_text(text)
        
        # 新規メッセージを検出
        new_messages = []
        
        for line in lines:
            # 短すぎる行は無視（OCRのノイズである可能性が高い）
            if len(line) < 2:
                continue
            
            # メッセージのハッシュを生成
            normalized_line = self._normalize_message(line)
            
            # キャッシュサイズの確認と必要に応じたクリーニング
            if len(self._message_cache) >= self._max_cache_size:
                self._clean_cache()
            
            # 新規メッセージの場合はリストに追加し、キャッシュに登録
            if normalized_line not in self._message_cache:
                new_messages.append(line)
                self._message_cache.add(normalized_line)
                self.logger.debug(f"新規メッセージを検出: {line}")
        
        if new_messages:
            self.logger.info(f"{len(new_messages)}件の新規メッセージを検出しました")
        
        # 現在のテキストを保存
        self._last_text = text
        
        return new_messages
    
    def _preprocess_text(self, text: str) -> List[str]:
        """テキストを前処理し、行に分割します。
        
        Args:
            text: 処理するテキスト
            
        Returns:
            List[str]: 前処理された行のリスト
        """
        # 改行で分割
        lines = text.split('\n')
        
        # 空行を除去し、各行をトリミング
        processed_lines = [line.strip() for line in lines if line.strip()]
        
        return processed_lines
    
    def _normalize_message(self, message: str) -> str:
        """メッセージを正規化します。
        
        複数のスペースの削除、大文字小文字の統一など、
        メッセージの内容を正規化して比較しやすくします。
        
        Args:
            message: 正規化するメッセージ
            
        Returns:
            str: 正規化されたメッセージ
        """
        # 空白文字を単一のスペースに置換
        normalized = re.sub(r'\s+', ' ', message)
        
        # トリミング
        normalized = normalized.strip()
        
        return normalized
    
    def _clean_cache(self) -> None:
        """キャッシュをクリーニングします。"""
        if len(self._message_cache) >= self._max_cache_size:
            # 新しいメッセージを優先するため、古いメッセージを削除
            cache_list = list(self._message_cache)
            cache_size = len(cache_list)
            # 必要な削除数を計算（最大サイズの半分を保持）
            remove_count = cache_size // 2
            self._message_cache = set(cache_list[remove_count:])
            self.logger.info(f"メッセージキャッシュをクリーニングしました: {cache_size} → {len(self._message_cache)}")
    
    def reset_cache(self) -> None:
        """メッセージキャッシュをリセットします。"""
        self._message_cache.clear()
        self._last_text = ""
        self.logger.info("メッセージキャッシュをリセットしました")
    
    def get_message_count(self) -> int:
        """現在のキャッシュに保存されているメッセージの数を返します。
        
        Returns:
            int: キャッシュされているメッセージの数
        """
        return len(self._message_cache)