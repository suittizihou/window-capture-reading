"""
Window Capture Reading アプリケーションのメインエントリーポイント。
"""

import logging
import sys
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.services.logger import setup_logger
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
        # TODO: 各サービスの初期化と実行
        
    except Exception as e:
        logger.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
