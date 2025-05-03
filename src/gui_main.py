"""レガシーGUIモジュール。

このモジュールは、リファクタリングされた新しいGUIモジュールに置き換えられました。
後方互換性のために維持されています。
"""

from src.gui import start_gui


def main():
    """アプリケーションを起動します（レガシー互換関数）。"""
    start_gui()


if __name__ == "__main__":
    main()
