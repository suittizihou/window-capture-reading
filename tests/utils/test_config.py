"""設定管理機能のテストモジュール。

Configクラスの保存・読み込み、デフォルト値などをテストします。
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.utils.config import Config, get_config


class TestConfigInit:
    """Config初期化のテスト"""

    def test_default_values(self) -> None:
        """デフォルト値が正しく設定されることをテスト"""
        # 一時ディレクトリを使用して設定ファイルの読み込みを避ける
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config_path = Path(tmpdir) / "nonexistent.json"

            # exists()とsave()をモック
            with patch.object(Path, "exists", return_value=False):
                with patch.object(Config, "save"):
                    with patch.object(Config, "_get_config_path", return_value=test_config_path):
                        config = Config()

                        assert config.window_title == ""
                        assert config.capture_interval == 1.0
                        assert config.draw_border is False
                        assert config.cursor_capture is False
                        assert config.diff_threshold == 0.05
                        assert config.diff_method == "ssim"
                        assert config.notification_sound is True


class TestConfigSaveLoad:
    """設定の保存・読み込みテスト"""

    def test_save_and_load(self) -> None:
        """設定の保存と読み込みをテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.json"

            # 設定を作成（__post_init__をモック）
            with patch.object(Path, "exists", return_value=False):
                with patch.object(Config, "save"):
                    config = Config()
                    config.config_path = config_path

            # カスタム値を設定
            config.window_title = "Test Window"
            config.capture_interval = 2.0
            config.diff_threshold = 0.1
            config.diff_method = "absdiff"
            config.notification_sound = False
            config.draw_border = True
            config.cursor_capture = True

            # 保存
            config.save()

            # ファイルが作成されたことを確認
            assert config_path.exists()

            # 読み込み
            loaded_config = Config.load(str(config_path))

            # 値が一致することを確認
            assert loaded_config.window_title == "Test Window"
            assert loaded_config.capture_interval == 2.0
            assert loaded_config.diff_threshold == 0.1
            assert loaded_config.diff_method == "absdiff"
            assert loaded_config.notification_sound is False
            assert loaded_config.draw_border is True
            assert loaded_config.cursor_capture is True

    def test_save_creates_directory(self) -> None:
        """保存時に親ディレクトリが自動作成されることをテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "subdir" / "config.json"

            # 設定を作成
            with patch.object(Path, "exists", return_value=False):
                with patch.object(Config, "save"):
                    config = Config()
                    config.config_path = config_path

            # 保存
            config.save()

            # ディレクトリとファイルが作成されたことを確認
            assert config_path.parent.exists()
            assert config_path.exists()

    def test_load_invalid_file(self) -> None:
        """存在しないファイルの読み込みをテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent.json"

            # 存在しないファイルを読み込もうとする
            # エラーは発生せず、デフォルト値のConfigが返される
            config = Config.load(str(config_path))

            # デフォルト値が設定されている
            assert isinstance(config, Config)

    def test_load_corrupted_json(self) -> None:
        """破損したJSONファイルの読み込みをテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "corrupted.json"

            # 破損したJSONファイルを作成
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("{invalid json}")

            # 破損したファイルを読み込もうとする
            # エラーは発生せず、デフォルト値のConfigが返される
            config = Config.load(str(config_path))

            # デフォルト値が設定されている
            assert isinstance(config, Config)


class TestConfigGetConfigSingleton:
    """get_config()のシングルトン動作テスト"""

    def test_get_config_returns_same_instance(self) -> None:
        """get_config()が同じインスタンスを返すことをテスト"""
        # グローバル変数をリセット
        import src.utils.config as config_module

        config_module._CONFIG = None

        with patch.object(Path, "exists", return_value=False):
            with patch.object(Config, "save"):
                config1 = get_config()
                config2 = get_config()

                # 同じインスタンスであることを確認
                assert config1 is config2


class TestConfigFieldValidation:
    """設定フィールドの値検証テスト"""

    def test_valid_diff_method_values(self) -> None:
        """diff_methodの有効な値をテスト"""
        with patch.object(Path, "exists", return_value=False):
            with patch.object(Config, "save"):
                config = Config()

                # 有効な値
                config.diff_method = "ssim"
                assert config.diff_method == "ssim"

                config.diff_method = "absdiff"
                assert config.diff_method == "absdiff"

    def test_numeric_field_types(self) -> None:
        """数値フィールドの型をテスト"""
        with patch.object(Path, "exists", return_value=False):
            with patch.object(Config, "save"):
                config = Config()

                # capture_intervalはfloat
                config.capture_interval = 2.5
                assert isinstance(config.capture_interval, float)
                assert config.capture_interval == 2.5

                # diff_thresholdはfloat
                config.diff_threshold = 0.1
                assert isinstance(config.diff_threshold, float)
                assert config.diff_threshold == 0.1

    def test_boolean_field_types(self) -> None:
        """ブールフィールドの型をテスト"""
        with patch.object(Path, "exists", return_value=False):
            with patch.object(Config, "save"):
                config = Config()

                # notification_soundはbool
                config.notification_sound = False
                assert isinstance(config.notification_sound, bool)
                assert config.notification_sound is False

                config.notification_sound = True
                assert config.notification_sound is True

                # draw_borderはbool
                config.draw_border = True
                assert isinstance(config.draw_border, bool)
                assert config.draw_border is True

                # cursor_captureはbool
                config.cursor_capture = True
                assert isinstance(config.cursor_capture, bool)
                assert config.cursor_capture is True


class TestConfigGetConfigPath:
    """設定ファイルパスの取得テスト"""

    def test_get_config_path_development(self) -> None:
        """開発環境での設定ファイルパス取得をテスト"""
        with patch.object(Path, "exists", return_value=False):
            with patch.object(Config, "save"):
                # frozen=Falseをシミュレート
                with patch("sys.frozen", False, create=True):
                    config = Config()
                    path = config._get_config_path()

                    # プロジェクトルートのconfig.jsonを指すはず
                    assert path.name == "config.json"
                    assert "src" not in str(path)  # srcディレクトリを含まない

    def test_get_config_path_frozen(self) -> None:
        """PyInstaller環境での設定ファイルパス取得をテスト"""
        with patch.object(Path, "exists", return_value=False):
            with patch.object(Config, "save"):
                # frozen=Trueをシミュレート
                with patch("sys.frozen", True, create=True):
                    with patch("sys.executable", "C:\\app\\WindowCaptureReading.exe"):
                        with patch("sys._MEIPASS", "C:\\temp\\meipass", create=True):
                            config = Config()
                            path = config._get_config_path()

                            # EXEと同じディレクトリのconfig.jsonを指すはず
                            assert path.name == "config.json"
                            assert "C:\\app" in str(path) or "C:/app" in str(
                                path
                            ).replace("\\", "/")


class TestConfigJSON:
    """JSON形式での保存内容テスト"""

    def test_saved_json_structure(self) -> None:
        """保存されたJSONの構造をテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            # 設定を作成
            with patch.object(Path, "exists", return_value=False):
                with patch.object(Config, "save"):
                    config = Config()
                    config.config_path = config_path

            config.window_title = "Test"
            config.capture_interval = 1.5

            # 保存
            config.save()

            # JSONファイルを読み込んで確認
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 必要なフィールドが含まれている
            assert "window_title" in data
            assert "capture_interval" in data
            assert "diff_threshold" in data
            assert "diff_method" in data
            assert "notification_sound" in data
            assert "draw_border" in data
            assert "cursor_capture" in data

            # プライベートフィールドは含まれない
            assert "config_path" not in data
            assert "_logger" not in data

    def test_json_encoding_unicode(self) -> None:
        """日本語などのUnicode文字が正しく保存されることをテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            # 設定を作成
            with patch.object(Path, "exists", return_value=False):
                with patch.object(Config, "save"):
                    config = Config()
                    config.config_path = config_path

            # 日本語のウィンドウタイトルを設定
            config.window_title = "テストウィンドウ"

            # 保存
            config.save()

            # 読み込んで確認
            loaded_config = Config.load(str(config_path))
            assert loaded_config.window_title == "テストウィンドウ"
