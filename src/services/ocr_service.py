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
from src.utils.messages import MessageManager
from src.utils.performance import PerformanceMonitor, Cache

# シングルトンインスタンスの取得
message_manager = MessageManager()
performance_monitor = PerformanceMonitor()
cache = Cache()

class OCRService:
    """OCRテキスト認識サービスクラス。
    
    Tesseract OCRを使用して画像からテキストを抽出する機能を提供します。
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """OCRサービスクラスを初期化します。
        
        Args:
            config: 基本設定の辞書
        """
        self.logger = logging.getLogger(__name__)
        
        # Tesseractの設定
        tesseract_path = config.get("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            self.tesseract_path = tesseract_path
            self._tesseract_available = True
        else:
            self.logger.warning(message_manager.get("tesseract_not_found", path=tesseract_path))
            self._tesseract_available = False
        
        # OCR設定
        self.lang = config.get("OCR_LANGUAGE", "jpn")
        self.config = config.get("OCR_CONFIG", "--psm 6")  # デフォルトは単一の統一なテキストブロックを想定
        
        # 前処理設定
        self.preprocessing_enabled = config.get("OCR_PREPROCESSING_ENABLED", "True").lower() == "true"
    
    @performance_monitor.measure_time("extract_text")
    def extract_text(self, image: np.ndarray) -> Optional[str]:
        """画像からテキストを抽出します。
        
        Args:
            image: OpenCV形式の画像データ（numpy.ndarray）
            
        Returns:
            Optional[str]: 抽出されたテキスト。失敗した場合はNone
        """
        try:
            # キャッシュチェック
            image_hash = hash(image.tobytes())
            cached_result = cache.get(str(image_hash))
            if cached_result is not None:
                self.logger.debug("キャッシュからテキストを取得しました")
                return cached_result
            
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
                text = text.strip()
                self.logger.debug(message_manager.get("ocr_success", length=len(text)))
                # 結果をキャッシュ
                cache.set(str(image_hash), text)
                return text
            else:
                self.logger.debug(message_manager.get("ocr_empty"))
                return None
            
        except Exception as e:
            self.logger.error(message_manager.get("ocr_error", error=str(e)), exc_info=True)
            return None
    
    @performance_monitor.measure_time("preprocess_image")
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
            self.logger.error(message_manager.get("preprocessing_error", error=str(e)), exc_info=True)
            return image  # エラー時は元の画像を返す
    
    @performance_monitor.measure_time("test_ocr")
    def test_ocr(self) -> bool:
        """OCRエンジンの動作をテストします。
        
        Returns:
            bool: テストが成功したかどうか
        """
        if not self._tesseract_available:
            self.logger.warning(message_manager.get("tesseract_not_found", path=self.tesseract_path))
            return False
            
        try:
            # テスト用の単純な画像を生成（白背景に黒文字）
            test_image = np.full((100, 300, 3), 255, dtype=np.uint8)
            cv2.putText(
                test_image,
                "Test OCR",
                (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 0),  # 黒色
                2
            )
            
            # OCR実行
            result = self.extract_text(test_image)
            
            if result and "test" in result.lower():
                self.logger.info(message_manager.get("test_success"))
                return True
            else:
                self.logger.warning(message_manager.get("test_failure"))
                return False
                
        except Exception as e:
            self.logger.error(message_manager.get("ocr_error", error=str(e)), exc_info=True)
            return False