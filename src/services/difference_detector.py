"""画面の差異検出サービス

画面キャプチャから差異を検出し、通知を行います。
"""

import logging
import threading
import time
import hashlib
from typing import Dict, Optional, Tuple, List, Any
import cv2
import numpy as np
from PIL import Image

from src.utils.config import Config


class DifferenceDetector:
    """
    画面の差異を検出するサービスクラス。
    OCRの前処理パラメータを流用した画像処理で連続するキャプチャ画像を比較し、
    変化があった場合に通知します。
    """
    
    def __init__(self, config: Config) -> None:
        """
        差異検出サービスを初期化します。
        
        Args:
            config: 設定オブジェクト
        """
        self.logger = logging.getLogger(__name__)
        
        # OCR用の設定を流用
        self.use_grayscale = config.get("OCR_USE_GRAYSCALE", "true").lower() == "true"
        self.use_blur = config.get("OCR_USE_BLUR", "true").lower() == "true"
        self.use_threshold = config.get("OCR_USE_THRESHOLD", "true").lower() == "true"
        self.blur_kernel = int(config.get("OCR_BLUR_KERNEL", "5"))
        self.threshold_method = config.get("OCR_THRESHOLD_METHOD", "adaptive")
        self.contrast_alpha = float(config.get("OCR_CONTRAST_ALPHA", "1.0"))
        self.contrast_beta = int(config.get("OCR_CONTRAST_BETA", "0"))
        
        # 差分検知用の設定
        self.threshold = float(config.get("DIFF_THRESHOLD", "0.05"))
        self.cooldown_time = float(config.get("DIFF_COOLDOWN", "1.0"))
        self.min_diff_area = int(config.get("DIFF_MIN_AREA", "100"))
        self.diff_method = config.get("DIFF_METHOD", "ssim")
        self.diff_blur_size = int(config.get("DIFF_BLUR_SIZE", "5"))
        
        # 内部状態
        self.previous_frame = None
        self.last_notification_time = 0
        self.is_shutting_down = threading.Event()
        
        # 通知履歴
        self.notification_history: List[Dict[str, Any]] = []
        self.max_history = int(config.get("DIFF_MAX_HISTORY", "10"))
        
        # デバッグモード
        self.debug_mode = config.get("DIFF_DEBUG_MODE", "false").lower() == "true"
        
        self.logger.info("画面差異検出サービスを初期化しました")
        
    def compare_frames(self, current_frame: Any) -> Tuple[bool, Optional[np.ndarray], float]:
        """
        現在のフレームと前回のフレームを比較し、差異を検出します。
        
        Args:
            current_frame: 現在のフレーム（numpy配列またはPIL.Image）
            
        Returns:
            Tuple[bool, Optional[np.ndarray], float]: 
                - 差異の有無
                - 差異を視覚化した画像（デバッグ用、デバッグモードOFFの場合はNone）
                - 差異の程度（0.0-1.0）
        """
        # 終了処理中の場合は早期リターン
        if self.is_shutting_down.is_set():
            return False, None, 0.0
        
        # OCRと同じ前処理を適用
        preprocessed = self._preprocess_image(current_frame)
        
        # 初回は前回のフレームがないので保存して終了
        if self.previous_frame is None:
            self.previous_frame = preprocessed
            return False, None, 0.0
        
        # 画像サイズが違う場合は再スケーリング
        if preprocessed.shape != self.previous_frame.shape:
            self.previous_frame = cv2.resize(self.previous_frame, 
                                            (preprocessed.shape[1], preprocessed.shape[0]))
        
        # 差異検出方法に応じた処理
        diff_score = 0.0
        diff_mask = None
        
        if self.diff_method == "ssim":
            # 構造的類似性（SSIM）による差異検出
            try:
                from skimage.metrics import structural_similarity as ssim
                # 既にグレースケール処理済みかチェック
                gray1 = preprocessed if len(preprocessed.shape) == 2 else cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
                gray2 = self.previous_frame if len(self.previous_frame.shape) == 2 else cv2.cvtColor(self.previous_frame, cv2.COLOR_BGR2GRAY)
                
                # SSIMによる差異検出
                score, diff = ssim(gray1, gray2, full=True)
                diff_score = 1.0 - score  # スコアを反転（高いほど差異が大きい）
                
                # 差異を視覚化
                diff = (diff * 255).astype("uint8")
                _, diff_mask = cv2.threshold(diff, 50, 255, cv2.THRESH_BINARY_INV)
            except ImportError:
                self.logger.warning("scikit-image not found. Falling back to absolute difference method.")
                self.diff_method = "absdiff"
        
        if self.diff_method == "absdiff":
            # 単純な絶対差分による検出
            # 既にグレースケール処理済みかチェック
            if len(preprocessed.shape) == 2 and len(self.previous_frame.shape) == 2:
                diff = cv2.absdiff(preprocessed, self.previous_frame)
                gray_diff = diff
            else:
                diff = cv2.absdiff(preprocessed, self.previous_frame)
                gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY) if len(diff.shape) > 2 else diff
                
            # ぼかし処理を適用
            kernel_size = self.diff_blur_size
            if kernel_size % 2 == 0:  # カーネルサイズは奇数でなければならない
                kernel_size += 1
            blur_diff = cv2.GaussianBlur(gray_diff, (kernel_size, kernel_size), 0)
            
            # しきい値処理が必要な場合のみ適用
            _, diff_mask = cv2.threshold(blur_diff, 20, 255, cv2.THRESH_BINARY)
            
            # 差異の程度を計算
            diff_score = np.sum(diff_mask) / (diff_mask.shape[0] * diff_mask.shape[1] * 255)
        
        # 差異領域の抽出と面積計算
        contours, _ = cv2.findContours(diff_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        significant_diff = False
        
        # 描画用の画像
        diff_visualization = None
        if self.debug_mode:
            # 現在のフレームをnp.ndarrayに変換（PIL.Imageの場合）
            current_np = current_frame
            if isinstance(current_frame, Image.Image):
                current_np = np.array(current_frame)
            
            # 描画用にコピー
            diff_visualization = current_np.copy()
            if len(diff_visualization.shape) == 2:  # グレースケールの場合はRGBに変換
                diff_visualization = cv2.cvtColor(diff_visualization, cv2.COLOR_GRAY2BGR)
        
        # 有意な差異領域をチェック
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_diff_area:
                significant_diff = True
                # デバッグモード時は差異領域を赤い矩形で囲む
                if self.debug_mode and diff_visualization is not None:
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.rectangle(diff_visualization, (x, y), (x+w, y+h), (0, 0, 255), 2)
        
        # 前回のフレームを更新
        self.previous_frame = preprocessed
        
        # 閾値と比較して差異があるかを判定
        has_difference = significant_diff and diff_score > self.threshold
        
        # クールダウン期間中かどうかをチェック
        current_time = time.time()
        if has_difference and (current_time - self.last_notification_time) < self.cooldown_time:
            has_difference = False  # クールダウン中は通知しない
        
        # 差異がある場合は通知時間を更新
        if has_difference:
            self.last_notification_time = current_time
            
            # 履歴に追加
            self.notification_history.append({
                "timestamp": current_time,
                "diff_score": diff_score,
                "areas": [cv2.contourArea(c) for c in contours if cv2.contourArea(c) > self.min_diff_area]
            })
            
            # 履歴が最大数を超えたら古いものを削除
            if len(self.notification_history) > self.max_history:
                self.notification_history.pop(0)
        
        return has_difference, diff_visualization, diff_score
    
    def _preprocess_image(self, image: Any) -> np.ndarray:
        """
        OCRと同じ前処理を適用して差異検出の精度を向上します。
        
        Args:
            image: 前処理する画像（numpy配列またはPIL.Image）
            
        Returns:
            前処理された画像（numpy配列）
        """
        # PIL.Image.Imageからnp.ndarrayに変換
        if isinstance(image, Image.Image):
            image = np.array(image)
            
        # 終了処理中の場合は早期リターン
        if self.is_shutting_down.is_set():
            return image
            
        try:
            # コピーを作成して元の画像を保持
            processed = image.copy()
            
            # グレースケール変換
            if self.use_grayscale and len(processed.shape) > 2:
                processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            
            # コントラスト調整
            if self.contrast_alpha != 1.0 or self.contrast_beta != 0:
                processed = cv2.convertScaleAbs(processed, alpha=self.contrast_alpha, beta=self.contrast_beta)
            
            # ブラー処理
            if self.use_blur:
                kernel_size = self.blur_kernel
                if kernel_size % 2 == 0:  # カーネルサイズは奇数でなければならない
                    kernel_size += 1
                processed = cv2.GaussianBlur(processed, (kernel_size, kernel_size), 0)
            
            # しきい値処理
            if self.use_threshold and len(processed.shape) == 2:  # グレースケール画像のみ
                if self.threshold_method == "adaptive":
                    # 適応的しきい値処理
                    processed = cv2.adaptiveThreshold(
                        processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                        cv2.THRESH_BINARY, 11, 2
                    )
                else:
                    # 単純なしきい値処理
                    _, processed = cv2.threshold(processed, 127, 255, cv2.THRESH_BINARY)
            
            return processed
            
        except Exception as e:
            self.logger.error(f"画像の前処理中にエラーが発生しました: {e}", exc_info=True)
            return image
    
    def reset(self) -> None:
        """
        前回のフレームと状態をリセットします。
        """
        self.previous_frame = None
        self.last_notification_time = 0
        self.notification_history.clear()
    
    def get_notification_history(self) -> List[Dict[str, Any]]:
        """
        通知履歴を取得します。
        
        Returns:
            List[Dict]: 通知履歴のリスト
        """
        return self.notification_history.copy()
    
    def shutdown(self) -> None:
        """
        サービスを終了します。
        """
        self.is_shutting_down.set()
        self.logger.info("差異検出サービスを終了しています...") 