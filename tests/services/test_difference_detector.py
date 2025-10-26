"""差分検知機能のテストモジュール。

画像の差分検知ロジックをテストします。実際のウィンドウキャプチャは行わず、
ダミー画像を使用してテストします。
"""

import pytest
import numpy as np
import time
from typing import cast
from numpy.typing import NDArray

from src.services.difference_detector import (
    DifferenceDetector,
    DiffResult,
    ImageArray,
)


def create_dummy_image(
    width: int = 100, height: int = 100, color: tuple = (255, 255, 255)
) -> ImageArray:
    """テスト用のダミー画像を生成します。

    Args:
        width: 画像の幅
        height: 画像の高さ
        color: BGR色（デフォルトは白）

    Returns:
        生成された画像
    """
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:, :] = color
    return cast(ImageArray, image)


def create_image_with_rect(
    width: int = 100,
    height: int = 100,
    rect_pos: tuple = (20, 20),
    rect_size: tuple = (30, 30),
    bg_color: tuple = (255, 255, 255),
    rect_color: tuple = (0, 0, 255),
) -> ImageArray:
    """矩形を含むテスト用画像を生成します。

    Args:
        width: 画像の幅
        height: 画像の高さ
        rect_pos: 矩形の左上位置 (x, y)
        rect_size: 矩形のサイズ (width, height)
        bg_color: 背景色（BGR）
        rect_color: 矩形の色（BGR）

    Returns:
        生成された画像
    """
    image = create_dummy_image(width, height, bg_color)
    x, y = rect_pos
    w, h = rect_size
    image[y : y + h, x : x + w] = rect_color
    return image


class TestDifferenceDetectorInit:
    """DifferenceDetectorの初期化テスト"""

    def test_init_default_values(self) -> None:
        """デフォルト値での初期化をテスト"""
        detector = DifferenceDetector()

        assert detector.threshold == 0.05
        assert detector.diff_method == "ssim"
        assert detector.cooldown == 1.0
        assert detector.max_history == 10
        assert detector.prev_frame is None
        assert len(detector.frame_history) == 0

    def test_init_custom_values(self) -> None:
        """カスタム値での初期化をテスト"""
        detector = DifferenceDetector(threshold=0.1, diff_method="absdiff")

        assert detector.threshold == 0.1
        assert detector.diff_method == "absdiff"


