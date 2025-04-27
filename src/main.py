"""
ウィンドウのテキストを読み上げるメインアプリケーション
"""

import os
import sys
import signal
import time
import logging
from typing import Dict, Any, Optional, List, Set, Tuple

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

def main() -> None:
    """メインアプリケーション関数"""
    global config, ocr_service, bouyomi_client, window_capture, memory_watcher, running
    
    # ロギングの設定
    setup_logging()
    logger = logging.getLogger()
    logger.info("アプリケーションを開始しています...")
    
    # 設定の読み込み
    config = Config()
    
    # シグナルハンドラの設定
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # サービスの初期化
        window_capture = WindowCapture(config.get("TARGET_WINDOW_TITLE", "LDPlayer"))
        ocr_service = OCRService(config)
        bouyomi_client = BouyomiClient(config)
        
        # メモリウォッチャーの初期化（オプショナル）
        if config.get("MEMORY_WATCHER_ENABLED", "false").lower() == "true":
            memory_watcher = MemoryWatcher(config)
            memory_watcher.start()
            logger.info("メモリ監視を開始しました")
        
        # 前回のテキスト（重複読み上げ防止用）
        last_text: str = ""
        ignore_texts: Set[str] = set()
        
        # キャプチャ間隔（秒）
        capture_interval = float(config.get("CAPTURE_INTERVAL", "1.0"))
        
        # メインループ
        logger.info("メインループを開始します")
        while running:
            loop_start_time = time.time()
            
            try:
                # 終了処理中は処理をスキップ
                if not running or (ocr_service and ocr_service.is_shutting_down.is_set()):
                    logger.debug("終了フラグが設定されました。ループをスキップします...")
                    time.sleep(0.1)
                    continue
                
                # ウィンドウのキャプチャ
                frame = window_capture.capture()
                
                if frame is None:
                    logger.warning("ウィンドウのキャプチャに失敗しました。次のフレームを試みます...")
                    time.sleep(capture_interval)
                    continue
                
                # 終了処理中は画像処理とOCRをスキップ
                if not running or (ocr_service and ocr_service.is_shutting_down.is_set()):
                    logger.debug("終了処理中のためOCR処理をスキップします")
                    continue
                
                # 画像からテキストを抽出
                if ocr_service and not ocr_service.is_shutting_down.is_set():
                    text = ocr_service.extract_text(frame)
                    
                    # 終了処理中はテキスト処理をスキップ
                    if not running or ocr_service.is_shutting_down.is_set():
                        continue
                    
                    # テキストが抽出され、かつ前回と異なる場合は読み上げる
                    if text and text != last_text and text not in ignore_texts:
                        logger.info(f"抽出されたテキスト: {text}")
                        last_text = text
                        
                        # 終了処理中は読み上げをスキップ
                        if not running or (ocr_service and ocr_service.is_shutting_down.is_set()):
                            continue
                            
                        # 読み上げ
                        if bouyomi_client:
                            bouyomi_client.talk(text)
                            
                            # 無視リストに追加（設定による）
                            ignore_limit = int(config.get("IGNORE_TEXT_LIMIT", "10"))
                            if ignore_limit > 0:
                                ignore_texts.add(text)
                                # 無視リストのサイズを制限
                                if len(ignore_texts) > ignore_limit:
                                    ignore_texts.pop()
                
                # キャプチャ間隔を待機
                elapsed_time = time.time() - loop_start_time
                if elapsed_time < capture_interval and running and (not ocr_service or not ocr_service.is_shutting_down.is_set()):
                    time.sleep(capture_interval - elapsed_time)
                    
            except Exception as e:
                if running and (not ocr_service or not ocr_service.is_shutting_down.is_set()):  # 終了中でなければ詳細なエラーログを出力
                    logger.error(f"メインループでエラーが発生しました: {e}", exc_info=True)
                else:
                    logger.debug(f"終了処理中にエラーが発生しました: {e}")
                
                # エラー発生時は少し待機（終了処理中でない場合のみ）
                if running and (not ocr_service or not ocr_service.is_shutting_down.is_set()):
                    time.sleep(1)
                else:
                    time.sleep(0.1)  # 終了処理中は短い待機
        
        logger.info("メインループを終了しました")
        
    except Exception as e:
        logger.error(f"アプリケーションの初期化中にエラーが発生しました: {e}", exc_info=True)
    
    finally:
        # 終了フラグを確実に設定
        running = False
        
        # OCRサービスの終了処理（まだ実行されていない場合）
        if ocr_service:
            # まず終了フラグを必ず設定
            ocr_service.is_shutting_down.set()
            try:
                ocr_service.shutdown()
                logger.info("OCRサービスの終了処理が完了しました")
            except Exception as e:
                logger.error(f"OCRサービスの終了処理中にエラーが発生しました: {e}")
        
        # メモリウォッチャーの停止
        if memory_watcher:
            try:
                memory_watcher.stop()
                logger.info("メモリ監視を停止しました")
            except Exception as e:
                logger.error(f"メモリウォッチャーの停止中にエラーが発生しました: {e}")
        
        logger.info("アプリケーションを終了します")

if __name__ == "__main__":
    main()