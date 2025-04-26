"""
Window Capture Reading アプリケーションのメインエントリーポイント。
"""

import logging
import sys
import time
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.services.logger import setup_logger
from src.services.window_capture import WindowCapture
from src.services.ocr_service import OCRService
from src.services.message_detector import MessageDetector
from src.utils.config import load_config

def main() -> None:
    """アプリケーションのメインエントリーポイント。"""
    # 設定の読み込み
    config = load_config()
    
    # ロガーのセットアップ
    setup_logger(config)
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("アプリケーションを開始します")
        
        # キャプチャ間隔の設定
        capture_interval = float(config.get("CAPTURE_INTERVAL", "1.0"))
        
        # サービスの初期化
        window_title = config.get("TARGET_WINDOW_TITLE", "LDPlayer")
        window_capture = WindowCapture(window_title)
        ocr_service = OCRService(config)
        message_detector = MessageDetector(config)
        
        logger.info(f"ウィンドウ '{window_title}' のキャプチャを開始します")
        
        # メインループ
        while True:
            # ウィンドウをキャプチャ
            image = window_capture.capture()
            
            if image:
                logger.debug(f"ウィンドウをキャプチャしました: サイズ {image.width}x{image.height}")
                
                # OCRでテキストを抽出
                text, confidence = ocr_service.extract_text_with_confidence(image)
                
                if text:
                    logger.debug(f"テキスト抽出結果 (信頼度: {confidence:.2f}%):")
                    logger.debug(text)
                    
                    # 新規メッセージの検出
                    new_messages = message_detector.detect_new_messages(text)
                    
                    # 新規メッセージがある場合、ログに出力（後にTTS送信にも使用）
                    if new_messages:
                        for msg in new_messages:
                            logger.info(f"新規メッセージ: {msg}")
                        
                        # TODO: 棒読みちゃんにメッセージを送信する機能を追加
                else:
                    logger.debug("テキストは検出されませんでした")
            else:
                logger.warning("ウィンドウのキャプチャに失敗しました")
            
            # 次のキャプチャまで待機
            time.sleep(capture_interval)
            
    except KeyboardInterrupt:
        logger.info("ユーザーによって停止されました")
    except Exception as e:
        logger.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()