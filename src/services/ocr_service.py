"""OCRテキスト認識機能を提供するモジュール。

Tesseract OCRを使用して画像からテキストを抽出します。
"""

import logging
import os
import tempfile
import hashlib
import time
import threading
from typing import Dict, Optional, Any, Tuple
from pathlib import Path
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont
from src.utils.messages import MessageManager
from src.utils.performance import PerformanceMonitor, Cache
from src.utils.config import Config

# シングルトンインスタンスの取得
message_manager = MessageManager()
performance_monitor = PerformanceMonitor()
cache = Cache()

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
        
        # Tesseractの設定
        self.tesseract_path = config.get("TESSERACT_PATH", r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
        self.tesseract_lang = config.get("TESSERACT_LANG", "jpn")
        self.tesseract_config = config.get("TESSERACT_CONFIG", "--psm 6")
        
        # Tesseractパスの設定
        if os.path.exists(self.tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
        else:
            self.logger.warning(f"指定されたTesseractのパスが見つかりません: {self.tesseract_path}")
            self.logger.warning("PATHからTesseractを探します。環境変数にTesseractのパスが設定されていることを確認してください。")
        
        # プリプロセスの設定
        self.use_grayscale = config.get("OCR_USE_GRAYSCALE", "true").lower() == "true"
        self.use_blur = config.get("OCR_USE_BLUR", "true").lower() == "true"
        self.use_threshold = config.get("OCR_USE_THRESHOLD", "true").lower() == "true"
        self.blur_kernel = int(config.get("OCR_BLUR_KERNEL", "5"))
        self.threshold_method = config.get("OCR_THRESHOLD_METHOD", "adaptive")
        self.contrast_alpha = float(config.get("OCR_CONTRAST_ALPHA", "1.0"))
        self.contrast_beta = int(config.get("OCR_CONTRAST_BETA", "0"))
        
        # キャッシュの設定
        self.use_cache = config.get("OCR_USE_CACHE", "true").lower() == "true"
        self.cache: Dict[str, Tuple[str, float]] = {}
        self.cache_ttl = float(config.get("OCR_CACHE_TTL", "5.0"))  # キャッシュのTTL（秒）
        
        # 終了フラグ（スレッドセーフ）
        self.is_shutting_down = threading.Event()
        
        # テスト実行（オプション）
        test_on_init = config.get("OCR_TEST_ON_INIT", "false").lower() == "true"
        if test_on_init:
            self.test_ocr()
    
    def extract_text(self, image: np.ndarray) -> Optional[str]:
        """画像からテキストを抽出します。
        
        Args:
            image: テキストを抽出する画像（OpenCV形式のnumpy.ndarrayまたはPIL.Image.Image）
            
        Returns:
            抽出されたテキスト、または抽出に失敗した場合はNone
        """
        # 終了処理中の場合は早期リターン
        if self.is_shutting_down.is_set():
            self.logger.debug("終了処理中のためOCR処理をスキップします")
            return None
        
        # PIL.Image.Image型ならnp.ndarrayに変換
        if isinstance(image, Image.Image):
            image = np.array(image)
            
        try:
            # 処理途中で終了されたかどうかを頻繁にチェック
            
            # キャッシュのチェック
            if self.use_cache:
                # 終了フラグの再チェック
                if self.is_shutting_down.is_set():
                    return None
                    
                # 画像のハッシュを作成
                img_hash = hashlib.md5(image.tobytes()).hexdigest()
                
                # キャッシュからテキストを取得（存在する場合）
                if img_hash in self.cache:
                    cached_text, timestamp = self.cache[img_hash]
                    
                    # キャッシュが期限内かチェック
                    if time.time() - timestamp <= self.cache_ttl:
                        self.logger.debug("キャッシュからテキストを取得しました")
                        return cached_text
                    else:
                        # 期限切れのキャッシュを削除
                        del self.cache[img_hash]
            
            # 終了フラグの再チェック
            if self.is_shutting_down.is_set():
                self.logger.debug("前処理前の終了処理中のためOCR処理をスキップします")
                return None
                
            # 画像の前処理
            processed_image = self._preprocess_image(image)
            
            # 終了処理中の場合は早期リターン
            if self.is_shutting_down.is_set():
                self.logger.debug("前処理後の終了処理中のためOCR処理をスキップします")
                return None
            
            # OCR処理
            # OCR処理は時間がかかるため、ここで終了フラグを再度チェック
            if self.is_shutting_down.is_set():
                self.logger.debug("OCR処理直前の終了処理中のためスキップします")
                return None
                
            text = pytesseract.image_to_string(
                processed_image,
                lang=self.tesseract_lang,
                config=self.tesseract_config
            )
            
            # 終了フラグの再チェック
            if self.is_shutting_down.is_set():
                self.logger.debug("OCR処理後の終了処理中のためテキスト処理をスキップします")
                return None
                
            # 結果の処理
            if text:
                # 新しい行だけをスペースに置換
                text = text.replace('\n', ' ').strip()
                
                # キャッシュに追加
                if self.use_cache and not self.is_shutting_down.is_set():
                    self.cache[img_hash] = (text, time.time())
                
                return text
            
            return None
        
        except Exception as e:
            # 終了処理中にエラーが発生した場合はログレベルを下げる
            if self.is_shutting_down.is_set():
                self.logger.debug(f"終了処理中にテキスト抽出のエラーが発生しました: {e}")
            else:
                self.logger.error(f"テキスト抽出中にエラーが発生しました: {e}", exc_info=True)
            return None
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """OCR精度向上のために画像を前処理します。
        
        Args:
            image: 前処理する画像
            
        Returns:
            前処理された画像
        """
        # 終了処理中の場合は早期リターン
        if self.is_shutting_down.is_set():
            return image
            
        try:
            # コピーを作成して元の画像を保持
            processed = image.copy()
            
            # 終了フラグをチェック
            if self.is_shutting_down.is_set():
                return image
                
            # グレースケール変換
            if self.use_grayscale and len(processed.shape) > 2:
                processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            
            # 終了フラグをチェック
            if self.is_shutting_down.is_set():
                return processed
                
            # コントラスト調整
            if self.contrast_alpha != 1.0 or self.contrast_beta != 0:
                processed = cv2.convertScaleAbs(processed, alpha=self.contrast_alpha, beta=self.contrast_beta)
            
            # 終了フラグをチェック
            if self.is_shutting_down.is_set():
                return processed
                
            # ノイズ除去（ぼかし）
            if self.use_blur and self.blur_kernel > 0:
                processed = cv2.GaussianBlur(processed, (self.blur_kernel, self.blur_kernel), 0)
            
            # 終了フラグをチェック
            if self.is_shutting_down.is_set():
                return processed
                
            # 二値化処理
            if self.use_threshold:
                if self.threshold_method == "adaptive":
                    # 適応的しきい値処理
                    processed = cv2.adaptiveThreshold(
                        processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
                    )
                elif self.threshold_method == "otsu" and len(processed.shape) == 2:
                    # 大津の二値化（グレースケール画像のみ）
                    _, processed = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                else:
                    # 単純な二値化
                    _, processed = cv2.threshold(processed, 127, 255, cv2.THRESH_BINARY)
            
            return processed
            
        except Exception as e:
            if self.is_shutting_down.is_set():
                self.logger.debug(f"終了処理中に前処理でエラーが発生しました: {e}")
            else:
                self.logger.error(f"画像の前処理中にエラーが発生しました: {e}", exc_info=True)
            # エラーが発生した場合、必ず元の画像を返す
            return image
    
    def test_ocr(self) -> bool:
        """OCRエンジンの機能をテストします。
        
        Returns:
            テストが成功した場合はTrue、失敗した場合はFalse
        """
        # 終了処理中の場合は早期リターン
        if self.is_shutting_down.is_set():
            self.logger.warning("終了処理中のためOCRテストをスキップします")
            return False
            
        try:
            self.logger.info("OCRエンジンのテストを実行しています...")
            
            # テスト用の簡単な画像を生成
            width, height = 200, 50
            image = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(image)
            
            # 終了フラグをチェック
            if self.is_shutting_down.is_set():
                self.logger.warning("テスト画像生成後に終了フラグが設定されたためテストを中断します")
                return False
                
            # フォントの設定（デフォルトフォント）
            try:
                font_path = str(Path(__file__).parent.parent.parent / "resources" / "fonts" / "meiryo.ttc")
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, 24)
                else:
                    # デフォルトフォントを使用
                    font = ImageFont.load_default()
            except Exception as e:
                self.logger.warning(f"フォント読み込みエラー: {e}")
                font = ImageFont.load_default()
            
            # 終了フラグをチェック
            if self.is_shutting_down.is_set():
                self.logger.warning("フォント設定後に終了フラグが設定されたためテストを中断します")
                return False
                
            # テキストを描画
            test_text = "テストABC123"
            draw.text((10, 10), test_text, fill='black', font=font)
            
            # PIL ImageをOpenCV形式に変換
            image_cv = np.array(image)
            
            # 終了フラグをチェック
            if self.is_shutting_down.is_set():
                self.logger.warning("画像変換後に終了フラグが設定されたためテストを中断します")
                return False
                
            # OCRでテキストを抽出
            extracted_text = self.extract_text(image_cv)
            
            # 終了フラグをチェック
            if self.is_shutting_down.is_set():
                self.logger.warning("テキスト抽出後に終了フラグが設定されたためテストを中断します")
                return False
                
            if extracted_text:
                self.logger.info(f"OCRテスト結果: '{extracted_text}'")
                
                # テスト文字列がどの程度含まれているかチェック
                test_tokens = set(test_text.lower())
                extracted_tokens = set(extracted_text.lower())
                common_chars = test_tokens.intersection(extracted_tokens)
                
                accuracy = len(common_chars) / len(test_tokens)
                self.logger.info(f"OCR精度: {accuracy:.2f} ({len(common_chars)}/{len(test_tokens)} 文字一致)")
                
                return accuracy > 0.5  # 50%以上の精度を成功と見なす
            else:
                self.logger.warning("OCRテストに失敗しました: テキストが抽出できませんでした")
                return False
                
        except Exception as e:
            if self.is_shutting_down.is_set():
                self.logger.warning(f"終了処理中にOCRテストでエラーが発生しました: {e}")
            else:
                self.logger.error(f"OCRテスト中にエラーが発生しました: {e}", exc_info=True)
            return False
    
    def shutdown(self) -> None:
        """OCRサービスの終了処理を行います。リソースの解放やスレッドの停止などを行います。"""
        try:
            self.logger.info("OCRサービスの終了処理を開始します...")
            
            # 終了フラグを設定（まだ設定されていない場合）
            if not self.is_shutting_down.is_set():
                self.is_shutting_down.set()
                self.logger.debug("OCRサービスの終了フラグを設定しました")
            
            # 少し待機して実行中の処理が終了フラグを検出できるようにする
            time.sleep(0.3)
            
            # キャッシュのクリア
            if hasattr(self, 'cache') and self.cache:
                self.cache.clear()
                self.logger.debug("OCRキャッシュをクリアしました")
            
            # pytesseractのセッションクリーン（一時ファイルの削除）
            temp_dir = tempfile.gettempdir()
            tesseract_temp_pattern = "tess_"
            
            try:
                # 一時ディレクトリ内のTesseract関連ファイルを検索して削除
                for filename in os.listdir(temp_dir):
                    if filename.startswith(tesseract_temp_pattern):
                        file_path = os.path.join(temp_dir, filename)
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                                self.logger.debug(f"一時ファイルを削除しました: {file_path}")
                        except (PermissionError, OSError) as e:
                            self.logger.debug(f"一時ファイルの削除中にエラーが発生しました: {e}")
            except Exception as e:
                self.logger.debug(f"一時ファイルの処理中にエラーが発生しました: {e}")
            
            # メモリリークを防ぐ追加の処理
            import gc
            gc.collect()
            
            # pythonインタープリタに少し時間を与えてリソースを解放
            time.sleep(0.2)
            
            # 終了フラグが確実に設定されていることを再確認
            if not self.is_shutting_down.is_set():
                self.is_shutting_down.set()
                self.logger.warning("終了フラグが正しく設定されていなかったため、再設定しました")
            
            self.logger.info("OCRサービスの終了処理が完了しました")
        except Exception as e:
            # 例外が発生しても終了フラグは必ず設定する
            if not self.is_shutting_down.is_set():
                self.is_shutting_down.set()
            self.logger.error(f"OCRサービスの終了処理中にエラーが発生しました: {e}", exc_info=True)