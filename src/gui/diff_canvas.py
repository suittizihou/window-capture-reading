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

        # コントロールフレームの作成
        self.control_frame = ttk.Frame(master)
        self.control_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.control_frame.grid_columnconfigure(0, weight=1)

        # ズーム関連の変数
        self.zoom_var = tk.DoubleVar(value=1.0)
        self.zoom_scale = ttk.Scale(
            self.control_frame,
            from_=0.1,
            to=5.0,
            orient="horizontal",
            variable=self.zoom_var,
            length=150,
        )
        self.zoom_scale.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # リセットボタン
        self.reset_button = ttk.Button(self.control_frame, text="リセット", command=self.reset_view)
        self.reset_button.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        # パン関連の変数
        self.pan_offset = [0, 0]  # [x, y]
        self.is_panning = False
        self.pan_start = [0, 0]  # [x, y]

        # 最小ズーム倍率
        self.min_zoom = 1.0

        # イベントバインド
        self.bind("<ButtonPress-1>", self._on_pan_start)
        self.bind("<B1-Motion>", self._on_pan_drag)
        self.bind("<ButtonRelease-1>", self._on_pan_end)
        self.bind("<MouseWheel>", self._on_mouse_wheel)  # Windows
        self.bind("<Button-4>", self._on_mouse_wheel)  # Linux上スクロール
        self.bind("<Button-5>", self._on_mouse_wheel)  # Linux下スクロール
        self.zoom_var.trace_add("write", lambda *args: self._on_zoom_change())

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
        self.zoom_var.set(1.0)
        self.min_zoom = 1.0

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

    def reset_view(self) -> None:
        """表示をリセットします。"""
        if self.image is not None:
            self.zoom_var.set(self.min_zoom)
            self.pan_offset = [0, 0]
            self.update_image(self.image)

    def _update_min_zoom(self) -> None:
        """最小ズーム倍率を更新します。"""
        if self.image is None or self is None:
            return

        # キャンバスのサイズを取得
        canvas_w = self.winfo_width()
        canvas_h = self.winfo_height()

        # キャンバスのサイズが有効でない場合は遅延更新
        if canvas_w <= 1 or canvas_h <= 1:
            self.after(100, self._update_min_zoom)
            return

        # 画像のサイズを取得
        img_w = self.image.width
        img_h = self.image.height

        # 最小ズーム倍率を計算（キャンバスに収まる最大サイズ）
        self.min_zoom = min(canvas_w / img_w, canvas_h / img_h)

    def _on_zoom_change(self, *args: Any) -> None:
        """ズーム変更時の処理。"""
        if self.image is not None:
            self.update_image(self.image)

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        """マウスホイール操作時の処理。

        Args:
            event: イベントオブジェクト
        """
        if self.image is None:
            return

        # 現在のズーム倍率を取得
        current_zoom = self.zoom_var.get()

        # ズーム量の計算
        if (
            hasattr(event, "num")
            and event.num == 4
            or hasattr(event, "delta")
            and event.delta > 0
        ):
            # ズームイン
            new_zoom = min(current_zoom * 1.1, 5.0)
        elif (
            hasattr(event, "num")
            and event.num == 5
            or hasattr(event, "delta")
            and event.delta < 0
        ):
            # ズームアウト
            new_zoom = max(current_zoom / 1.1, self.min_zoom)
        else:
            return

        # ズーム倍率を設定
        self.zoom_var.set(new_zoom)

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

    def _clamp_pan_offset(
        self, canvas_w: int, canvas_h: int, disp_w: int, disp_h: int
    ) -> None:
        """パンオフセットを制限します。

        Args:
            canvas_w: キャンバスの幅
            canvas_h: キャンバスの高さ
            disp_w: 表示画像の幅
            disp_h: 表示画像の高さ
        """
        # パンの制限を計算
        max_x = max(0, (disp_w - canvas_w) // 2)
        max_y = max(0, (disp_h - canvas_h) // 2)

        # パンオフセットを制限
        self.pan_offset[0] = max(-max_x, min(max_x, self.pan_offset[0]))
        self.pan_offset[1] = max(-max_y, min(max_y, self.pan_offset[1]))
