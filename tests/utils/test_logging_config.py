"""ログ設定のテストモジュール。

アプリケーションのロギング設定をテストします。
"""

import pytest
import logging
import sys
from unittest.mock import patch, MagicMock
from typing import List

from src.utils.logging_config import setup_logging


class TestLoggingConfigDevelopment:
    """開発環境でのログ設定テスト"""

    def test_setup_logging_development(self) -> None:
        """開発環境でのログ設定をテスト"""
        # frozen=Falseをシミュレート
        with patch("sys.frozen", False, create=True):
            with patch("logging.basicConfig") as mock_basic_config:
                setup_logging()

                # basicConfigが呼ばれたことを確認
                mock_basic_config.assert_called_once()

                # 呼び出された引数を取得
                call_kwargs = mock_basic_config.call_args[1]

                # ログレベルがDEBUGであることを確認
                assert call_kwargs["level"] == logging.DEBUG

                # ハンドラーが2つあることを確認（コンソール+ファイル）
                handlers = call_kwargs["handlers"]
                assert len(handlers) == 2

                # StreamHandlerとFileHandlerが含まれていることを確認
                handler_types = [type(h).__name__ for h in handlers]
                assert "StreamHandler" in handler_types
                assert "FileHandler" in handler_types

    def test_log_format_development(self) -> None:
        """開発環境でのログフォーマットをテスト"""
        with patch("sys.frozen", False, create=True):
            with patch("logging.basicConfig") as mock_basic_config:
                setup_logging()

                call_kwargs = mock_basic_config.call_args[1]
                log_format = call_kwargs["format"]

                # フォーマットに必要な要素が含まれていることを確認
                assert "%(asctime)s" in log_format
                assert "%(levelname)s" in log_format
                assert "%(name)s" in log_format


class TestLoggingConfigFrozen:
    """製品ビルド環境でのログ設定テスト"""

    def test_setup_logging_frozen(self) -> None:
        """製品ビルド環境でのログ設定をテスト"""
        # frozen=Trueをシミュレート
        with patch("sys.frozen", True, create=True):
            with patch("sys._MEIPASS", "/tmp/meipass", create=True):
                with patch("logging.basicConfig") as mock_basic_config:
                    setup_logging()

                    # basicConfigが呼ばれたことを確認
                    mock_basic_config.assert_called_once()

                    # 呼び出された引数を取得
                    call_kwargs = mock_basic_config.call_args[1]

                    # ログレベルがINFOであることを確認
                    assert call_kwargs["level"] == logging.INFO

                    # ハンドラーが1つであることを確認（ファイルのみ）
                    handlers = call_kwargs["handlers"]
                    assert len(handlers) == 1

                    # FileHandlerであることを確認
                    handler_types = [type(h).__name__ for h in handlers]
                    assert "FileHandler" in handler_types
                    assert "StreamHandler" not in handler_types

    def test_log_format_frozen(self) -> None:
        """製品ビルド環境でのログフォーマットをテスト"""
        with patch("sys.frozen", True, create=True):
            with patch("sys._MEIPASS", "/tmp/meipass", create=True):
                with patch("logging.basicConfig") as mock_basic_config:
                    setup_logging()

                    call_kwargs = mock_basic_config.call_args[1]
                    log_format = call_kwargs["format"]

                    # フォーマットに必要な要素が含まれていることを確認
                    assert "%(asctime)s" in log_format
                    assert "%(levelname)s" in log_format
                    assert "%(name)s" in log_format


class TestLoggingLevelDifference:
    """環境によるログレベルの違いをテスト"""

    def test_log_level_is_debug_in_dev(self) -> None:
        """開発環境ではDEBUGレベルであることをテスト"""
        with patch("sys.frozen", False, create=True):
            with patch("logging.basicConfig") as mock_basic_config:
                setup_logging()

                call_kwargs = mock_basic_config.call_args[1]
                assert call_kwargs["level"] == logging.DEBUG

    def test_log_level_is_info_in_frozen(self) -> None:
        """製品環境ではINFOレベルであることをテスト"""
        with patch("sys.frozen", True, create=True):
            with patch("sys._MEIPASS", "/tmp/meipass", create=True):
                with patch("logging.basicConfig") as mock_basic_config:
                    setup_logging()

                    call_kwargs = mock_basic_config.call_args[1]
                    assert call_kwargs["level"] == logging.INFO


class TestFileHandlerEncoding:
    """FileHandlerのエンコーディングテスト"""

    def test_file_handler_utf8_encoding(self) -> None:
        """FileHandlerがUTF-8エンコーディングであることをテスト"""
        with patch("sys.frozen", False, create=True):
            with patch("logging.basicConfig") as mock_basic_config:
                setup_logging()

                call_kwargs = mock_basic_config.call_args[1]
                handlers = call_kwargs["handlers"]

                # FileHandlerを取得
                file_handlers = [
                    h for h in handlers if type(h).__name__ == "FileHandler"
                ]
                assert len(file_handlers) == 1

                # エンコーディングがUTF-8であることを確認
                file_handler = file_handlers[0]
                # encoding属性が存在するかチェック（Python内部実装依存なので柔軟に）
                if hasattr(file_handler, "encoding"):
                    assert file_handler.encoding == "utf-8"
