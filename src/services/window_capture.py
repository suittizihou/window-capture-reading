"""ウィンドウキャプチャ機能を提供するモジュール。

Win32 APIを使用して、指定されたウィンドウのキャプチャを行います。
"""

import logging
from ctypes import windll, byref, c_ubyte
from ctypes.wintypes import BOOL, HWND, HDC, RECT
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image

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
            Optional[HWND]: ウィンドウハンドル。見つからない場合はNone。
        """
        hwnd = self.user32.FindWindowW(None, self.window_title)
        if not hwnd:
            self.logger.warning(f"ウィンドウ'{self.window_title}'が見つかりませんでした")
            return None
        return hwnd
    
    def get_window_rect(self, hwnd: HWND) -> Optional[RECT]:
        """ウィンドウの矩形情報を取得します。

        Args:
            hwnd: ウィンドウハンドル

        Returns:
            Optional[RECT]: ウィンドウの矩形情報。取得失敗時はNone。
        """
        rect = RECT()
        if not self.user32.GetWindowRect(hwnd, byref(rect)):
            self.logger.error(f"ウィンドウの矩形情報の取得に失敗しました: {hwnd}")
            return None
        return rect
    
    def capture(self) -> Optional[Image.Image]:
        """ウィンドウをキャプチャします。

        Returns:
            Optional[Image.Image]: キャプチャしたPIL Imageオブジェクト。失敗時はNone。
        """
        try:
            # ウィンドウハンドルを取得
            hwnd = self.find_window()
            if not hwnd:
                return None
            
            # ウィンドウの矩形情報を取得
            rect = self.get_window_rect(hwnd)
            if not rect:
                return None
            
            # ウィンドウの幅と高さを計算
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            
            # ウィンドウのDCを取得
            hwnd_dc = self.user32.GetDC(hwnd)
            if not hwnd_dc:
                self.logger.error("ウィンドウDCの取得に失敗しました")
                return None
            
            # メモリDCを作成
            mem_dc = self.gdi32.CreateCompatibleDC(hwnd_dc)
            if not mem_dc:
                self.logger.error("メモリDCの作成に失敗しました")
                self.user32.ReleaseDC(hwnd, hwnd_dc)
                return None
            
            # ビットマップを作成
            bitmap = self.gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
            if not bitmap:
                self.logger.error("ビットマップの作成に失敗しました")
                self.gdi32.DeleteDC(mem_dc)
                self.user32.ReleaseDC(hwnd, hwnd_dc)
                return None
            
            # ビットマップをメモリDCに選択
            self.gdi32.SelectObject(mem_dc, bitmap)
            
            # BitBltでウィンドウをキャプチャ
            if not self.gdi32.BitBlt(
                mem_dc, 0, 0, width, height,
                hwnd_dc, 0, 0, 0x00CC0020  # SRCCOPY
            ):
                self.logger.error("BitBltの実行に失敗しました")
                self.gdi32.DeleteObject(bitmap)
                self.gdi32.DeleteDC(mem_dc)
                self.user32.ReleaseDC(hwnd, hwnd_dc)
                return None
            
            # ビットマップ情報を取得
            bmp_info = self._get_bitmap_info(bitmap)
            if not bmp_info:
                self.gdi32.DeleteObject(bitmap)
                self.gdi32.DeleteDC(mem_dc)
                self.user32.ReleaseDC(hwnd, hwnd_dc)
                return None
            
            # ピクセルデータを取得
            buffer = (c_ubyte * (width * height * 4))()  # RGBA
            if not self.gdi32.GetDIBits(
                mem_dc, bitmap, 0, height,
                byref(buffer), bmp_info, 0  # DIB_RGB_COLORS
            ):
                self.logger.error("ピクセルデータの取得に失敗しました")
                self.gdi32.DeleteObject(bitmap)
                self.gdi32.DeleteDC(mem_dc)
                self.user32.ReleaseDC(hwnd, hwnd_dc)
                return None
            
            # リソースを解放
            self.gdi32.DeleteObject(bitmap)
            self.gdi32.DeleteDC(mem_dc)
            self.user32.ReleaseDC(hwnd, hwnd_dc)
            
            # numpy配列に変換
            array = np.frombuffer(buffer, dtype=np.uint8)
            array = array.reshape((height, width, 4))  # RGBA
            
            # BGRからRGBに変換
            array = cv2.cvtColor(array, cv2.COLOR_BGRA2RGB)
            
            # PIL Imageに変換
            image = Image.fromarray(array)
            return image
            
        except Exception as e:
            self.logger.error(f"キャプチャ中にエラーが発生しました: {e}", exc_info=True)
            return None
    
    def _get_bitmap_info(self, bitmap: int) -> Optional[object]:
        """ビットマップ情報を取得します。

        Args:
            bitmap: ビットマップハンドル

        Returns:
            Optional[object]: ビットマップ情報オブジェクト。失敗時はNone。
        """
        try:
            from ctypes import Structure, c_long, c_ulong
            
            class BITMAPINFOHEADER(Structure):
                _fields_ = [
                    ("biSize", c_ulong),
                    ("biWidth", c_long),
                    ("biHeight", c_long),
                    ("biPlanes", c_ulong),
                    ("biBitCount", c_ulong),
                    ("biCompression", c_ulong),
                    ("biSizeImage", c_ulong),
                    ("biXPelsPerMeter", c_long),
                    ("biYPelsPerMeter", c_long),
                    ("biClrUsed", c_ulong),
                    ("biClrImportant", c_ulong)
                ]
            
            class BITMAPINFO(Structure):
                _fields_ = [
                    ("bmiHeader", BITMAPINFOHEADER),
                    ("bmiColors", c_ulong * 3)
                ]
            
            # BITMAPINFO構造体を初期化
            bmp_info = BITMAPINFO()
            bmp_header = BITMAPINFOHEADER()
            
            # ヘッダー情報を設定
            bmp_header.biSize = 40  # sizeof(BITMAPINFOHEADER)
            bmp_header.biPlanes = 1
            bmp_header.biBitCount = 32  # RGBA
            bmp_header.biCompression = 0  # BI_RGB
            bmp_info.bmiHeader = bmp_header
            
            # ビットマップの情報を取得
            if not self.gdi32.GetDIBits(
                self.user32.GetDC(0), bitmap,
                0, 0, None, byref(bmp_info), 0  # DIB_RGB_COLORS
            ):
                self.logger.error("ビットマップ情報の取得に失敗しました")
                return None
            
            return bmp_info
            
        except Exception as e:
            self.logger.error(f"ビットマップ情報の取得中にエラーが発生しました: {e}", exc_info=True)
            return None
