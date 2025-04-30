"""画面の差分を検知するモジュール。

画像の変化を検出し、差分画像を生成します。
"""

import logging
import threading
import time
import numpy as np
import cv2
from PIL import Image
from typing import Tuple, Optional, Dict, Any, List

from src.utils.config import Config


class DifferenceDetector:
    """画面の差分を検知するクラス。"""

    def __init__(self, config: Config) -> None:
        """DifferenceDetectorを初期化します。

        Args:
            config: 設定オブジェクト
        """
        self.logger = logging.getLogger(__name__)

        # 設定を保存
        self.config = config

        # 設定から値を読み込む
        self.threshold = float(config.get("DIFF_THRESHOLD", "0.05"))
        self.method = config.get("DIFF_METHOD", "ssim")
        self.cooldown = float(config.get("DIFF_COOLDOWN", "1.0"))
        self.max_history = int(config.get("DIFF_MAX_HISTORY", "10"))
        self.debug_mode = config.get("DIFF_DEBUG_MODE", "false").lower() == "true"

        # 前回の比較結果
        self.last_diff_time = 0
        self.history: List[Image.Image] = []

        # 終了フラグ
        self.is_shutting_down = threading.Event()

    def compare_frames(
        self, current_image: Image.Image
    ) -> Tuple[bool, Optional[Image.Image], float]:
        """現在のフレームと過去のフレームを比較し、差分を検出します。

        Args:
            current_image: 現在のフレーム画像

        Returns:
            差分があるかどうか、デバッグ画像（あれば）、差分スコア
        """
        # 終了処理中の場合は早期リターン
        if self.is_shutting_down.is_set():
            return False, None, 0.0

        try:
            # 履歴が空の場合は追加して終了
            if len(self.history) == 0:
                self.history.append(current_image.copy())
                return False, current_image, 0.0

            # 前回の画像を取得
            prev_image = self.history[-1]

            # クールダウン期間中は差分なしとする
            now = time.time()
            if now - self.last_diff_time < self.cooldown:
                return False, current_image, 0.0

            # 終了処理中の場合は早期リターン
            if self.is_shutting_down.is_set():
                return False, None, 0.0

            # 2つの画像間の差分を検出
            has_diff, diff_ratio, result_image = self.detect_difference(
                prev_image, current_image
            )

            # 差分がある場合は履歴に追加
            if has_diff:
                self.last_diff_time = now
                # 履歴が最大数を超えたら古いものを削除
                if len(self.history) >= self.max_history:
                    self.history.pop(0)
                self.history.append(current_image.copy())

            return has_diff, result_image, diff_ratio

        except Exception as e:
            if self.is_shutting_down.is_set():
                self.logger.debug(f"終了処理中に差分検知エラーが発生: {e}")
            else:
                self.logger.error(f"差分検知エラー: {e}", exc_info=True)
            return False, current_image, 0.0

    def detect_difference(
        self, prev_image: Image.Image, current_image: Image.Image
    ) -> Tuple[bool, float, Image.Image]:
        """2つの画像間の差分を検出します。

        Args:
            prev_image: 前回の画像
            current_image: 現在の画像

        Returns:
            差分があったかどうか、差分の割合（%）、差分を可視化した画像のタプル
        """
        try:
            # 終了処理中の場合は早期リターン
            if self.is_shutting_down.is_set():
                return False, 0.0, current_image

            # PIL ImageをOpenCV形式に変換
            prev_cv = self._pil_to_cv(prev_image)
            current_cv = self._pil_to_cv(current_image)

            # サイズが異なる場合はリサイズ
            if prev_cv.shape != current_cv.shape:
                h, w = current_cv.shape[:2]
                prev_cv = cv2.resize(prev_cv, (w, h))

            # グレースケールに変換
            if len(prev_cv.shape) > 2:
                prev_gray = cv2.cvtColor(prev_cv, cv2.COLOR_BGR2GRAY)
                current_gray = cv2.cvtColor(current_cv, cv2.COLOR_BGR2GRAY)
            else:
                prev_gray = prev_cv
                current_gray = current_cv

            # 選択された方法で差分を検出
            if self.method == "ssim":
                # SSIM（構造的類似性）で比較
                return self._detect_with_ssim(prev_gray, current_gray, current_cv)
            else:
                # デフォルトの絶対差分で比較
                return self._detect_with_absdiff(prev_gray, current_gray, current_cv)

        except Exception as e:
            if self.is_shutting_down.is_set():
                self.logger.debug(f"終了処理中に差分検知中にエラー: {e}")
            else:
                self.logger.error(f"差分検知中にエラー: {e}", exc_info=True)
            # エラー時は差分なしと判断し、現在の画像をそのまま返す
            return False, 0.0, current_image

    def _detect_with_absdiff(
        self, prev_gray: np.ndarray, current_gray: np.ndarray, current_cv: np.ndarray
    ) -> Tuple[bool, float, Image.Image]:
        """絶対差分による差分検出を行います。

        Args:
            prev_gray: 前回のグレースケール画像
            current_gray: 現在のグレースケール画像
            current_cv: 現在のカラー画像

        Returns:
            差分があったかどうか、差分の割合（%）、差分を可視化した画像のタプル
        """
        # 画像の差分を計算
        diff = cv2.absdiff(prev_gray, current_gray)
        _, thresh = cv2.threshold(
            diff, int(self.threshold * 255), 255, cv2.THRESH_BINARY
        )

        # 膨張・収縮でノイズを除去
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(thresh, kernel, iterations=1)

        # 差分ピクセル数をカウント
        diff_pixels = np.count_nonzero(dilated)
        total_pixels = dilated.size
        diff_ratio = (diff_pixels / total_pixels) * 100

        # 最小面積（100ピクセル）を超える場合は差分あり
        has_diff = diff_pixels > 100

        # 差分画像の作成
        if has_diff or self.debug_mode:
            # カラー画像に戻して赤色でマーク
            result = current_cv.copy()

            # マスクを3チャンネルに変換してカラー画像にする
            mask_3ch = cv2.cvtColor(dilated, cv2.COLOR_GRAY2BGR)
            # 赤色でマスク
            red_mask = np.zeros_like(mask_3ch)
            red_mask[:, :, 2] = mask_3ch[:, :, 0]  # 赤チャンネルにマスクを適用

            # 元画像と差分マスクを合成（半透明）
            alpha = 0.5
            result = cv2.addWeighted(result, 1.0, red_mask, alpha, 0)

            # OpenCV BGR -> PIL RGB
            result_pil = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        else:
            # 差分がない場合は現在の画像をそのまま返す
            result_pil = Image.fromarray(cv2.cvtColor(current_cv, cv2.COLOR_BGR2RGB))

        return has_diff, diff_ratio, result_pil

    def _detect_with_ssim(
        self, prev_gray: np.ndarray, current_gray: np.ndarray, current_cv: np.ndarray
    ) -> Tuple[bool, float, Image.Image]:
        """SSIM（構造的類似性）による差分検出を行います。

        Args:
            prev_gray: 前回のグレースケール画像
            current_gray: 現在のグレースケール画像
            current_cv: 現在のカラー画像

        Returns:
            差分があったかどうか、差分の割合（%）、差分を可視化した画像のタプル
        """
        try:
            # skimage.metricsからSSIMをインポート
            from skimage.metrics import structural_similarity

            # SSIMスコアを計算（1.0が完全一致、0.0が完全不一致）
            ssim_score, diff = structural_similarity(
                prev_gray, current_gray, full=True, data_range=255
            )

            # SSIM差分マップを[0, 1]から[0, 255]に変換
            diff = (1 - diff) * 255
            diff = diff.astype(np.uint8)

            # 閾値処理
            _, thresh = cv2.threshold(
                diff, int(self.threshold * 255), 255, cv2.THRESH_BINARY
            )

            # 輪郭検出
            contours, _ = cv2.findContours(
                thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            # 差分領域の面積をチェック
            total_area = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                total_area += area

            # 全体に対する割合を計算
            total_pixels = prev_gray.size
            diff_ratio = (total_area / total_pixels) * 100

            # 最小面積（100ピクセル）を超える場合は差分あり
            has_diff = total_area > 100

            # デバッグモードまたは差分がある場合は視覚化
            if has_diff or self.debug_mode:
                # 結果画像を作成
                result = current_cv.copy()

                # 差分領域を赤色で描画
                cv2.drawContours(result, contours, -1, (0, 0, 255), 2)

                # 各輪郭について矩形で囲む
                for c in contours:
                    if cv2.contourArea(c) > 100:  # 一定サイズ以上の輪郭のみ
                        (x, y, w, h) = cv2.boundingRect(c)
                        cv2.rectangle(result, (x, y), (x + w, y + h), (0, 0, 255), 2)

                # OpenCV BGR -> PIL RGB
                result_pil = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
            else:
                # 差分がない場合は現在の画像をそのまま返す
                result_pil = Image.fromarray(
                    cv2.cvtColor(current_cv, cv2.COLOR_BGR2RGB)
                )

            return has_diff, diff_ratio, result_pil

        except Exception as e:
            self.logger.error(f"SSIM差分検出中にエラー: {e}", exc_info=True)
            # エラー時は絶対差分法を使用
            return self._detect_with_absdiff(prev_gray, current_gray, current_cv)

    def _pil_to_cv(self, pil_image: Image.Image) -> np.ndarray:
        """PIL画像をOpenCV形式に変換します。

        Args:
            pil_image: PIL画像

        Returns:
            OpenCV形式の画像（BGR）
        """
        # PIL画像をRGBに変換
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        # PIL -> NumPy配列（RGB）
        np_image = np.array(pil_image)

        # RGB -> BGR（OpenCVの形式）
        cv_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)

        return cv_image

    def shutdown(self) -> None:
        """終了処理を行います。"""
        self.is_shutting_down.set()
        self.logger.info("差分検知モジュールを終了しています")

        # 履歴をクリア
        self.history.clear()
