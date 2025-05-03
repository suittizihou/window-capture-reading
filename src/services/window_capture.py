"""ウィンドウキャプチャ機能を提供するモジュール。

Win32 APIを使用して、指定されたウィンドウのキャプチャを行います。
"""

import logging
from ctypes import (
    windll,
    byref,
    c_ubyte,
    Array,
    Structure,
    c_long,
    c_ulong,
    c_void_p,
    c_ushort,
    sizeof,
)
from ctypes.wintypes import BOOL, HWND, HDC, RECT
from typing import Optional, Tuple, Any, cast
import numpy as np
from numpy.typing import NDArray
import cv2
from PIL import Image

# 画像処理関連の型定義
ImageArray = NDArray[np.uint8]


class WindowCapture:
    """ウィンドウキャプチャ機能を提供するクラス。"""

    def __init__(self, window_title: str) -> None:
        """ウィンドウキャプチャクラスを初期化します。

        Args:
            window_title: キャプチャ対象のウィンドウタイトル
        """
        self.window_title = window_title
        self.logger = logging.getLogger(__name__)

        # Win32 APIの関数を取得
        self.user32 = windll.user32
        self.gdi32 = windll.gdi32

    def find_window(self) -> Optional[HWND]:
        """指定されたタイトルのウィンドウハンドルを取得します。

        Returns:
            ウィンドウハンドル。見つからない場合はNone。
        """
        try:
            hwnd = self.user32.FindWindowW(None, self.window_title)
            if not hwnd:
                self.logger.warning(f"ウィンドウが見つかりません: {self.window_title}")
                return None
            return cast(HWND, hwnd)
        except Exception as e:
            self.logger.error(f"ウィンドウの検索中にエラー: {e}")
            return None

    def get_window_rect(self, hwnd: HWND) -> Optional[Tuple[int, int, int, int]]:
        """ウィンドウの位置とサイズを取得します。

        Args:
            hwnd: ウィンドウハンドル

        Returns:
            (x, y, width, height)のタプル。取得失敗時はNone。
        """
        try:
            rect = RECT()
            if not self.user32.GetWindowRect(hwnd, byref(rect)):
                self.logger.error("ウィンドウの位置とサイズの取得に失敗しました")
                return None
            return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
        except Exception as e:
            self.logger.error(f"ウィンドウの位置とサイズの取得中にエラー: {e}")
            return None

    def capture(self) -> Optional[ImageArray]:
        """ウィンドウをキャプチャします。

        Returns:
            キャプチャした画像。失敗時はNone。
        """
        try:
            # ウィンドウハンドルを取得
            hwnd = self.find_window()
            if not hwnd:
                return None

            # ウィンドウの位置とサイズを取得
            rect = self.get_window_rect(hwnd)
            if not rect:
                return None
            x, y, width, height = rect

            # ウィンドウのDCを取得
            hwnd_dc = self.user32.GetDC(hwnd)
            if not hwnd_dc:
                self.logger.error("ウィンドウのDC取得に失敗しました")
                return None

            # 互換DCを作成
            mfc_dc = self.gdi32.CreateCompatibleDC(hwnd_dc)
            if not mfc_dc:
                self.user32.ReleaseDC(hwnd, hwnd_dc)
                self.logger.error("互換DC作成に失敗しました")
                return None

            # ビットマップを作成
            save_bit = self.gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
            if not save_bit:
                self.gdi32.DeleteDC(mfc_dc)
                self.user32.ReleaseDC(hwnd, hwnd_dc)
                self.logger.error("ビットマップ作成に失敗しました")
                return None

            # ビットマップを選択
            self.gdi32.SelectObject(mfc_dc, save_bit)

            # 画面をコピー
            self.gdi32.BitBlt(
                mfc_dc, 0, 0, width, height, hwnd_dc, 0, 0, 0x00CC0020
            )  # SRCCOPY

            # ビットマップ情報を取得
            bmp_info = self._create_bitmap_info(width, height)
            if not bmp_info:
                self.gdi32.DeleteObject(save_bit)
                self.gdi32.DeleteDC(mfc_dc)
                self.user32.ReleaseDC(hwnd, hwnd_dc)
                return None

            # 画像データを取得
            image_data = np.zeros((height, width, 4), dtype=np.uint8)
            self.gdi32.GetDIBits(
                mfc_dc,
                save_bit,
                0,
                height,
                image_data.ctypes.data_as(c_void_p),
                bmp_info,
                0,
            )

            # リソースを解放
            self.gdi32.DeleteObject(save_bit)
            self.gdi32.DeleteDC(mfc_dc)
            self.user32.ReleaseDC(hwnd, hwnd_dc)

            # BGRAからBGRに変換
            image_data_bgr = cv2.cvtColor(image_data, cv2.COLOR_BGRA2BGR)

            return cast(ImageArray, image_data_bgr)

        except Exception as e:
            self.logger.error(f"画面キャプチャ中にエラー: {e}")
            return None

    def _create_bitmap_info(self, width: int, height: int) -> Optional[Any]:
        """ビットマップ情報構造体を作成します。

        Args:
            width: 画像の幅
            height: 画像の高さ

        Returns:
            ビットマップ情報構造体。作成失敗時はNone。
        """
        try:

            class BITMAPINFOHEADER(Structure):
                _fields_ = [
                    ("biSize", c_ulong),
                    ("biWidth", c_long),
                    ("biHeight", c_long),
                    ("biPlanes", c_ushort),
                    ("biBitCount", c_ushort),
                    ("biCompression", c_ulong),
                    ("biSizeImage", c_ulong),
                    ("biXPelsPerMeter", c_long),
                    ("biYPelsPerMeter", c_long),
                    ("biClrUsed", c_ulong),
                    ("biClrImportant", c_ulong),
                ]

            class BITMAPINFO(Structure):
                _fields_ = [("bmiHeader", BITMAPINFOHEADER)]

            # ビットマップ情報を設定
            bmp_info = BITMAPINFO()
            bmp_info.bmiHeader.biSize = sizeof(BITMAPINFOHEADER)
            bmp_info.bmiHeader.biWidth = width
            bmp_info.bmiHeader.biHeight = -height  # トップダウン
            bmp_info.bmiHeader.biPlanes = 1
            bmp_info.bmiHeader.biBitCount = 32
            bmp_info.bmiHeader.biCompression = 0  # BI_RGB
            return bmp_info

        except Exception as e:
            self.logger.error(f"ビットマップ情報構造体の作成中にエラー: {e}")
            return None
