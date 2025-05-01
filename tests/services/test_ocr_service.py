"""OCRサービスのテストモジュール。"""

import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from numpy.typing import NDArray
from PIL import Image
import cv2
from src.services.ocr_service import OCRService
from src.utils.config import Config

# 画像処理関連の型定義
ImageArray = NDArray[np.uint8]

class TestOCRService(unittest.TestCase):
    """OCRサービスのテストクラス。"""

    def setUp(self) -> None:
        """テストの前準備。"""
        self.config = Config()
        self.ocr = OCRService(self.config)

    def test_recognize_text_with_invalid_input(self) -> None:
        """無効な入力画像でのOCR処理のテスト。"""
        # Noneを入力
        with self.assertRaises(TypeError):
            self.ocr.recognize_text(None)  # type: ignore

    def test_recognize_text_with_empty_image(self) -> None:
        """空の画像でのOCR処理のテスト。"""
        # 空の画像を作成（uint8型で明示的に作成）
        empty_array = np.zeros((100, 100, 3), dtype=np.uint8)
        # ImageArrayとして明示的にキャスト
        empty_image: ImageArray = empty_array
        result = self.ocr.recognize_text(empty_image)
        self.assertEqual(result, "")

    @patch('pytesseract.image_to_string')
    def test_recognize_text_with_mock(self, mock_image_to_string: MagicMock) -> None:
        """モックを使用したOCR処理のテスト。"""
        # モックの戻り値を設定
        expected_text = "テストテキスト"
        mock_image_to_string.return_value = expected_text

        # テスト用の画像を作成（uint8型で明示的に作成）
        # PILイメージとして作成し、OCRServiceが対応する型にする
        pil_image = Image.fromarray(np.ones((100, 100, 3), dtype=np.uint8) * 255)
        
        # OCR処理を実行
        result = self.ocr.recognize_text(pil_image)

        # 結果を検証
        self.assertEqual(result, expected_text)
        mock_image_to_string.assert_called_once()

    def test_preprocess_image(self) -> None:
        """画像の前処理機能のテスト。"""
        # テスト用の画像を作成
        test_image = Image.fromarray(np.ones((100, 100, 3), dtype=np.uint8) * 255)

        # 前処理を実行
        processed_image = self.ocr._preprocess_image(test_image)

        # 結果を検証
        self.assertIsNotNone(processed_image)
        self.assertEqual(processed_image.size, test_image.size)

if __name__ == "__main__":
    unittest.main()
