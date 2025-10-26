"""
設定を管理するモジュール。

設定を管理し、ユーザーが容易に設定を変更できるようにします。
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, cast, ClassVar
import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field, asdict

# グローバル設定オブジェクト
_CONFIG: Optional["Config"] = None


def get_config() -> "Config":
    """
    グローバル設定オブジェクトを取得します。存在しない場合は新規作成します。

    Returns:
        Config: 設定オブジェクト
    """
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = Config()
    return _CONFIG


@dataclass
class Config:
    """
    設定を管理するデータクラス。
    """

    # ウィンドウ設定
    window_title: str = ""
    capture_interval: float = 1.0
    draw_border: bool = False  # キャプチャ時の枠表示
    cursor_capture: bool = False  # マウスカーソルをキャプチャ

    # 差分検出設定
    diff_threshold: float = 0.05
    diff_method: str = "ssim"

    # 通知設定
    notification_sound: bool = True

    # ログ設定
    enable_log_file: bool = False  # ログファイル出力の有効/無効
    enable_verbose_log: bool = False  # 詳細ログ出力（True: DEBUG、False: WARNING）

    # クラス変数
    _logger: ClassVar[logging.Logger] = logging.getLogger(__name__)

    def __post_init__(self) -> None:
        """初期化後の処理。設定ファイルがあれば読み込む。"""
        # 設定ファイルのパスを取得
        self.config_path = self._get_config_path()

        # 設定ファイルが存在する場合は読み込む
        if self.config_path.exists():
            try:
                self._load_from_file(self.config_path)
                self._logger.info(f"設定ファイルを読み込みました: {self.config_path}")
            except Exception as e:
                self._logger.error(f"設定ファイルの読み込みに失敗しました: {e}")
        else:
            # 設定ファイルが存在しない場合は作成する
            self.save()
            self._logger.info(
                f"デフォルト設定ファイルを作成しました: {self.config_path}"
            )

    def _get_config_path(self) -> Path:
        """
        実行環境に応じて設定ファイルのパスを返します。

        Returns:
            Path: 設定ファイルのパス
        """
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            # PyInstallerでexe化されている場合
            exe_dir = Path(sys.executable).parent
            return exe_dir / "config.json"
        else:
            # 通常のスクリプト実行
            return Path(__file__).parent.parent.parent / "config.json"

    def _load_from_file(self, path: Path) -> None:
        """ファイルから設定を読み込みます。

        Args:
            path: 設定ファイルのパス
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 有効なフィールドのみを設定
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
        except Exception as e:
            self._logger.error(f"設定ファイルの読み込みに失敗しました: {e}")

    def save(self, path: Optional[str] = None) -> None:
        """現在の設定をJSONファイルに保存します。

        Args:
            path: 保存先のパス（省略時は標準の設定ファイル）
        """
        save_path = Path(path) if path else self.config_path

        try:
            # 必要なディレクトリを作成
            save_path.parent.mkdir(parents=True, exist_ok=True)

            # dataclassをdictに変換して保存
            with open(save_path, "w", encoding="utf-8") as f:
                # クラス変数は除外
                config_dict = {
                    k: v for k, v in asdict(self).items() if not k.startswith("_")
                }
                if "config_path" in config_dict:
                    del config_dict["config_path"]

                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            self._logger.info(f"設定を保存しました: {save_path}")
        except Exception as e:
            self._logger.error(f"設定の保存に失敗しました: {e}")

    @classmethod
    def load(cls, path: str) -> "Config":
        """ファイルから設定を読み込んで新しいインスタンスを返します。

        Args:
            path: 設定ファイルのパス

        Returns:
            Config: 読み込んだ設定
        """
        config = cls()
        config._load_from_file(Path(path))
        return config

    def get_window_titles(self) -> List[str]:
        """
        現在表示中のウィンドウタイトル一覧を取得します。

        Returns:
            List[str]: ウィンドウタイトルのリスト
        """
        titles = []
        try:
            EnumWindows = ctypes.windll.user32.EnumWindows
            EnumWindowsProc = ctypes.WINFUNCTYPE(
                ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
            )
            GetWindowText = ctypes.windll.user32.GetWindowTextW
            GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
            IsWindowVisible = ctypes.windll.user32.IsWindowVisible

            def foreach(hwnd, lParam):
                if IsWindowVisible(hwnd):
                    length = GetWindowTextLength(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        GetWindowText(hwnd, buff, length + 1)
                        title = buff.value.strip()
                        if title:
                            titles.append(title)
                return True

            EnumWindows(EnumWindowsProc(foreach), 0)
            return sorted(set(titles))
        except Exception as e:
            self._logger.error(f"ウィンドウタイトル一覧の取得に失敗しました: {e}")
            return []
