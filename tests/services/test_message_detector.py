"""メッセージ検知機能のテストモジュール。"""

import unittest
import numpy as np
from typing import Dict
from src.services.message_detector import MessageDetector

class TestMessageDetector(unittest.TestCase):
    """メッセージ検知機能のテストクラス。"""

    def setUp(self) -> None:
        """テストの前準備。"""
        self.config: Dict[str, str] = {
            "MAX_MESSAGE_CACHE": "10",
            "CACHE_CLEAN_THRESHOLD": "12"
        }
        self.detector = MessageDetector(self.config)

    def test_detect_new_messages_empty(self) -> None:
        """空のテキストでのメッセージ検知のテスト。"""
        # 空のテキストでテスト
        result = self.detector.detect_new_messages("")
        
        # 結果を検証
        self.assertEqual(result, [])

    def test_detect_new_messages_with_text(self) -> None:
        """テキストを含む場合のメッセージ検知のテスト。"""
        # テスト用のテキスト
        test_text = "これはテストメッセージです。"

        # メッセージ検知を実行
        result = self.detector.detect_new_messages(test_text)

        # 結果を検証
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "これはテストメッセージです。")

    def test_detect_duplicate_messages(self) -> None:
        """重複メッセージの検知テスト。"""
        # 同じメッセージを2回送信
        test_text = "これはテストメッセージです。"
        
        # 1回目の検知
        first_result = self.detector.detect_new_messages(test_text)
        # 2回目の検知
        second_result = self.detector.detect_new_messages(test_text)

        # 結果を検証
        self.assertEqual(len(first_result), 1)
        self.assertEqual(len(second_result), 0)

if __name__ == "__main__":
    unittest.main()
