"""
Window Capture Reading アプリケーションのメインエントリーポイント。
"""

import logging
import sys
import time
from pathlib import Path
from typing import List

# プロジェクトルートへのパスを追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.services.logger import setup_logger
from src.services.window_capture import WindowCapture
from src.services.ocr_service import OCRService
from src.services.message_detector import MessageDetector
from src.services.bouyomi_client import BouyomiClient
from src.utils.config import load_config

def main() -> None:
    """アプリケーションのメインエントリーポイント。"""
    try:
        # 設定の読み込み
        config = load_config()
        
        # ロガーの設定
        logger = setup_logger(config)
        
        # ウィンドウタイトルの取得
        window_title = config.get("TARGET_WINDOW_TITLE", "LDPlayer")
        
        # キャプチャ間隔の設定
        capture_interval = float(config.get("CAPTURE_INTERVAL", "1.0"))
        
        # サービスの初期化
        window_capture = WindowCapture(window_title)
        ocr_service = OCRService(config)
        message_detector = MessageDetector(config)
        
        # 棒読みちゃんクライアントの初期化（有効な場合のみ）
        bouyomi_enabled = config.get("BOUYOMI_ENABLED", "true").lower() == "true"
        bouyomi_client = None
        
        if bouyomi_enabled:
            bouyomi_client = BouyomiClient(config)
            # 接続テスト
            if bouyomi_client.test_connection():
                logger.info("棒読みちゃんに接続しました")
            else:
                logger.warning("棒読みちゃんへの接続に失敗しました。再接続を試みます。")
        else:
            logger.info("棒読みちゃん連携機能は無効に設定されています")
        
        logger.info(f"ウィンドウ '{window_title}' のキャプチャを開始します")
        
        # メインループ
        while True:
            # ウィンドウのキャプチャ
            image = window_capture.capture()
            
            if image:
                logger.debug(f"ウィンドウをキャプチャしました: サイズ {image.width}x{image.height}")
                
                # OCRでテキストを抽出
                text = ocr_service.extract_text(image)
                
                if text:
                    # 新規メッセージの検出
                    new_messages = message_detector.detect_new_messages(text)
                    
                    # 新規メッセージがある場合、処理を行う
                    if new_messages:
                        process_new_messages(new_messages, bouyomi_client, logger)
                else:
                    logger.debug("テキストは検出されませんでした")
            else:
                logger.warning("ウィンドウのキャプチャに失敗しました")
            
            # 次のキャプチャまで待機
            time.sleep(capture_interval)
            
    except Exception as e:
        logger.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)
        sys.exit(1)

def process_new_messages(messages: List[str], bouyomi_client: BouyomiClient, logger: logging.Logger) -> None:
    """新規メッセージを処理します。
    
    Args:
        messages: 処理する新規メッセージのリスト
        bouyomi_client: 棒読みちゃんクライアント
        logger: ロガー
    """
    for msg in messages:
        # ログに出力
        logger.info(f"新規メッセージ: {msg}")
        
        # 棒読みちゃんに送信（クライアントが有効な場合）
        if bouyomi_client:
            if bouyomi_client.speak(msg):
                logger.debug(f"メッセージを棒読みちゃんに送信しました: {msg}")
            else:
                logger.warning(f"メッセージの送信に失敗しました: {msg}")

if __name__ == "__main__":
    main()