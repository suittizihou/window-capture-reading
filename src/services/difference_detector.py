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
from skimage.metrics import structural_similarity

from src.utils.config import Config

# 画像処理関連の型定義
# OpenCVの画像型として、複数の型が許容されるようUnion型で定義
ImageArray = Union[NDArray[np.uint8], NDArray[Any]]


class DiffResult(NamedTuple):
    """差分検出結果を表す型。"""

    has_difference: bool
    diff_image: ImageArray
    score: float


class DifferenceDetector:
    """画面の差分を検知するクラス。"""

    def __init__(
        self,
        threshold: float = 0.05,
        diff_method: str = "ssim",
    ) -> None:
        """DifferenceDetectorを初期化します。

        Args:
            threshold: 差分検出の閾値
            diff_method: 差分検出方法（"ssim"または"absdiff"）
        """
        self.logger = logging.getLogger(__name__)

        # 設定を保存
        self.threshold = threshold
        self.diff_method = diff_method
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

            # グレースケール画像を正しい型にキャスト
            gray1 = cast(ImageArray, gray1)
            gray2 = cast(ImageArray, gray2)

            # 検出方法に応じて処理を分岐
            if self.diff_method.lower() == "ssim":
                return self._detect_with_ssim(prev_image, current_image, gray1, gray2)
            else:
                return self._detect_with_absdiff(
                    prev_image, current_image, gray1, gray2
                )

        except Exception as e:
            self.logger.error(f"差分検出エラー: {e}", exc_info=True)
            # エラーの場合は差分なしとする
            empty_image = np.zeros_like(current_image)
            return DiffResult(has_difference=False, diff_image=empty_image, score=1.0)

    def _detect_with_ssim(
        self, img1: ImageArray, img2: ImageArray, gray1: ImageArray, gray2: ImageArray
    ) -> DiffResult:
        """SSIMによる差分検出。

        Args:
            img1: 比較する画像1
            img2: 比較する画像2
            gray1: グレースケール画像1
            gray2: グレースケール画像2

        Returns:
            差分検出結果
        """
        try:
            # SSIMスコアを計算（1.0が完全一致、0.0が完全不一致）
            ssim_score, diff = structural_similarity(
                gray1, gray2, full=True, data_range=255
            )

            # スコアを保存
            score = ssim_score

            # 閾値判定
            has_diff = score < (1.0 - self.threshold)

            # 差分画像を生成
            diff_image = self._create_diff_with_ssim(img1, img2, gray1, gray2, diff)

            return DiffResult(
                has_difference=has_diff,
                diff_image=diff_image,
                score=score,
            )

        except Exception as e:
            self.logger.error(f"SSIM差分検出中にエラー: {e}", exc_info=True)
            # エラーの場合は絶対差分法を使用
            return self._detect_with_absdiff(img1, img2, gray1, gray2)

    def _detect_with_absdiff(
        self, img1: ImageArray, img2: ImageArray, gray1: ImageArray, gray2: ImageArray
    ) -> DiffResult:
        """絶対差分による差分検出。

        Args:
            img1: 比較する画像1
            img2: 比較する画像2
            gray1: グレースケール画像1
            gray2: グレースケール画像2

        Returns:
            差分検出結果
        """
        # 絶対差分を計算
        diff = cv2.absdiff(gray1, gray2)
        total_pixels = diff.size
        diff_pixels = np.count_nonzero(diff > int(self.threshold * 255))

        # スコアを計算（1.0に近いほど一致）
        score = 1.0 - (diff_pixels / total_pixels)

        # 閾値判定（一定数以上のピクセルが異なれば差分あり）
        has_diff = diff_pixels > 100

        # 差分画像を生成
        diff_image = self._create_diff_with_absdiff(img1, img2, gray1, gray2)

        return DiffResult(
            has_difference=has_diff,
            diff_image=diff_image,
            score=score,
        )

    def _create_diff_with_absdiff(
        self, img1: ImageArray, img2: ImageArray, gray1: ImageArray, gray2: ImageArray
    ) -> ImageArray:
        """絶対差分による差分画像の生成。

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
        _, thresh = cv2.threshold(
            diff, int(self.threshold * 255), 255, cv2.THRESH_BINARY
        )

        # 膨張処理（差分部分を強調）
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(thresh, kernel, iterations=2)  # iterations=2でより強調
        dilated = cast(ImageArray, dilated)  # 型をキャスト

        # 差分画像の作成（常にuint8型を維持）
        result = img2.copy()

        # マスクを3チャンネルに変換してカラー画像にする
        mask_3ch = cv2.cvtColor(dilated, cv2.COLOR_GRAY2BGR)
        mask_3ch = cast(ImageArray, mask_3ch)  # 型をキャスト

        # 赤色でマスク（鮮明な赤色にする）
        red_mask = np.zeros_like(mask_3ch)
        red_mask[:, :, 2] = mask_3ch[:, :, 0]  # 赤チャンネルにマスクを適用
        red_mask = cast(ImageArray, red_mask)  # 型をキャスト

        # 元画像と差分マスクを合成（透明度高め）
        alpha = 0.8  # 値を大きくすると赤色が鮮明になる
        result = cv2.addWeighted(result, 1.0, red_mask, alpha, 0)
        result = cast(ImageArray, result)  # 型をキャスト

        # 差分部分に輪郭線を追加（個別に処理して型を整合させる）
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        # 各輪郭を個別に描画（型の問題を回避）
        for c in contours:
            # タプルでなくリストを使用し、色指定を明示的にfloat型に
            color = [0.0, 0.0, 255.0]  # 赤色
            # シーケンスの色と他の引数で正しく呼び出し
            cv2.drawContours(
                result,  # 描画先の画像
                [c],     # 輪郭のリスト
                0,       # 描画する輪郭のインデックス（0=すべて）
                color,   # 色（BGR）
                2        # 線の太さ
            )  # type: ignore  # OpenCVの型定義の問題を無視

        return result

    def _create_diff_with_ssim(
        self,
        img1: ImageArray,
        img2: ImageArray,
        gray1: ImageArray,
        gray2: ImageArray,
        diff: NDArray[np.float64],
    ) -> ImageArray:
        """SSIMによる差分画像の生成。

        Args:
            img1: 比較する画像1
            img2: 比較する画像2
            gray1: グレースケール画像1
            gray2: グレースケール画像2
            diff: SSIM差分マップ

        Returns:
            差分を可視化した画像
        """
        # SSIM差分マップを[0, 1]から[0, 255]に変換
        diff_map = (1 - diff) * 255
        # numpy float64から明示的にuint8へキャスト
        diff_map = diff_map.astype(np.uint8)

        # 閾値処理（敏感にするために低めの値を使用）
        _, thresh = cv2.threshold(
            diff_map, int(self.threshold * 200), 255, cv2.THRESH_BINARY
        )

        # 膨張処理で少しノイズを除去し、差分部分を強調
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.dilate(thresh, kernel, iterations=1)

        # 輪郭検出
        contours, _ = cv2.findContours(
            thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # 結果画像を作成（常にuint8型を維持）
        result = img2.copy()

        # 差分部分にマスクと輪郭線を描画
        # まず、マスクを作成
        mask = np.zeros_like(thresh)
        
        # 各輪郭を個別に塗りつぶし（型の問題を回避）
        for c in contours:
            # 輪郭内部を塗りつぶす (255は白色)
            cv2.drawContours(
                mask,   # 描画先の画像
                [c],    # 輪郭のリスト
                0,      # 描画する輪郭のインデックス（0=すべて）
                255,    # 色（グレースケールなので整数値）
                -1      # -1は内部塗りつぶし
            )  # type: ignore  # OpenCVの型定義の問題を無視

        # 膨張処理で差分部分を強調
        mask = cv2.dilate(mask, kernel, iterations=2)
        mask = cast(ImageArray, mask)

        # マスクを3チャンネルに変換
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        mask_3ch = cast(ImageArray, mask_3ch)

        # 赤色のマスクを作成
        red_mask = np.zeros_like(mask_3ch)
        red_mask[:, :, 2] = mask_3ch[:, :, 0]  # 赤チャンネルにマスクを適用
        red_mask = cast(ImageArray, red_mask)

        # 元画像と差分マスクを合成（透明度を大きめに）
        alpha = 0.8  # 値を大きくすると赤色が鮮明になる
        result = cv2.addWeighted(result, 1.0, red_mask, alpha, 0)
        result = cast(ImageArray, result)

        # 各輪郭について矩形で囲む（輪郭が小さすぎる場合は無視）
        for c in contours:
            if cv2.contourArea(c) > 50:  # 小さな差分も検出
                (x, y, w, h) = cv2.boundingRect(c)
                # 色指定を正確なシーケンス型で
                cv2.rectangle(
                    result, (x, y), (x + w, y + h), [0.0, 0.0, 255.0], 2
                )  # 太さ2で赤色の枠

        return result

    def _create_diff_image(
        self, img1: ImageArray, img2: ImageArray, gray1: ImageArray, gray2: ImageArray
    ) -> ImageArray:
        """2つの画像から差分画像を生成します。この関数はDifferenceDetectorのdetect関数によって
           _create_diff_with_ssimまたは_create_diff_with_absdiffに置き換えられます。

        Args:
            img1: 比較する画像1
            img2: 比較する画像2
            gray1: グレースケール画像1
            gray2: グレースケール画像2

        Returns:
            差分を可視化した画像
        """
        # 単純な絶対差分を使用
        return self._create_diff_with_absdiff(img1, img2, gray1, gray2)

    def detect_difference(self, frame: ImageArray) -> bool:
        """画像の差分を検出する。

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