class TestDifferenceDetectorSSIM:
    """SSIMメソッドによる差分検知テスト"""

    def test_detect_no_difference(self) -> None:
        """同一画像で差分なしを検出"""
        detector = DifferenceDetector(threshold=0.05, diff_method="ssim")

        # グラデーション画像を使用（SSIMが正しく計算できるように構造を持たせる）
        img1 = np.tile(np.arange(0, 256, 256 // 100, dtype=np.uint8), (100, 1))
        img1 = np.stack([img1, img1, img1], axis=-1)
        img2 = img1.copy()

        result = detector.detect(img1, img2)

        assert isinstance(result, DiffResult)
        assert not result.has_difference  # 差分なし
        assert result.score > 0.99  # 同一画像なのでスコアは非常に高い
        assert result.diff_image.shape == img1.shape

    def test_detect_with_difference(self) -> None:
        """異なる画像で差分ありを検出"""
        detector = DifferenceDetector(threshold=0.05, diff_method="ssim")

        # 構造のある画像を作成
        img1 = np.tile(np.arange(0, 256, 256 // 100, dtype=np.uint8), (100, 1))
        img1 = np.stack([img1, img1, img1], axis=-1)
        # 異なる画像（大きめの矩形で明確な差分を作る）
        img2 = img1.copy()
        img2[10:60, 10:60] = [0, 0, 0]  # 大きな黒い矩形

        result = detector.detect(img1, img2)

        assert isinstance(result, DiffResult)
        assert result.has_difference  # 差分あり
        assert result.score < 0.95  # 差分があるのでスコアは低い
        assert result.diff_image.shape == img1.shape

    def test_detect_threshold_sensitivity(self) -> None:
        """閾値による検知感度のテスト"""
        # 高感度（閾値が低い）
        detector_high = DifferenceDetector(threshold=0.01, diff_method="ssim")

        # 構造のある画像とわずかに異なる画像を作成
        img1 = np.tile(np.arange(0, 256, 256 // 100, dtype=np.uint8), (100, 1))
        img1 = np.stack([img1, img1, img1], axis=-1)
        img2 = img1.copy()
        img2[45:55, 45:55] = [200, 200, 200]  # 小さな変化

        result_high = detector_high.detect(img1, img2)

        # 高感度の場合、小さな差分も検出できる
        assert result_high.has_difference  # 差分を検出


class TestDifferenceDetectorAbsDiff:
    """絶対差分メソッドによる差分検知テスト"""

    def test_detect_no_difference_absdiff(self) -> None:
        """同一画像で差分なしを検出（絶対差分）"""
        detector = DifferenceDetector(threshold=0.05, diff_method="absdiff")

        img1 = create_dummy_image(100, 100, (255, 255, 255))
        img2 = create_dummy_image(100, 100, (255, 255, 255))

        result = detector.detect(img1, img2)

        assert result.has_difference is False
        assert result.score > 0.95
        assert result.diff_image.shape == img1.shape

    def test_detect_with_difference_absdiff(self) -> None:
        """異なる画像で差分ありを検出（絶対差分）"""
        detector = DifferenceDetector(threshold=0.05, diff_method="absdiff")

        img1 = create_dummy_image(100, 100, (255, 255, 255))
        img2 = create_image_with_rect(100, 100, (20, 20), (30, 30))

        result = detector.detect(img1, img2)

        assert result.has_difference is True
        assert result.score < 1.0
        assert result.diff_image.shape == img1.shape


class TestDifferenceDetectorCooldown:
    """クールダウン機能のテスト"""

    def test_cooldown_blocks_detection(self) -> None:
        """クールダウン中は差分検知しないことをテスト"""
        detector = DifferenceDetector(threshold=0.05, diff_method="ssim")
        detector.cooldown = 1.0  # 1秒のクールダウン

        img1 = create_dummy_image(100, 100, (255, 255, 255))
        img2 = create_image_with_rect(100, 100, (20, 20), (30, 30))

        # 最初の検知
        result1 = detector.detect_difference(img1)
        assert not result1  # 初回は前フレームがないのでFalse

        # 2回目の検知（差分あり）
        result2 = detector.detect_difference(img2)
        assert result2  # 差分を検出

        # すぐに3回目の検知（クールダウン中）
        img3 = create_image_with_rect(100, 100, (40, 40), (20, 20))
        result3 = detector.detect_difference(img3)
        assert not result3  # クールダウン中なのでFalse

    def test_cooldown_expires(self) -> None:
        """クールダウン時間経過後は検知できることをテスト"""
        detector = DifferenceDetector(threshold=0.05, diff_method="ssim")
        detector.cooldown = 0.1  # 0.1秒のクールダウン

        img1 = create_dummy_image(100, 100, (255, 255, 255))
        img2 = create_image_with_rect(100, 100, (20, 20), (30, 30))

        # 初回
        detector.detect_difference(img1)
        # 差分検知
        result1 = detector.detect_difference(img2)
        assert result1  # 差分を検出

        # クールダウン時間待機
        time.sleep(0.15)

        # 再度差分検知（異なる画像）
        img3 = create_image_with_rect(100, 100, (40, 40), (20, 20))
        result2 = detector.detect_difference(img3)
        assert result2  # 差分を検出


class TestDifferenceDetectorFrameHistory:
    """フレーム履歴のテスト"""

    def test_frame_history_updates(self) -> None:
        """差分検知時にフレーム履歴が更新されることをテスト"""
        detector = DifferenceDetector(threshold=0.05, diff_method="ssim")
        detector.max_history = 3
        detector.cooldown = 0.0  # クールダウンなし

        img1 = create_dummy_image(100, 100, (255, 255, 255))
        img2 = create_image_with_rect(100, 100, (20, 20), (30, 30))

        # 初回
        detector.detect_difference(img1)
        assert len(detector.frame_history) == 0

        # 差分検知
        detector.detect_difference(img2)
        assert len(detector.frame_history) == 1

    def test_frame_history_max_limit(self) -> None:
        """フレーム履歴が最大数を超えないことをテスト"""
        detector = DifferenceDetector(threshold=0.05, diff_method="ssim")
        detector.max_history = 2
        detector.cooldown = 0.0  # クールダウンなし

        img1 = create_dummy_image(100, 100, (255, 255, 255))

        # 初回
        detector.detect_difference(img1)

        # 複数回差分検知（異なる画像）
        for i in range(5):
            img = create_image_with_rect(100, 100, (i * 10, i * 10), (20, 20))
            detector.detect_difference(img)
            time.sleep(0.01)  # わずかに待機

        # 最大数を超えないことを確認
        assert len(detector.frame_history) <= detector.max_history


class TestDifferenceDetectorShutdown:
    """終了処理のテスト"""

    def test_shutdown_clears_state(self) -> None:
        """shutdownで状態がクリアされることをテスト"""
        detector = DifferenceDetector()

        img1 = create_dummy_image(100, 100, (255, 255, 255))
        img2 = create_image_with_rect(100, 100, (20, 20), (30, 30))

        # 差分検知して状態を設定
        detector.detect_difference(img1)
        detector.detect_difference(img2)

        # shutdown実行
        detector.shutdown()

        # 状態がクリアされている
        assert len(detector.frame_history) == 0
        assert detector.prev_frame is None
        assert detector.is_shutting_down.is_set()

    def test_shutdown_blocks_detection(self) -> None:
        """shutdown後は検知しないことをテスト"""
        detector = DifferenceDetector()

        img = create_image_with_rect(100, 100, (20, 20), (30, 30))

        # shutdown実行
        detector.shutdown()

        # 検知を試みる
        result = detector.detect_difference(img)

        # shutdownフラグが立っているので検知しない
        assert not result


class TestDifferenceDetectorErrorHandling:
    """エラーハンドリングのテスト"""

    def test_detect_with_invalid_images(self) -> None:
        """異なるサイズの画像でエラーが適切に処理されることをテスト"""
        detector = DifferenceDetector(threshold=0.05, diff_method="ssim")

        img_large = create_dummy_image(100, 100, (255, 255, 255))
        img_small = create_dummy_image(50, 50, (255, 255, 255))  # 異なるサイズ

        # エラーが発生してもクラッシュせず、結果を返す
        result = detector.detect(img_large, img_small)

        assert isinstance(result, DiffResult)
        # エラー時は差分なしとする
        assert result.has_difference is False

    def test_detect_with_grayscale_conversion_error(self) -> None:
        """グレースケール変換エラーの処理をテスト"""
        detector = DifferenceDetector(threshold=0.05, diff_method="ssim")

        # 不正な画像データ（1チャンネル）
        img = np.zeros((100, 100), dtype=np.uint8)

        # エラーが発生してもクラッシュしない
        result = detector.detect(img, img)

        assert isinstance(result, DiffResult)
        assert result.has_difference is False
