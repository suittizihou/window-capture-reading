"""OCRテキスト認識機能を提供するモジュール。

Tesseract OCRを使用して画像からテキストを抽出します。
"""

import logging
import os
import tempfile
import hashlib
import time
import threading
import io
from typing import Dict, Optional, Any, Tuple, Union, List, cast
from pathlib import Path
import cv2
import numpy as np
from numpy.typing import NDArray
import pytesseract  # type: ignore
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont
from src.utils.messages import MessageManager
from src.utils.performance import PerformanceMonitor, Cache
from src.utils.config import Config

# シングルトンインスタンスの取得
message_manager = MessageManager()
performance_monitor = PerformanceMonitor()
cache = Cache()

# 画像処理関連の型定義
ImageArray = NDArray[np.uint8]

class OCRService:
    """OCRテキスト認識サービスクラス。

    Tesseract OCRを使用して画像からテキストを抽出する機能を提供します。
    """

    def __init__(self, config: Config) -> None:
        """OCRServiceを初期化します。

        Args:
            config: 設定オブジェクト
        """
        self.logger = logging.getLogger(__name__)

        # 設定を保存
        self.config = config

        # Tesseractの設定
        tesseract_path = getattr(config, "TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if not os.path.exists(tesseract_path):
            self.logger.error(f"Tesseractが見つかりません: {tesseract_path}")
            raise FileNotFoundError(f"Tesseractが見つかりません: {tesseract_path}")
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

        # OCRの設定
        self.language = getattr(config, "OCR_LANGUAGE", "jpn")
        self.config_str = getattr(config, "OCR_CONFIG", "--psm 6")
        self.preprocessing_enabled = getattr(config, "OCR_PREPROCESSING_ENABLED", True)

        # キャッシュの設定
        self.cache_enabled = getattr(config, "OCR_CACHE_ENABLED", True)
        self.cache_dir = Path(getattr(config, "OCR_CACHE_DIR", "cache"))
        if self.cache_enabled:
            os.makedirs(self.cache_dir, exist_ok=True)

    def recognize_text(self, image: Union[Image.Image, ImageArray]) -> str:
        """画像からテキストを認識します。

        Args:
            image: 認識対象の画像（PIL ImageまたはNumPy配列）

        Returns:
            認識されたテキスト
        """
        try:
            # 画像の前処理
            if isinstance(image, np.ndarray):
                image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

            # キャッシュをチェック
            if self.cache_enabled:
                cache_key = self._generate_cache_key(image)
                cached_text = self._get_from_cache(cache_key)
                if cached_text is not None:
                    return cached_text

            # 画像の前処理
            if self.preprocessing_enabled:
                image = self._preprocess_image(image)

            # OCRを実行
            ocr_result = pytesseract.image_to_string(
                image,
                lang=self.language,
                config=self.config_str
            )
            
            # 戻り値の型が不定でない場合は文字列に変換
            text = str(ocr_result) if ocr_result is not None else ""

            # キャッシュに保存
            if self.cache_enabled:
                self._save_to_cache(cache_key, text)

            return text.strip()

        except Exception as e:
            self.logger.error(f"テキスト認識中にエラー: {e}")
            return ""

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """画像を前処理します。

        Args:
            image: 前処理する画像

        Returns:
            前処理された画像
        """
        try:
            # グレースケールに変換
            image = image.convert("L")

            # NumPy配列に変換
            img_array = np.array(image)

            # ノイズ除去
            img_array = cv2.medianBlur(img_array, 3)

            # 二値化
            _, img_array = cv2.threshold(
                img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            # PIL Imageに戻す
            return Image.fromarray(img_array)

        except Exception as e:
            self.logger.error(f"画像の前処理中にエラー: {e}")
            return image

    def _generate_cache_key(self, image: Image.Image) -> str:
        """画像のキャッシュキーを生成します。

        Args:
            image: キャッシュキーを生成する画像

        Returns:
            キャッシュキー
        """
        try:
            # 画像をバイト列に変換
            with io.BytesIO() as bio:
                image.save(bio, format="PNG")
                img_bytes = bio.getvalue()

            # ハッシュを計算
            return hashlib.md5(img_bytes).hexdigest()

        except Exception as e:
            self.logger.error(f"キャッシュキーの生成中にエラー: {e}")
            return str(time.time())  # フォールバック

    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """キャッシュからテキストを取得します。

        Args:
            cache_key: キャッシュキー

        Returns:
            キャッシュされたテキスト。存在しない場合はNone。
        """
        try:
            cache_file = self.cache_dir / f"{cache_key}.txt"
            if cache_file.exists():
                return cache_file.read_text(encoding="utf-8")
            return None

        except Exception as e:
            self.logger.error(f"キャッシュの読み込み中にエラー: {e}")
            return None

    def _save_to_cache(self, cache_key: str, text: str) -> None:
        """テキストをキャッシュに保存します。

        Args:
            cache_key: キャッシュキー
            text: 保存するテキスト
        """
        try:
            cache_file = self.cache_dir / f"{cache_key}.txt"
            cache_file.write_text(text, encoding="utf-8")

        except Exception as e:
            self.logger.error(f"キャッシュの保存中にエラー: {e}")
