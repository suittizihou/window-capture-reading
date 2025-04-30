"""画面の差分を検知するモジュール。

画像の変化を検出し、差分画像を生成します。
"""

import logging
import numpy as np
import cv2
from PIL import Image
from typing import Tuple, Optional


class DifferenceDetector:
    """画面の差分を検知するクラス。"""
    
    def __init__(self) -> None:
        """DifferenceDetectorを初期化します。"""
        self.logger = logging.getLogger(__name__)
        self.threshold = 30  # 画素値の差分しきい値
        self.min_diff_pixels = 100  # 最小差分ピクセル数
        self.diff_ratio_threshold = 1.0  # 差分率のしきい値（%）
    
    def detect_difference(self, 
                          prev_image: Image.Image, 
                          current_image: Image.Image) -> Tuple[bool, float, Image.Image]:
        """2つの画像間の差分を検出します。
        
        Args:
            prev_image: 前回の画像
            current_image: 現在の画像
            
        Returns:
            差分があったかどうか、差分の割合（%）、差分を可視化した画像のタプル
        """
        try:
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
            
            # 画像の差分を計算
            diff = cv2.absdiff(prev_gray, current_gray)
            _, thresh = cv2.threshold(diff, self.threshold, 255, cv2.THRESH_BINARY)
            
            # 膨張・収縮でノイズを除去
            kernel = np.ones((5, 5), np.uint8)
            dilated = cv2.dilate(thresh, kernel, iterations=1)
            
            # 差分ピクセル数をカウント
            diff_pixels = np.count_nonzero(dilated)
            total_pixels = dilated.size
            diff_ratio = (diff_pixels / total_pixels) * 100
            
            # 差分があるかどうかを判定
            has_diff = diff_pixels > self.min_diff_pixels and diff_ratio > self.diff_ratio_threshold
            
            # 差分画像の作成
            if has_diff:
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
            
        except Exception as e:
            self.logger.error(f"差分検知中にエラーが発生しました: {e}", exc_info=True)
            # エラー時は差分なしと判断し、現在の画像をそのまま返す
            return False, 0.0, current_image
    
    def _pil_to_cv(self, pil_image: Image.Image) -> np.ndarray:
        """PIL ImageをOpenCV形式に変換します。
        
        Args:
            pil_image: 変換するPIL Image
            
        Returns:
            OpenCV形式（numpy.ndarray）の画像
        """
        # PIL ImageがRGBモードでない場合は変換
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # PIL -> Numpy array
        cv_image = np.array(pil_image)
        
        # RGB -> BGR変換（OpenCVはBGRなので）
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
        
        return cv_image 