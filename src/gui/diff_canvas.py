"""差分キャンバスモジュール。

差分表示用キャンバスの機能を提供します。
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple, List, Callable, Any, cast
from PIL import Image, ImageTk
import numpy as np
import logging

class DiffCanvas:
    """差分表示用キャンバスクラス。"""

    def __init__(self, parent: tk.Widget) -> None:
        """差分表示用キャンバスを初期化します。

        Args:
            parent: 親ウィジェット
        """
        self.parent = parent
        self.canvas = tk.Canvas(parent, bg="black")
        self.canvas.pack(fill="both", expand=True)
        
        # ズーム関連の変数
        self.zoom_var = tk.DoubleVar(value=1.0)
        self.zoom_scale = ttk.Scale(
            parent,
            from_=0.1,
            to=5.0,
            orient="horizontal",
            variable=self.zoom_var,
            length=150
        )
        self.zoom_scale.pack(side="bottom", fill="x", padx=5, pady=5)
        
        # リセットボタン
        self.reset_button = ttk.Button(parent, text="リセット", command=self.reset_view)
        self.reset_button.pack(side="bottom", fill="x", padx=5, pady=5)
        
        # キャンバス上の画像ID
        self.img_id: Optional[int] = None
        
        # 画像オブジェクト（参照を保持）
        self.img_obj: Optional[ImageTk.PhotoImage] = None
        
        # 表示中の画像（元画像）
        self.current_img: Optional[Image.Image] = None
        
        # パン関連の変数
        self.pan_offset = [0, 0]  # [x, y]
        self.is_panning = False
        self.pan_start = [0, 0]  # [x, y]
        
        # 最小ズーム倍率
        self.min_zoom = 1.0
        
        # イベントバインド
        self.canvas.bind("<ButtonPress-1>", self._on_pan_start)
        self.canvas.bind("<B1-Motion>", self._on_pan_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_pan_end)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)  # Windows
        self.canvas.bind("<Button-4>", self._on_mouse_wheel)    # Linux上スクロール
        self.canvas.bind("<Button-5>", self._on_mouse_wheel)    # Linux下スクロール
        self.zoom_var.trace_add("write", lambda *args: self._on_zoom_change())
        
        # 最初は画像なしの状態
        self.clear()

    def clear(self) -> None:
        """キャンバスをクリアします。"""
        self.canvas.delete("all")
        self.img_id = None
        self.img_obj = None
        self.current_img = None
        self.pan_offset = [0, 0]
        self.is_panning = False
        self.zoom_var.set(1.0)
        self.min_zoom = 1.0

    def set_image(self, img: Image.Image) -> None:
        """画像を設定します。

        Args:
            img: 表示する画像
        """
        self.current_img = img
        self._update_min_zoom()
        
        # 最初は最小ズーム倍率で表示
        self.zoom_var.set(self.min_zoom)
        self.pan_offset = [0, 0]
        
        # 画像を描画
        self._draw_image()

    def reset_view(self) -> None:
        """表示をリセットします。"""
        if self.current_img is not None:
            self.zoom_var.set(self.min_zoom)
            self.pan_offset = [0, 0]
            self._draw_image()

    def _update_min_zoom(self) -> None:
        """最小ズーム倍率を更新します。"""
        if self.current_img is None or self.canvas is None:
            return
            
        # キャンバスのサイズを取得
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        # キャンバスのサイズが有効でない場合は遅延更新
        if canvas_w <= 1 or canvas_h <= 1:
            self.canvas.after(100, self._update_min_zoom)
            return
            
        # 画像のサイズを取得
        img_w = self.current_img.width
        img_h = self.current_img.height
        
        # 最小ズーム倍率を計算（キャンバスに収まる最大サイズ）
        self.min_zoom = min(canvas_w / img_w, canvas_h / img_h)

    def _on_zoom_change(self, *args: Any) -> None:
        """ズーム変更時の処理。"""
        if self.current_img is not None:
            self._draw_image()

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        """マウスホイール操作時の処理。

        Args:
            event: イベントオブジェクト
        """
        if self.current_img is None:
            return
            
        # 現在のズーム倍率を取得
        current_zoom = self.zoom_var.get()
        
        # ズーム量の計算
        if hasattr(event, 'num') and event.num == 4 or hasattr(event, 'delta') and event.delta > 0:
            # ズームイン
            new_zoom = min(current_zoom * 1.1, 5.0)
        elif hasattr(event, 'num') and event.num == 5 or hasattr(event, 'delta') and event.delta < 0:
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
        self._draw_image()

    def _on_pan_end(self, event: tk.Event) -> None:
        """パン終了時の処理。

        Args:
            event: イベントオブジェクト
        """
        self.is_panning = False

    def _clamp_pan_offset(self, canvas_w: int, canvas_h: int, disp_w: int, disp_h: int) -> None:
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

    def _draw_image(self) -> None:
        """画像を描画します。"""
        if self.current_img is None or self.canvas is None:
            return
            
        # キャンバスのサイズを取得
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        # キャンバスのサイズが有効でない場合は遅延更新
        if canvas_w <= 1 or canvas_h <= 1:
            self.canvas.after(100, self._draw_image)
            return
            
        # 画像のサイズを取得
        img_w = self.current_img.width
        img_h = self.current_img.height
        
        # 現在のズーム倍率を取得
        zoom = self.zoom_var.get()
        
        # 表示サイズを計算
        disp_w = int(img_w * zoom)
        disp_h = int(img_h * zoom)
        
        # パンオフセットを制限
        self._clamp_pan_offset(canvas_w, canvas_h, disp_w, disp_h)
        
        # 画像をリサイズ
        resized_img = self.current_img.resize((disp_w, disp_h), Image.LANCZOS)
        
        # 画像オブジェクトを作成（参照を保持）
        self.img_obj = ImageTk.PhotoImage(resized_img)
        
        # 画像を描画（中央に配置）
        center_x = canvas_w // 2 + self.pan_offset[0]
        center_y = canvas_h // 2 + self.pan_offset[1]
        
        # 既存の画像を削除
        if self.img_id is not None:
            self.canvas.delete(self.img_id)
            
        # 新しい画像を描画
        self.img_id = self.canvas.create_image(
            center_x, center_y, 
            image=self.img_obj, 
            anchor="center"
        ) 