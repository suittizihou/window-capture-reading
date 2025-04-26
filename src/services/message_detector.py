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
        self._max_cache_size = int(config.get("MAX_MESSAGE_CACHE", "1000"))
        
        # キャッシュクリーニングのしきい値
        self._cache_clean_threshold = int(config.get("CACHE_CLEAN_THRESHOLD", "1200"))
        
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
        
        # キャッシュサイズの確認と必要に応じたクリーニング
        self._check_and_clean_cache()
        
        # テキストを行に分割し、前処理
        lines = self._preprocess_text(text)
        
        # 新規メッセージを検出
        new_messages = self._extract_new_messages(lines)
        
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
    
    def _extract_new_messages(self, lines: List[str]) -> List[str]:
        """行リストから新規メッセージを抽出します。
        
        Args:
            lines: テキスト行のリスト
            
        Returns:
            List[str]: 新規メッセージのリスト
        """
        new_messages = []
        
        for line in lines:
            # 短すぎる行は無視（OCRのノイズである可能性が高い）
            if len(line) < 2:
                continue
            
            # メッセージのハッシュを生成
            # 単純な内容比較ではなく、正規化されたハッシュを使用することで
            # 微妙な違いによる重複検出を防止
            normalized_line = self._normalize_message(line)
            
            # 新規メッセージの場合はリストに追加し、キャッシュに登録
            if normalized_line not in self._message_cache:
                new_messages.append(line)
                self._message_cache.add(normalized_line)
                self.logger.debug(f"新規メッセージを検出: {line}")
        
        if new_messages:
            self.logger.info(f"{len(new_messages)}件の新規メッセージを検出しました")
        
        return new_messages
    
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
    
    def _check_and_clean_cache(self) -> None:
        """キャッシュサイズを確認し、必要に応じてクリーニングします。"""
        if len(self._message_cache) >= self._cache_clean_threshold:
            # キャッシュサイズが閾値を超えた場合、最大サイズまで削減
            self.logger.info(f"メッセージキャッシュをクリーニングします: {len(self._message_cache)} → {self._max_cache_size}")
            
            # 新しいメッセージを優先するため、古いメッセージを削除
            # （setには順序がないため、リストに変換して操作）
            cache_list = list(self._message_cache)
            self._message_cache = set(cache_list[-self._max_cache_size:])
    
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