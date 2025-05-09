"""アプリケーションのメインモジュール。

アプリケーションのメインループと初期化処理を提供します。
"""

import logging
import threading
import time
import argparse
from typing import Optional, Dict, Any, List, Tuple, cast
from PIL import Image
import numpy as np
from numpy.typing import NDArray
from src.services.window_capture import WindowCapture
from src.services.difference_detector import DifferenceDetector
from src.utils.config import Config, get_config
from src.utils.logging_config import setup_logging

# 画像処理関連の型定義
ImageArray = NDArray[np.uint8]


def run_main_loop(
    running: threading.Event,
    roi: Optional[List[int]] = None,
    callback: Optional[Any] = None,
) -> None:
    """メインループを実行する。

    Args:
        running: 実行状態を制御するイベント
        roi: 関心領域の座標 [x1, y1, x2, y2]
        callback: コールバック関数
    """
    logger = logging.getLogger(__name__)
    config = get_config()

    try:
        # ウィンドウキャプチャの初期化
        window_name = config.window_title or "LDPlayer"
        window_capture = WindowCapture(window_name)

        # 差分検知器の初期化
        detector = DifferenceDetector(
            threshold=config.diff_threshold,
            diff_method=config.diff_method,
        )

        # メインループ
        while running.is_set():
            try:
                # 画面キャプチャ
                frame = window_capture.capture()
                if frame is None:
                    logger.warning("キャプチャに失敗しました")
                    time.sleep(0.2)
                    continue

                # ROIでクロップ
                if roi is not None:
                    x1, y1, x2, y2 = [int(round(v)) for v in roi]
                    x1 = max(0, min(x1, frame.shape[1] - 1))
                    y1 = max(0, min(y1, frame.shape[0] - 1))
                    x2 = max(0, min(x2, frame.shape[1]))
                    y2 = max(0, min(y2, frame.shape[0]))
                    if x2 > x1 and y2 > y1:
                        frame = frame[y1:y2, x1:x2]

                # 差分検知
                has_diff = detector.detect_difference(frame)

                # コールバックがあれば実行
                if callback is not None:
                    callback(has_diff)

                # キャプチャ間隔
                capture_interval = config.capture_interval
                time.sleep(capture_interval)

            except Exception as e:
                logger.error(f"メインループでエラー: {e}", exc_info=True)
                time.sleep(0.2)

    except Exception as e:
        logger.error(f"メインループの初期化でエラー: {e}", exc_info=True)

    finally:
        # 終了処理
        if detector is not None:
            detector.shutdown()
        logger.info("メインループを終了しました")


def main() -> None:
    """アプリケーションのエントリーポイント。"""
    # ロギングの設定
    setup_logging()

    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="Window Capture Reading")
    parser.add_argument(
        "--window-title", "-w", help="キャプチャ対象のウィンドウタイトル", default=None
    )
    parser.add_argument(
        "--no-gui",
        "-n",
        help="GUIを使用せずにコマンドラインモードで実行",
        action="store_true",
    )
    args = parser.parse_args()

    if args.no_gui:
        # コマンドラインモード
        event = threading.Event()
        event.set()
        try:
            run_main_loop(event)
        except KeyboardInterrupt:
            logging.info("Ctrl+Cが押されました。終了します...")
            event.clear()
    else:
        # GUIモード
        from src.gui import start_gui

        start_gui()


if __name__ == "__main__":
    main()
