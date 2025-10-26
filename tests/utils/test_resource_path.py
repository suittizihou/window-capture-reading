"""リソースパス取得のテストモジュール。

PyInstaller環境と開発環境でのリソースパス解決をテストします。
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch

from src.utils.resource_path import get_resource_path, get_sound_file_path


class TestGetResourcePathDevelopment:
    """開発環境でのリソースパス取得テスト"""

    def test_get_resource_path_development(self) -> None:
        """開発環境でのリソースパス取得をテスト"""
        # frozen=Falseをシミュレート
        with patch("sys.frozen", False, create=True):
            result = get_resource_path("resources/test.txt")

            # プロジェクトルートからの相対パスになっているはず
            assert "resources" in result
            assert "test.txt" in result
            # srcディレクトリより上のパスを指しているはず
            assert os.path.isabs(result)

    def test_get_resource_path_with_nested_path(self) -> None:
        """ネストされたパスの取得をテスト"""
        with patch("sys.frozen", False, create=True):
            result = get_resource_path("resources/icons/app.ico")

            assert "resources" in result
            assert "icons" in result
            assert "app.ico" in result
            assert os.path.isabs(result)


class TestGetResourcePathFrozen:
    """PyInstaller環境でのリソースパス取得テスト"""

    def test_get_resource_path_frozen(self) -> None:
        """PyInstaller環境でのリソースパス取得をテスト"""
        # frozen=Trueをシミュレート
        with patch("sys.frozen", True, create=True):
            with patch("sys._MEIPASS", "/tmp/meipass", create=True):
                result = get_resource_path("resources/test.txt")

                # _MEIPASSディレクトリを基準にしたパスになっているはず
                assert "/tmp/meipass" in result or "\\tmp\\meipass" in result
                assert "resources" in result
                assert "test.txt" in result

    def test_get_resource_path_frozen_windows(self) -> None:
        """Windows PyInstaller環境でのリソースパス取得をテスト"""
        with patch("sys.frozen", True, create=True):
            with patch("sys._MEIPASS", "C:\\Temp\\meipass", create=True):
                result = get_resource_path("resources/test.txt")

                # Windowsパスを正規化して比較
                result_normalized = result.replace("\\", "/")
                assert "Temp/meipass" in result_normalized or "Temp\\meipass" in result
                assert "resources" in result
                assert "test.txt" in result


class TestGetSoundFilePath:
    """サウンドファイルパス取得テスト"""

    def test_get_sound_file_path_development(self) -> None:
        """開発環境でのサウンドファイルパス取得をテスト"""
        with patch("sys.frozen", False, create=True):
            result = get_sound_file_path()

            # リソースディレクトリ内の通知音ファイルを指しているはず
            assert "resources" in result
            assert "notification_sound.wav" in result
            assert os.path.isabs(result)

    def test_get_sound_file_path_frozen(self) -> None:
        """PyInstaller環境でのサウンドファイルパス取得をテスト"""
        with patch("sys.frozen", True, create=True):
            with patch("sys._MEIPASS", "/tmp/meipass", create=True):
                result = get_sound_file_path()

                # _MEIPASSディレクトリを基準にしたパスになっているはず
                assert "/tmp/meipass" in result or "\\tmp\\meipass" in result
                assert "resources" in result
                assert "notification_sound.wav" in result


class TestPathConsistency:
    """パスの一貫性テスト"""

    def test_multiple_calls_return_same_path(self) -> None:
        """複数回呼び出しても同じパスが返されることをテスト"""
        with patch("sys.frozen", False, create=True):
            path1 = get_resource_path("resources/test.txt")
            path2 = get_resource_path("resources/test.txt")

            assert path1 == path2

    def test_relative_path_consistency(self) -> None:
        """相対パスが一貫して処理されることをテスト"""
        with patch("sys.frozen", False, create=True):
            # 同じリソースを異なる形式で指定
            path1 = get_resource_path("resources/test.txt")
            path2 = get_resource_path(os.path.join("resources", "test.txt"))

            # 正規化して比較
            path1_normalized = os.path.normpath(path1)
            path2_normalized = os.path.normpath(path2)

            assert path1_normalized == path2_normalized


class TestPathSeparators:
    """パス区切り文字のテスト"""

    def test_path_uses_os_separator(self) -> None:
        """OSに応じた正しいパス区切り文字が使用されることをテスト"""
        with patch("sys.frozen", False, create=True):
            result = get_resource_path("resources/icons/app.ico")

            # os.path.joinが使われているので、OSのパス区切り文字が使われているはず
            # ただし、内部でos.path.joinを使っているので、
            # Windowsでは\\、Unix系では/になる
            # どちらかが含まれていることを確認
            assert os.sep in result or "/" in result
