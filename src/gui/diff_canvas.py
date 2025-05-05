"""差分キャンバスモジュール。

差分表示用キャンバスの機能を提供します。
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional, Tuple, List, Callable, Any, cast
from PIL import Image, ImageTk
import numpy as np


class DiffCanvas(tk.Canvas):
    """差分表示用のキャンバスクラス"""

    def __init__(self, master: tk.Widget | None = None, **kwargs) -> None:
        """
        差分表示用のキャンバスを初期化します。

        Args:
            master (tk.Widget | None): 親ウィジェット
            **kwargs: キャンバスの追加設定
        """
        super().__init__(master, **kwargs)
        self.image: Image.Image | None = None
        self.photo_image: ImageTk.PhotoImage | None = None
        self.image_on_canvas: int | None = None
        self.bind("<Configure>", self._on_resize)

        # パン関連の変数
        self.pan_offset = [0, 0]  # [x, y]
        self.is_panning = False
        self.pan_start = [0, 0]  # [x, y]

        # イベントバインド
        self.bind("<ButtonPress-1>", self._on_pan_start)
        self.bind("<B1-Motion>", self._on_pan_drag)
        self.bind("<ButtonRelease-1>", self._on_pan_end)
        
        # マウスホイールイベントは必要ないので削除
        # self.bind("<MouseWheel>", self._on_mouse_wheel)
        # self.bind("<Button-4>", self._on_mouse_wheel)
        # self.bind("<Button-5>", self._on_mouse_wheel)

        # 最初は画像なしの状態
        self.clear()

    def clear(self) -> None:
        """キャンバスをクリアします。"""
        self.delete("all")
        self.image = None
        self.photo_image = None
        self.image_on_canvas = None
        self.pan_offset = [0, 0]
        self.is_panning = False

    def update_image(self, image: Image.Image | None) -> None:
        """
        差分画像を更新します。

        Args:
            image (Image.Image | None): 表示する差分画像
        """
        self.image = image
        if image:
            # キャンバスのサイズに合わせて画像をリサイズ
            canvas_width = self.winfo_width()
            canvas_height = self.winfo_height()

            if canvas_width > 1 and canvas_height > 1:  # 有効なサイズの場合のみ処理
                # アスペクト比を保持してリサイズ
                img_width, img_height = image.size
                scale = min(canvas_width / img_width, canvas_height / img_height)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)

                resized_image = image.resize((new_width, new_height), Image.LANCZOS)

                # PhotoImageを作成して保持（ガベージコレクション対策）
                self.photo_image = ImageTk.PhotoImage(resized_image)

                # 既存の画像を削除
                if self.image_on_canvas is not None:
                    self.delete(self.image_on_canvas)

                # 画像を中央に配置
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                self.image_on_canvas = self.create_image(
                    x, y, anchor="nw", image=self.photo_image
                )
        else:
            # 画像がNoneの場合は表示をクリア
            if self.image_on_canvas is not None:
                self.delete(self.image_on_canvas)
                self.image_on_canvas = None
            self.photo_image = None

    def _on_resize(self, event: tk.Event) -> None:
        """
        キャンバスのリサイズイベントハンドラ

        Args:
            event (tk.Event): リサイズイベント
        """
        if self.image:
            self.update_image(self.image)

    def _on_pan_start(self, event: tk.Event) -> None:
        """パン開始時の処理。

        Args:
            event: イベントオブジェクト
        """
        self.is_panning = True
        self.pan_start = [event.x, event.y]

    def _on_pan_drag(self, event: tk.Event) -> None:
        """パンドラッグ中の処理。

        Args:
            event: イベントオブジェクト
        """
        if not self.is_panning:
            return

        # 移動量の計算
        dx = event.x - self.pan_start[0]
        dy = event.y - self.pan_start[1]

        # パンオフセットを更新
        self.pan_offset[0] += dx
        self.pan_offset[1] += dy

        # パン開始位置を更新
        self.pan_start = [event.x, event.y]

        # 画像を再描画
        self.update_image(self.image)

    def _on_pan_end(self, event: tk.Event) -> None:
        """パン終了時の処理。

        Args:
            event: イベントオブジェクト
        """
        self.is_panning = False
