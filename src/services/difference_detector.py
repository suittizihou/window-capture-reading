"""画面の差分を検知するモジュール。

画像の変化を検出し、差分画像を生成します。
"""

import logging
import threading
import time
import numpy as np
import cv2
from PIL import Image
from typing import Tuple, Optional, Dict, Any, List, cast, Union, NamedTuple
from numpy.typing import NDArray

from src.utils.config import Config

# 画像処理関連の型定義
ImageArray = NDArray[np.uint8]

class DiffResult(NamedTuple):
    """差分検出結果を表す型。"""
    has_difference: bool
    diff_image: ImageArray
    score: float
    text_changes: List[str] = []

class DifferenceDetector:
    """画面の差分を検知するクラス。"""

    def __init__(
        self, 
        threshold: float = 0.05, 
        ocr_enabled: bool = True, 
        ocr_language: str = "jpn", 
        ocr_threshold: float = 0.7
    ) -> None:
        """DifferenceDetectorを初期化します。

        Args:
            threshold: 差分検出の閾値
            ocr_enabled: OCR機能を有効にするかどうか
            ocr_language: OCRの言語
            ocr_threshold: OCRの検出閾値
        """
        self.logger = logging.getLogger(__name__)

        # 設定を保存
        self.threshold = threshold
        self.ocr_enabled = ocr_enabled
        self.ocr_language = ocr_language
        self.ocr_threshold = ocr_threshold
        self.cooldown = 1.0
        self.max_history = 10
        self.debug_mode = False

        # 内部状態の初期化
        self.prev_frame: Optional[ImageArray] = None
        self.last_diff_time = 0.0
        self.frame_history: List[ImageArray] = []
        self.is_shutting_down = threading.Event()

    def detect(self, prev_image: ImageArray, current_image: ImageArray) -> DiffResult:
        """2つの画像間の差分を検出します。

        Args:
            prev_image: 前の画像
            current_image: 現在の画像

        Returns:
            差分検出結果
        """
        try:
            # グレースケールに変換
            gray1 = cv2.cvtColor(prev_image, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(current_image, cv2.COLOR_BGR2GRAY)

            # SSIMを計算
            score = self._compute_ssim(cast(NDArray[np.uint8], gray1), cast(NDArray[np.uint8], gray2))
            has_diff = score < (1.0 - self.threshold)

            # 差分画像を生成
            diff_image = self._create_diff_image(
                prev_image, 
                current_image, 
                cast(NDArray[np.uint8], gray1), 
                cast(NDArray[np.uint8], gray2)
            )

            # OCRによるテキスト変更の検出
            text_changes = self._detect_text_changes(prev_image, current_image) if self.ocr_enabled and has_diff else []

            return DiffResult(
                has_difference=has_diff,
                diff_image=diff_image,
                score=score,
                text_changes=text_changes
            )
        except Exception as e:
            self.logger.error(f"差分検出エラー: {e}", exc_info=True)
            # エラーの場合は差分なしとする
            empty_image = np.zeros_like(current_image)
            return DiffResult(has_difference=False, diff_image=empty_image, score=1.0)

    def _create_diff_image(
        self, 
        img1: ImageArray, 
        img2: ImageArray, 
        gray1: ImageArray, 
        gray2: ImageArray
    ) -> ImageArray:
        """2つの画像から差分画像を生成します。

        Args:
            img1: 比較する画像1
            img2: 比較する画像2
            gray1: グレースケール画像1
            gray2: グレースケール画像2

        Returns:
            差分を可視化した画像
        """
        # 絶対差分を計算
        diff = cv2.absdiff(gray1, gray2)
        
        # 閾値処理
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        # 膨張処理（差分部分を強調）
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(thresh, kernel, iterations=2)
        
        # 輪郭を検出
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 差分部分を強調した画像を作成
        result = img2.copy()
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100:  # 小さすぎる差分は無視
                (x, y, w, h) = cv2.boundingRect(contour)
                cv2.rectangle(result, (x, y), (x + w, y + h), (0, 0, 255), 2)
                
        return result

    def _detect_text_changes(self, img1: ImageArray, img2: ImageArray) -> List[str]:
        """2つの画像間のテキスト変更を検出します。

        Args:
            img1: 比較する画像1
            img2: 比較する画像2

        Returns:
            変更されたテキストのリスト
        """
        # OCRが実装されていない場合は空のリストを返す
        return []

    def detect_difference(self, frame: ImageArray) -> bool:
        """画像の差分を検出する。（後方互換性のため残しています）

        Args:
            frame: 比較する画像

        Returns:
            差分が検出された場合はTrue
        """
        if self.is_shutting_down.is_set():
            return False

        # クールダウン中は検出しない
        if time.time() - self.last_diff_time < self.cooldown:
            return False

        # 前回のフレームがない場合は保存して終了
        if self.prev_frame is None:
            self.prev_frame = frame
            return False

        # 差分を検出
        result = self.detect(self.prev_frame, frame)
        has_difference = result.has_difference

        # 差分を検出した場合は履歴を更新
        if has_difference:
            self.last_diff_time = time.time()
            self.frame_history.append(frame)
            if len(self.frame_history) > self.max_history:
                self.frame_history.pop(0)

        # 現在のフレームを保存
        self.prev_frame = frame

        return has_difference

    def _compute_ssim(self, img1: NDArray[np.uint8], img2: NDArray[np.uint8]) -> float:
        """SSIMスコアを計算する。

        Args:
            img1: 比較する画像1
            img2: 比較する画像2

        Returns:
            SSIMスコア
        """
        C1 = (0.01 * 255) ** 2
        C2 = (0.03 * 255) ** 2

        # 画像の統計量を計算
        mu1 = cv2.GaussianBlur(img1, (11, 11), 1.5)
        mu2 = cv2.GaussianBlur(img2, (11, 11), 1.5)
        mu1_sq = mu1 * mu1
        mu2_sq = mu2 * mu2
        mu1_mu2 = mu1 * mu2
        sigma1_sq = cv2.GaussianBlur(img1 * img1, (11, 11), 1.5) - mu1_sq
        sigma2_sq = cv2.GaussianBlur(img2 * img2, (11, 11), 1.5) - mu2_sq
        sigma12 = cv2.GaussianBlur(img1 * img2, (11, 11), 1.5) - mu1_mu2

        # SSIMを計算
        ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / (
            (mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2)
        )

        return float(ssim_map.mean())

    def shutdown(self) -> None:
        """終了処理を行います。"""
        self.is_shutting_down.set()
        self.logger.info("差分検知モジュールを終了しています")

        # 履歴をクリア
        self.frame_history.clear()
        self.prev_frame = None
