"""
ウィンドウのテキストを読み上げるメインアプリケーション
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
from src.services.ocr_service import OCRService
from src.services.bouyomi_client import BouyomiClient
from src.services.memory_watcher import MemoryWatcher
from src.utils.config import Config
from src.utils.logging_config import setup_logging

# グローバル変数
config: Config = None
ocr_service: OCRService = None
bouyomi_client: BouyomiClient = None
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

    # まず最初にOCRサービスの終了フラグを設定
    if ocr_service:
        ocr_service.is_shutting_down.set()

    # 棒読みちゃんクライアントの終了処理
    logger.info("棒読みちゃんクライアントを終了しています...")
    if bouyomi_client:
        bouyomi_client.close()
        
    # OCRサービスの終了処理
    logger.info("OCRサービスを終了しています...")
    if ocr_service:
        # 終了フラグはすでに設定済み、shutdown処理を実行
        ocr_service.shutdown()

def run_main_loop(running_flag: Callable[[], bool]) -> None:
    """
    OCR・読み上げメインループを外部から制御可能な関数として実行します。

    Args:
        running_flag: ループ継続判定用のコール可能オブジェクト（例: lambda: True/False）
    """
    global config, ocr_service, bouyomi_client, window_capture, memory_watcher
    setup_logging()
    logger = logging.getLogger()
    logger.info("メインループを開始します (GUI制御)")
    config = Config()
    window_capture = WindowCapture(config.get("TARGET_WINDOW_TITLE", "LDPlayer"))
    ocr_service = OCRService(config)
    bouyomi_client = BouyomiClient(config)
    if config.get("MEMORY_WATCHER_ENABLED", "false").lower() == "true":
        memory_watcher = MemoryWatcher(config)
        memory_watcher.start()
        logger.info("メモリ監視を開始しました")
    last_text: str = ""
    ignore_texts: Set[str] = set()
    capture_interval = float(config.get("CAPTURE_INTERVAL", "1.0"))
    try:
        while running_flag():
            loop_start_time = time.time()
            try:
                if ocr_service and ocr_service.is_shutting_down.is_set():
                    time.sleep(0.1)
                    continue
                frame = window_capture.capture()
                if frame is None:
                    logger.warning("ウィンドウのキャプチャに失敗しました。次のフレームを試みます...")
                    time.sleep(capture_interval)
                    continue
                if ocr_service and ocr_service.is_shutting_down.is_set():
                    continue
                if ocr_service and not ocr_service.is_shutting_down.is_set():
                    text = ocr_service.extract_text(frame)
                    if ocr_service.is_shutting_down.is_set():
                        continue
                    if text and text != last_text and text not in ignore_texts:
                        logger.info(f"抽出されたテキスト: {text}")
                        last_text = text
                        if bouyomi_client:
                            bouyomi_client.talk(text)
                            ignore_limit = int(config.get("IGNORE_TEXT_LIMIT", "10"))
                            if ignore_limit > 0:
                                ignore_texts.add(text)
                                if len(ignore_texts) > ignore_limit:
                                    ignore_texts.pop()
                elapsed_time = time.time() - loop_start_time
                if elapsed_time < capture_interval and running_flag() and (not ocr_service or not ocr_service.is_shutting_down.is_set()):
                    time.sleep(capture_interval - elapsed_time)
            except Exception as e:
                if running_flag() and (not ocr_service or not ocr_service.is_shutting_down.is_set()):
                    logger.error(f"メインループでエラーが発生しました: {e}", exc_info=True)
                    time.sleep(1)
                else:
                    logger.debug(f"終了処理中にエラーが発生しました: {e}")
                    time.sleep(0.1)
        logger.info("メインループを終了しました (GUI制御)")
    except Exception as e:
        logger.error(f"メインループ実行中にエラーが発生しました: {e}", exc_info=True)
    finally:
        if ocr_service:
            ocr_service.is_shutting_down.set()
            try:
                ocr_service.shutdown()
                logger.info("OCRサービスの終了処理が完了しました")
            except Exception as e:
                logger.error(f"OCRサービスの終了処理中にエラーが発生しました: {e}")
        if memory_watcher:
            try:
                memory_watcher.stop()
                logger.info("メモリ監視を停止しました")
            except Exception as e:
                logger.error(f"メモリウォッチャーの停止中にエラーが発生しました: {e}")