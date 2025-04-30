import os
import sys
from typing import Optional


def get_resource_path(relative_path: str) -> str:
    """
    リソースファイルのパスを取得する。
    PyInstallerでパッケージ化された場合と通常実行の場合の両方に対応する。

    Args:
        relative_path: リソースファイルの相対パス

    Returns:
        str: リソースファイルの絶対パス
    """
    # exe化されている場合
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
    else:
        # 通常実行の場合
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    return os.path.join(base_dir, relative_path)


def get_sound_file_path() -> str:
    """
    通知音ファイルのパスを取得する。

    Returns:
        str: 通知音ファイルのパス
    """
    return get_resource_path(os.path.join('resources', 'notification_sound.wav')) 