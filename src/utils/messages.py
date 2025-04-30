"""メッセージの多言語対応を管理するモジュール。"""

from typing import Dict, Optional
import os

# 利用可能な言語
AVAILABLE_LANGUAGES = ["ja", "en"]

# デフォルト言語
DEFAULT_LANGUAGE = "ja"

# メッセージ定義
MESSAGES: Dict[str, Dict[str, str]] = {
    "ja": {
        "ocr_success": "テキストを抽出しました: {length}文字",
        "ocr_empty": "テキストが検出されませんでした",
        "ocr_error": "テキスト抽出中にエラーが発生しました: {error}",
        "tesseract_not_found": "Tesseractが指定されたパスに見つかりません: {path}",
        "preprocessing_error": "画像の前処理中にエラーが発生しました: {error}",
        "test_success": "OCRエンジンのテストに成功しました",
        "test_failure": "OCRエンジンのテストに失敗しました",
    },
    "en": {
        "ocr_success": "Text extracted: {length} characters",
        "ocr_empty": "No text detected",
        "ocr_error": "Error occurred during text extraction: {error}",
        "tesseract_not_found": "Tesseract not found at specified path: {path}",
        "preprocessing_error": "Error occurred during image preprocessing: {error}",
        "test_success": "OCR engine test succeeded",
        "test_failure": "OCR engine test failed",
    },
}


class MessageManager:
    """メッセージ管理クラス。"""

    def __init__(self):
        """メッセージマネージャーを初期化します。"""
        self.language = os.environ.get("MESSAGE_LANGUAGE", DEFAULT_LANGUAGE)
        if self.language not in AVAILABLE_LANGUAGES:
            self.language = DEFAULT_LANGUAGE

    def get(self, key: str, **kwargs) -> str:
        """メッセージを取得します。

        Args:
            key: メッセージのキー
            **kwargs: メッセージ内の変数に対応する値

        Returns:
            str: フォーマットされたメッセージ
        """
        try:
            message = MESSAGES[self.language][key]
            return message.format(**kwargs) if kwargs else message
        except KeyError:
            # キーが見つからない場合はデフォルト言語のメッセージを返す
            try:
                message = MESSAGES[DEFAULT_LANGUAGE][key]
                return message.format(**kwargs) if kwargs else message
            except KeyError:
                return f"Message not found: {key}"

    def set_language(self, language: str) -> None:
        """使用する言語を設定します。

        Args:
            language: 言語コード（"ja"または"en"）
        """
        if language in AVAILABLE_LANGUAGES:
            self.language = language


# シングルトンインスタンス
message_manager = MessageManager()
