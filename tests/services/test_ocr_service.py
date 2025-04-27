"""OCRServiceのテストモジュール。"""

import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import cv2
from typing import Dict, Any
from src.services.ocr_service import OCRService

class TestOCRService(unittest.TestCase):
    """OCRServiceのテストクラス。"""
    
    def setUp(self) -> None:
        """テストの前準備。

        環境設定とテスト用画像を初期化します。
        """
        self.config: Dict[str, str] = {
            "TESSERACT_PATH": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            "OCR_LANGUAGE": "jpn",
            "OCR_CONFIG": "--psm 6",
            "OCR_PREPROCESSING_ENABLED": "True"
        }
        self.ocr = OCRService(self.config)
        
        # テスト用画像の作成
        self.test_image = np.zeros((100, 300, 3), dtype=np.uint8)
        cv2.putText(
            self.test_image,
            "Test OCR",
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2
        )
    
    @patch('pytesseract.image_to_string')
    def test_extract_text_success(self, mock_image_to_string: MagicMock) -> None:
        """テキスト抽出の成功ケースをテスト。"""
        # モックの設定
        mock_image_to_string.return_value = "Test OCR"
        
        # テスト実行
        result = self.ocr.extract_text(self.test_image)
        
        # 結果の確認
        self.assertEqual(result, "Test OCR")
        mock_image_to_string.assert_called_once()
    
    @patch('pytesseract.image_to_string')
    def test_extract_text_empty(self, mock_image_to_string: MagicMock) -> None:
        """空のテキスト抽出ケースをテスト。"""
        # モックの設定
        mock_image_to_string.return_value = ""
        
        # テスト実行
        result = self.ocr.extract_text(self.test_image)
        
        # 結果の確認
        self.assertIsNone(result)
        mock_image_to_string.assert_called_once()
    
    @patch('pytesseract.image_to_string')
    def test_extract_text_error(self, mock_image_to_string: MagicMock) -> None:
        """テキスト抽出のエラーケースをテスト。"""
        # モックの設定
        mock_image_to_string.side_effect = Exception("OCR error")
        
        # テスト実行
        result = self.ocr.extract_text(self.test_image)
        
        # 結果の確認
        self.assertIsNone(result)
        mock_image_to_string.assert_called_once()
    
    def test_preprocess_image(self) -> None:
        """画像前処理機能をテスト。"""
        # テスト実行
        result = self.ocr._preprocess_image(self.test_image)
        
        # 結果の確認
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(result.shape[:2], self.test_image.shape[:2])
    
    def test_preprocess_image_error(self) -> None:
        """画像前処理のエラーケースをテスト。"""
        # 無効な画像データ
        invalid_image = np.zeros((100, 300), dtype=np.uint8)  # チャンネル数が不正
        
        # テスト実行
        result = self.ocr._preprocess_image(invalid_image)
        
        # エラー時は元の画像が返されることを確認
        self.assertTrue(np.array_equal(result, invalid_image))
    
    @patch('pytesseract.image_to_string')
    def test_ocr_test_success(self, mock_image_to_string: MagicMock) -> None:
        """OCRテスト機能の成功ケースをテスト。"""
        # モックの設定
        mock_image_to_string.return_value = "Test OCR"
        
        # テスト成功の代替パターン
        # OCRServiceオブジェクトを新たに作り、extract_textメソッドをモックする
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            test_ocr = OCRService(self.config)
            test_ocr._tesseract_available = True
            
            # extract_textのモック
            with patch.object(test_ocr, 'extract_text', return_value="Test OCR"):
                # テスト実行
                result = test_ocr.test_ocr()
                
                # 結果の確認
                self.assertTrue(result)
    
    @patch('pytesseract.image_to_string')
    def test_ocr_test_failure(self, mock_image_to_string: MagicMock) -> None:
        """OCRテスト機能の失敗ケースをテスト。"""
        # モックの設定
        mock_image_to_string.return_value = "Invalid result"
        
        # Tesseractのパスを一時的に変更して利用可能に設定
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            self.ocr = OCRService(self.config)
            self.ocr._tesseract_available = True
            
            # テスト実行
            result = self.ocr.test_ocr()
            
            # 結果の確認
            self.assertFalse(result)
            mock_image_to_string.assert_called_once()
    
    def test_tesseract_not_found(self) -> None:
        """Tesseractが見つからない場合のテストケース。"""
        # 無効なTesseractパスで初期化
        config = self.config.copy()
        config["TESSERACT_PATH"] = r"C:\Invalid\Path\tesseract.exe"
        ocr = OCRService(config)
        
        # テスト実行
        result = ocr.test_ocr()
        
        # 結果の確認
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()