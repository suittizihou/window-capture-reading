"""OCRテキスト認識機能を提供するモジュール。

Tesseract OCRを使用して画像からテキストを抽出します。
"""

import logging
import os
from typing import Dict, Optional
import cv2
import numpy as np
import pytesseract
from PIL import Image

class OCRService:
    """OCRテキスト認識サービスクラス。
    
    Tesseract OCRを使用して画像からテキストを抽出する機能を提供します。
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """OCRサービスクラスを初期化します。
        
        Args:
            config: 環境設定の辞書
        """
        self.logger = logging.getLogger(__name__)
        
        # Tesseractの設定
        tesseract_path = config.get("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            self.logger.warning(f"Tesseractが指定されたパスに見つかりません: {tesseract_path}")
        
        # OCR設定
        self.lang = config.get("OCR_LANGUAGE", "jpn")
        self.config = config.get("OCR_CONFIG", "--psm 6")  # デフォルトは単一の均一なテキストブロックを想定
        
        # 前処理設定
        self.preprocessing_enabled = config.get("OCR_PREPROCESSING_ENABLED", "True").lower() == "true"
    
    def extract_text(self, image: np.ndarray) -> Optional[str]:
        """画像からテキストを抽出します。
        
        Args:
            image: OpenCV形式の画像データ（numpy.ndarray）
            
        Returns:
            Optional[str]: 抽出されたテキスト。失敗した場合はNone
        """
        try:
            # 画像の前処理
            if self.preprocessing_enabled:
                processed_image = self._preprocess_image(image)
            else:
                processed_image = image
            
            # OpenCV形式からPIL形式に変換
            pil_image = Image.fromarray(cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB))
            
            # OCR実行
            text = pytesseract.image_to_string(
                pil_image,
                lang=self.lang,
                config=self.config
            )
            
            if text:
                self.logger.debug(f"テキストを抽出しました: {len(text)}文字")
                return text.strip()
            else:
                self.logger.debug("テキストが検出されませんでした")
                return None
            
        except Exception as e:
            self.logger.error(f"テキスト抽出中にエラーが発生しました: {e}", exc_info=True)
            return None
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """OCRの精度向上のために画像を前処理します。
        
        Args:
            image: 前処理する画像
            
        Returns:
            np.ndarray: 前処理された画像
        """
        try:
            # グレースケール変換
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # ノイズ除去（バイラテラルフィルタ）
            denoised = cv2.bilateralFilter(gray, 9, 75, 75)
            
            # コントラスト調整
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            
            # 二値化（適応的閾値処理）
            binary = cv2.adaptiveThreshold(
                enhanced,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2
            )
            
            return binary
            
        except Exception as e:
            self.logger.error(f"画像の前処理中にエラーが発生しました: {e}", exc_info=True)
            return image  # エラー時は元の画像を返す
    
    def test_ocr(self) -> bool:
        """OCRエンジンの動作をテストします。
        
        Returns:
            bool: テストが成功したかどうか
        """
        try:
            # テスト用の単純な画像を生成
            test_image = np.zeros((100, 300), dtype=np.uint8)
            cv2.putText(
                test_image,
                "Test OCR",
                (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                255,
                2
            )
            
            # OCR実行
            result = self.extract_text(cv2.cvtColor(test_image, cv2.COLOR_GRAY2BGR))
            
            if result and "test" in result.lower():
                self.logger.info("OCRエンジンのテストに成功しました")
                return True
            else:
                self.logger.warning("OCRエンジンのテストに失敗しました")
                return False
                
        except Exception as e:
            self.logger.error(f"OCRエンジンのテスト中にエラーが発生しました: {e}", exc_info=True)
            return False