"""プレビューキャンバスモジュール。

プレビュー表示用キャンバスの機能を提供します。
"""

import tkinter as tk
from typing import Optional, Tuple, List, Callable, Any, cast
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import logging


class PreviewCanvas(tk.Frame):
    """プレビュー表示用キャンバスクラス。"""

    def __init__(self, parent: tk.Widget) -> None:
        """プレビュー表示用キャンバスを初期化します。

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)

        # キャンバスの作成
        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # フレームの行と列の設定
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # キャンバス上の画像ID
        self.img_id: Optional[int] = None

        # 画像オブジェクト（参照を保持）
        self.img_obj: Optional[ImageTk.PhotoImage] = None

        # 表示中の画像（元画像）
        self.current_img: Optional[Image.Image] = None

        # ROI関連の変数
        self.roi: Optional[List[int]] = None  # [x1, y1, x2, y2]
        self.roi_rect: Optional[int] = None
        self.handle_size = 10
        self.handle_ids: List[int] = []

        # ドラッグ関連の変数
        self.dragging_handle: Optional[int] = None
        self.drag_start: Optional[Tuple[float, float]] = None

        # コールバック関数
        self.on_roi_changed: Optional[Callable[[List[int]], None]] = None

        # イベントバインド
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # 最初は画像なしの状態
        self.clear()

    def clear(self) -> None:
        """キャンバスをクリアします。"""
        self.canvas.delete("all")
        self.img_id = None
        self.img_obj = None
        self.current_img = None
        self.roi = None
        self.roi_rect = None
        self.handle_ids = []

    def set_image(self, img: Image.Image) -> None:
        """画像を設定します。

        Args:
            img: 表示する画像
        """
        self.current_img = img
        self._draw_image()

    def set_roi(self, roi: Optional[List[int]]) -> None:
        """ROIを設定します。

        Args:
            roi: ROI座標 [x1, y1, x2, y2]
        """
        self.roi = roi
        self._draw_image()

    def get_roi(self) -> Optional[List[int]]:
        """現在のROIを取得します。

        Returns:
            ROI座標 [x1, y1, x2, y2]
        """
        return self.roi

    def _draw_image(self) -> None:
        """画像を描画します。"""
        if self.current_img is None:
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

        # スケール係数を計算
        scale = min(canvas_w / img_w, canvas_h / img_h)

        # 表示サイズを計算
        disp_w = int(img_w * scale)
        disp_h = int(img_h * scale)

        # 画像をリサイズ
        resized_img = self.current_img.resize((disp_w, disp_h), Image.LANCZOS)

        # 画像オブジェクトを作成（参照を保持）
        self.img_obj = ImageTk.PhotoImage(resized_img)

        # 既存の要素を削除
        self.canvas.delete("all")

        # 画像を描画（中央に配置）
        x_offset = (canvas_w - disp_w) // 2
        y_offset = (canvas_h - disp_h) // 2

        self.img_id = self.canvas.create_image(
            x_offset, y_offset, image=self.img_obj, anchor="nw"
        )

        # ROIを描画
        if self.roi is not None:
            self._draw_roi(x_offset, y_offset, scale)

    def _draw_roi(self, x_offset: int, y_offset: int, scale: float) -> None:
        """ROIを描画します。

        Args:
            x_offset: X方向オフセット
            y_offset: Y方向オフセット
            scale: スケール係数
        """
        if self.roi is None:
            return

        # 画像座標からキャンバス座標に変換
        x1, y1, x2, y2 = self.roi
        cx1 = x_offset + int(x1 * scale)
        cy1 = y_offset + int(y1 * scale)
        cx2 = x_offset + int(x2 * scale)
        cy2 = y_offset + int(y2 * scale)

        # ROI矩形を描画
        self.roi_rect = self.canvas.create_rectangle(
            cx1, cy1, cx2, cy2, outline="red", width=2
        )

        # ハンドルを描画
        self.handle_ids = []
        handles = [
            (cx1, cy1),  # 左上
            (cx2, cy1),  # 右上
            (cx1, cy2),  # 左下
            (cx2, cy2),  # 右下
        ]

        for i, (hx, hy) in enumerate(handles):
            handle_id = self.canvas.create_rectangle(
                hx - self.handle_size // 2,
                hy - self.handle_size // 2,
                hx + self.handle_size // 2,
                hy + self.handle_size // 2,
                fill="red",
                outline="white",
                width=1,
                tags=f"handle{i}",
            )
            self.handle_ids.append(handle_id)

    def canvas_to_image(self, x: float, y: float) -> Tuple[float, float]:
        """キャンバス座標を画像座標に変換します。

        Args:
            x: キャンバスのX座標
            y: キャンバスのY座標

        Returns:
            画像座標のタプル (x, y)
        """
        if self.current_img is None:
            return (x, y)

        # キャンバスのサイズを取得
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        # 画像のサイズを取得
        img_w = self.current_img.width
        img_h = self.current_img.height

        # スケール係数を計算
        scale = min(canvas_w / img_w, canvas_h / img_h)

        # 画像の表示サイズを計算
        disp_w = int(img_w * scale)
        disp_h = int(img_h * scale)

        # キャンバス中央のオフセットを計算
        x_offset = (canvas_w - disp_w) // 2
        y_offset = (canvas_h - disp_h) // 2

        # キャンバス座標から画像座標に変換
        img_x = (x - x_offset) / scale
        img_y = (y - y_offset) / scale

        return (img_x, img_y)

    def image_to_canvas(self, x: float, y: float) -> Tuple[float, float]:
        """画像座標をキャンバス座標に変換します。

        Args:
            x: 画像のX座標
            y: 画像のY座標

        Returns:
            キャンバス座標のタプル (x, y)
        """
        if self.current_img is None:
            return (x, y)

        # キャンバスのサイズを取得
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        # 画像のサイズを取得
        img_w = self.current_img.width
        img_h = self.current_img.height

        # スケール係数を計算
        scale = min(canvas_w / img_w, canvas_h / img_h)

        # 画像の表示サイズを計算
        disp_w = int(img_w * scale)
        disp_h = int(img_h * scale)

        # キャンバス中央のオフセットを計算
        x_offset = (canvas_w - disp_w) // 2
        y_offset = (canvas_h - disp_h) // 2

        # 画像座標からキャンバス座標に変換
        canvas_x = x_offset + x * scale
        canvas_y = y_offset + y * scale

        return (canvas_x, canvas_y)

    def _get_handle_at(self, x: float, y: float) -> Optional[int]:
        """指定位置のハンドルインデックスを取得します。

        Args:
            x: X座標
            y: Y座標

        Returns:
            ハンドルインデックス（0-3）または None
        """
        for i, handle_id in enumerate(self.handle_ids):
            bbox = self.canvas.bbox(handle_id)
            if bbox is not None:
                x1, y1, x2, y2 = bbox
                if x1 <= x <= x2 and y1 <= y <= y2:
                    return i
        return None

    def _on_canvas_press(self, event: tk.Event) -> None:
        """キャンバスクリック時の処理。

        Args:
            event: イベントオブジェクト
        """
        # ハンドルのヒットテスト
        handle_idx = self._get_handle_at(event.x, event.y)

        if handle_idx is not None:
            # ハンドルをドラッグ開始
            self.dragging_handle = handle_idx
            self.drag_start = (event.x, event.y)
        elif self.roi_rect is not None:
            # ROI矩形内であればROI全体をドラッグ
            bbox = self.canvas.bbox(self.roi_rect)
            if bbox is not None:
                x1, y1, x2, y2 = bbox
                if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                    self.dragging_handle = -1  # 特殊値：ROI全体をドラッグ
                    self.drag_start = (event.x, event.y)
        else:
            # 新しいROIの作成開始
            img_x, img_y = self.canvas_to_image(event.x, event.y)
            # floatをintに安全に変換
            self.roi = [
                int(round(img_x)),
                int(round(img_y)),
                int(round(img_x)),
                int(round(img_y)),
            ]
            self.dragging_handle = 3  # 右下
            self.drag_start = (event.x, event.y)
            self._draw_image()

    def _on_canvas_drag(self, event: tk.Event) -> None:
        """キャンバスドラッグ中の処理。

        Args:
            event: イベントオブジェクト
        """
        if self.dragging_handle is None or self.roi is None or self.drag_start is None:
            return

        # 現在の画像座標を取得
        img_x, img_y = self.canvas_to_image(event.x, event.y)
        x1, y1, x2, y2 = self.roi

        if self.dragging_handle == -1:
            # ROI全体をドラッグ
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]

            # キャンバス座標の差分を画像座標に変換
            img_dx, img_dy = 0.0, 0.0
            if self.current_img is not None:
                canvas_w = self.canvas.winfo_width()
                canvas_h = self.canvas.winfo_height()
                img_w = self.current_img.width
                img_h = self.current_img.height
                scale = min(canvas_w / img_w, canvas_h / img_h)
                img_dx = dx / scale
                img_dy = dy / scale

            # ROIを移動
            self.roi = [
                int(round(x1 + img_dx)),
                int(round(y1 + img_dy)),
                int(round(x2 + img_dx)),
                int(round(y2 + img_dy)),
            ]

            # ドラッグ開始位置を更新
            self.drag_start = (event.x, event.y)
        else:
            # 各ハンドルのドラッグ処理
            if self.dragging_handle == 0:  # 左上
                self.roi = [int(round(img_x)), int(round(img_y)), x2, y2]
            elif self.dragging_handle == 1:  # 右上
                self.roi = [x1, int(round(img_y)), int(round(img_x)), y2]
            elif self.dragging_handle == 2:  # 左下
                self.roi = [int(round(img_x)), y1, x2, int(round(img_y))]
            elif self.dragging_handle == 3:  # 右下
                self.roi = [x1, y1, int(round(img_x)), int(round(img_y))]

        # ROIの正規化（左上-右下の順になるよう調整）
        x1, y1, x2, y2 = self.roi
        self.roi = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]

        # 画像の再描画
        self._draw_image()

    def _on_canvas_release(self, event: tk.Event) -> None:
        """キャンバスリリース時の処理。

        Args:
            event: イベントオブジェクト
        """
        if self.dragging_handle is not None and self.roi is not None:
            # ROIの変更を通知
            if self.on_roi_changed is not None:
                self.on_roi_changed(self.roi)

        # ドラッグ状態をリセット
        self.dragging_handle = None
        self.drag_start = None
