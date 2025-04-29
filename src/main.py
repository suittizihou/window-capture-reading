"""
ウィンドウの画面差異検知メインアプリケーション
"""

import os
import sys
import signal
import time
import logging
from typing import Dict, Any, Optional, List, Set, Tuple, Callable
import threading

import cv2
import numpy as np

from src.services.window_capture import WindowCapture
from src.services.difference_detector import DifferenceDetector
from src.services.memory_watcher import MemoryWatcher
from src.utils.config import Config
from src.utils.logging_config import setup_logging

# グローバル変数
config: Config = None
difference_detector: Optional[DifferenceDetector] = None
window_capture: WindowCapture = None
memory_watcher: Optional[MemoryWatcher] = None
running: bool = True

def signal_handler(sig: int, frame: Any) -> None:
    """シグナルハンドラ関数。プログラムの終了を処理します。

    Args:
        sig: シグナル番号
        frame: 現在のスタックフレーム
    """
    global running
    logger = logging.getLogger()
    logger.info("終了シグナルを受信しました。アプリケーションを終了します...")
    
    # 終了フラグを設定
    running = False

    # 差異検出サービスの終了処理
    logger.info("差異検出サービスを終了しています...")
    if difference_detector:
        difference_detector.shutdown()

def run_main_loop(running_flag: Callable[[], bool]) -> None:
    """
    画面差異検知メインループを外部から制御可能な関数として実行します。

    Args:
        running_flag: ループ継続判定用のコール可能オブジェクト（例: lambda: True/False）
    """
    global config, difference_detector, window_capture, memory_watcher
    setup_logging()
    logger = logging.getLogger()
    logger.info("メインループを開始します (GUI制御)")
    config = Config()
    window_capture = WindowCapture(config.get("TARGET_WINDOW_TITLE", "LDPlayer"))
    difference_detector = DifferenceDetector(config)
    
    if config.get("MEMORY_WATCHER_ENABLED", "false").lower() == "true":
        memory_watcher = MemoryWatcher(config)
        memory_watcher.start()
        logger.info("メモリ監視を開始しました")
    
    capture_interval = float(config.get("CAPTURE_INTERVAL", "1.0"))
    notification_sound = config.get("NOTIFICATION_SOUND", "true").lower() == "true"
    
    try:
        while running_flag():
            loop_start_time = time.time()
            try:
                # 差異検出サービスが終了中なら待機
                if difference_detector and difference_detector.is_shutting_down.is_set():
                    time.sleep(0.1)
                    continue
                
                frame = window_capture.capture()
                if frame is None:
                    logger.warning("ウィンドウのキャプチャに失敗しました。次のフレームを試みます...")
                    time.sleep(capture_interval)
                    continue
                
                # 差異検出サービスが終了中なら待機
                if difference_detector and difference_detector.is_shutting_down.is_set():
                    continue
                
                # 画像の差異を検出
                if difference_detector and not difference_detector.is_shutting_down.is_set():
                    has_difference, debug_image, diff_score = difference_detector.compare_frames(frame)
                    
                    # 差異検出サービスが終了中なら待機
                    if difference_detector.is_shutting_down.is_set():
                        continue
                    
                    # 差異がある場合は通知
                    if has_difference:
                        logger.info(f"画面の変化を検知しました: スコア {diff_score:.4f}")
                        
                        # Windows通知を表示
                        if notification_sound:
                            try:
                                # Windows 10/11向けの通知
                                from win10toast import ToastNotifier
                                
                                notification_title = config.get("NOTIFICATION_TITLE", "画面の変化を検知しました")
                                toaster = ToastNotifier()
                                toaster.show_toast(
                                    notification_title,
                                    f"差異スコア: {diff_score:.4f}",
                                    duration=3,
                                    threaded=True
                                )
                            except ImportError:
                                # 通知ライブラリがない場合はビープ音のみ
                                import winsound
                                winsound.Beep(1000, 200)  # 1000Hz, 200ミリ秒
                                logger.warning("win10toast がインストールされていないため、ビープ音による通知を使用します")
                            except Exception as e:
                                logger.error(f"通知の表示中にエラーが発生しました: {e}", exc_info=True)
                
                elapsed_time = time.time() - loop_start_time
                if elapsed_time < capture_interval and running_flag() and (not difference_detector or not difference_detector.is_shutting_down.is_set()):
                    time.sleep(capture_interval - elapsed_time)
            except Exception as e:
                if running_flag() and (not difference_detector or not difference_detector.is_shutting_down.is_set()):
                    logger.error(f"メインループでエラーが発生しました: {e}", exc_info=True)
                    time.sleep(1)
                else:
                    logger.debug(f"終了処理中にエラーが発生しました: {e}")
                    time.sleep(0.1)
        logger.info("メインループを終了しました (GUI制御)")
    except Exception as e:
        logger.error(f"メインループ実行中にエラーが発生しました: {e}", exc_info=True)
    finally:
        if difference_detector:
            difference_detector.is_shutting_down.set()
            try:
                difference_detector.shutdown()
                logger.info("差異検出サービスの終了処理が完了しました")
            except Exception as e:
                logger.error(f"差異検出サービスの終了処理中にエラーが発生しました: {e}")
        if memory_watcher:
            try:
                memory_watcher.stop()
                logger.info("メモリ監視を停止しました")
            except Exception as e:
                logger.error(f"メモリウォッチャーの停止中にエラーが発生しました: {e}")