"""OCRServiceクラスのテストモジュール。"""

import unittest
import numpy as np
import cv2
from unittest.mock import patch, MagicMock
from src.services.ocr_service import OCRService

class TestOCRService(unittest.TestCase):
    """OCRServiceクラスのテストケース。"""
    
    def setUp(self):
        """各テストケース実行前の準備。"""
        self.config = {
            "TESSERACT_PATH": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            "OCR_LANGUAGE": "jpn",
            "OCR_CONFIG": "--psm 6",
            "OCR_PREPROCESSING_ENABLED": "True"
        }
        self.ocr = OCRService(self.config)
    
    @patch('pytesseract.image_to_string')
    def test_extract_text_success(self, mock_image_to_string):
        """テキスト抽出の成功ケースをテスト。"""
        # モックの設定
        expected_text = "テストテキスト"
        mock_image_to_string.return_value = expected_text
        
        # テスト用画像の作成
        test_image = np.zeros((100, 300, 3), dtype=np.uint8)
        cv2.putText(test_image, "Test", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # テキスト抽出
        result = self.ocr.extract_text(test_image)
        
        # 結果の確認
        self.assertEqual(result, expected_text)
        mock_image_to_string.assert_called_once()
    
    @patch('pytesseract.image_to_string')
    def test_extract_text_empty(self, mock_image_to_string):
        """空のテキスト抽出をテスト。"""
        # モックの設定
        mock_image_to_string.return_value = ""
        
        # テスト用画像の作成
        test_image = np.zeros((100, 300, 3), dtype=np.uint8)
        
        # テキスト抽出
        result = self.ocr.extract_text(test_image)
        
        # 結果の確認
        self.assertIsNone(result)
    
    @patch('pytesseract.image_to_string')
    def test_extract_text_error(self, mock_image_to_string):
        """テキスト抽出エラーのテスト。"""
        # モックの設定
        mock_image_to_string.side_effect = Exception("OCRエラー")
        
        # テスト用画像の作成
        test_image = np.zeros((100, 300, 3), dtype=np.uint8)
        
        # テキスト抽出
        result = self.ocr.extract_text(test_image)
        
        # 結果の確認
        self.assertIsNone(result)
    
    def test_preprocess_image(self):
        """画像前処理のテスト。"""
        # テスト用画像の作成
        test_image = np.zeros((100, 300, 3), dtype=np.uint8)
        cv2.putText(test_image, "Test", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # 前処理実行
        processed = self.ocr._preprocess_image(test_image)
        
        # 結果の確認
        self.assertIsInstance(processed, np.ndarray)
        self.assertEqual(len(processed.shape), 2)  # グレースケール画像であることを確認
        self.assertEqual(processed.dtype, np.uint8)
    
    def test_preprocess_image_error(self):
        """画像前処理エラーのテスト。"""
        # 不正な画像データ
        invalid_image = np.zeros((100, 300), dtype=np.uint8)  # BGRではない
        
        # 前処理実行
        result = self.ocr._preprocess_image(invalid_image)
        
        # エラー時は元の画像が返されることを確認
        self.assertTrue(np.array_equal(result, invalid_image))
    
    @patch('pytesseract.image_to_string')
    def test_ocr_test_success(self, mock_image_to_string):
        """OCRテスト機能の成功ケースをテスト。"""
        # モックの設定
        mock_image_to_string.return_value = "Test OCR"
        
        # テスト実行
        result = self.ocr.test_ocr()
        
        # 結果の確認
        self.assertTrue(result)
        mock_image_to_string.assert_called_once()
    
    @patch('pytesseract.image_to_string')
    def test_ocr_test_failure(self, mock_image_to_string):
        """OCRテスト機能の失敗ケースをテスト。"""
        # モックの設定
        mock_image_to_string.return_value = "Invalid result"
        
        # テスト実行
        result = self.ocr.test_ocr()
        
        # 結果の確認
        self.assertFalse(result)
        mock_image_to_string.assert_called_once()

if __name__ == '__main__':
    unittest.main()