import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import Optional
import queue
import time
from src.main import run_main_loop
from src.utils.logging_config import setup_logging
import logging
import os
from pathlib import Path
import tkinter.messagebox as messagebox
from tkinter import ttk
import ctypes
import ctypes.wintypes
from PIL import Image, ImageTk, ImageOps
import cv2
import numpy as np
from src.services.window_capture import WindowCapture
import textwrap
from tkinter import filedialog
import sys

# グローバル変数の初期化
roi = None  # ROI矩形座標 [x1, y1, x2, y2]
ocr_preview_img = None  # OCRプレビュー用画像を保持

# 省略表示用関数を追加
MAX_TITLE_DISPLAY_LENGTH = 24  # 表示上限（全角換算で調整可）
def ellipsize(text: str, max_length: int = MAX_TITLE_DISPLAY_LENGTH) -> str:
    """
    長すぎるテキストを...で省略して返す。
    Args:
        text: 元のテキスト
        max_length: 最大表示文字数
    Returns:
        省略後のテキスト
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'

def main(window_title: Optional[str] = None) -> None:
    """
    Tkinterで実装したOCRテキストライブプレビュー付きGUI。
    - 画面キャプチャとプレビューを常時表示
    - Start/Stopボタンでテキスト認識と読み上げを制御
    - ステータスバーでシステム状態を表示

    Args:
        window_title: 現在ターゲットとなっているウィンドウ名
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    root = tk.Tk()
    root.title('Window Capture Reading')
    root.geometry('900x350')  # 高さを少し拡張
    root.resizable(True, True)
    root.minsize(800, 400)  # より実用的な最小サイズに

    # --- メニューバー追加 ---
    menubar = tk.Menu(root)
    file_menu = tk.Menu(menubar, tearoff=0)

    # デフォルトディレクトリをexeと同じ階層に
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        default_dir = os.path.dirname(sys.executable)
    else:
        default_dir = os.path.abspath(os.path.dirname(__file__))

    def menu_save_config():
        from src.utils.config import Config
        config = Config()
        path = filedialog.asksaveasfilename(
            defaultextension='.json',
            filetypes=[('JSON', '*.json')],
            title='設定ファイルを保存',
            initialdir=default_dir
        )
        if path:
            import json
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(dict(config), f, ensure_ascii=False, indent=2)
    def menu_load_config():
        from src.utils.config import Config, save_config
        path = filedialog.askopenfilename(
            defaultextension='.json',
            filetypes=[('JSON', '*.json')],
            title='設定ファイルを読み込み',
            initialdir=default_dir
        )
        if path:
            import json
            with open(path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            save_config(loaded)
            # 再起動して反映
            root.destroy()
            from src.gui_main import main as gui_main_entry
            main_title = loaded.get('TARGET_WINDOW_TITLE', 'LDPlayer')
            gui_main_entry(window_title=main_title)
    def menu_exit():
        on_exit()
    def menu_settings():
        show_settings_dialog()
    file_menu.add_command(label='設定', command=menu_settings)
    file_menu.add_separator()
    file_menu.add_command(label='終了', command=menu_exit)
    menubar.add_cascade(label='ファイル', menu=file_menu)
    root.config(menu=menubar)

    # フォント設定
    title_font = tkfont.Font(family="Meiryo", size=14)
    status_font = tkfont.Font(family="Meiryo", size=10)
    ocr_font = tkfont.Font(family="Meiryo", size=12)

    # タイトルラベル
    title_var = tk.StringVar()
    display_title = ellipsize(window_title or "(未設定)")
    title_var.set(f'ターゲットウィンドウ: {display_title}')

    # OCRテキスト表示エリア
    ocr_text_var = tk.StringVar()
    ocr_text_var.set('まだテキストは検出されていません')

    # ステータスバー
    status_var = tk.StringVar()
    status_var.set('Stopped')
    status_bar = tk.Label(root, textvariable=status_var, font=status_font, bd=1, relief=tk.SUNKEN, anchor='w', bg='#f0f0f0')
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # スレッド制御用
    running = threading.Event()
    running.clear()
    ocr_text_queue = queue.Queue()
    ocr_thread = None
    capture_thread = None  # キャプチャスレッド用
    capture_running = threading.Event()  # キャプチャ制御用
    capture_running.set()  # キャプチャは常時実行

    # --- レイアウトの土台だけ先に作る ---
    main_frame = tk.Frame(root)
    main_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
    left_frame = tk.Frame(main_frame, width=450)
    left_frame.pack(side='left', fill='both', expand=True)
    right_frame = tk.Frame(main_frame, width=420)
    right_frame.pack(side='right', fill='y', expand=False)

    # タイトル・テキストエリア（左側）
    title_label = tk.Label(left_frame, textvariable=title_var, font=title_font, anchor='w', width=38)
    title_label.pack(pady=(20, 10), padx=0, anchor='w')
    title_label.config(wraplength=600)  # タイトルが折り返されるように
    ocr_text_box = tk.Label(left_frame, textvariable=ocr_text_var, font=ocr_font, width=60, height=4, anchor='nw', justify='left', bg='#f8f8f8', relief=tk.SUNKEN, bd=1)
    ocr_text_box.pack(pady=(0, 10), padx=0, fill='x')
    ocr_text_box.config(wraplength=600)

    # --- OCRプレビューとボタンを横並びにする行フレーム ---
    content_row = tk.Frame(left_frame)
    content_row.pack(pady=(0, 10), padx=0, fill='both', expand=True)

    # OCRプレビュー（左）: タイトル付きで大きく
    ocr_preview_frame = tk.LabelFrame(content_row, text='OCRプレビュー', labelanchor='n', font=ocr_font, bg='#f8f8ff')
    ocr_preview_frame.pack(side='left', fill='both', expand=True, padx=(0, 16), pady=0)

    # --- OCRプレビューCanvas ---
    OCR_CANVAS_W, OCR_CANVAS_H = 320, 240
    ocr_canvas = tk.Canvas(ocr_preview_frame, width=OCR_CANVAS_W, height=OCR_CANVAS_H, bg='#fff', relief=tk.SUNKEN, bd=1, highlightthickness=0)
    ocr_canvas.pack(fill='both', expand=True, padx=12, pady=(12, 0))
    ocr_canvas_img = None
    ocr_canvas_img_obj = None
    ocr_canvas_zoom = 1.0
    ocr_canvas_pan = [0, 0]
    ocr_canvas_dragging = False
    ocr_canvas_drag_start = [0, 0]

    def draw_ocr_canvas_img(img: Image.Image):
        nonlocal ocr_canvas_img, ocr_canvas_img_obj
        # ズーム・パンを反映して表示
        canvas_w = ocr_canvas.winfo_width() or OCR_CANVAS_W
        canvas_h = ocr_canvas.winfo_height() or OCR_CANVAS_H
        zoom = ocr_canvas_zoom
        disp_w, disp_h = int(img.width * zoom), int(img.height * zoom)
        img_disp = img.resize((disp_w, disp_h), Image.LANCZOS)
        # パン（中央基準）
        x_offset = (canvas_w - disp_w) // 2 + ocr_canvas_pan[0]
        y_offset = (canvas_h - disp_h) // 2 + ocr_canvas_pan[1]
        ocr_canvas.delete('all')
        ocr_canvas_img = ImageTk.PhotoImage(img_disp)
        ocr_canvas_img_obj = ocr_canvas.create_image(x_offset, y_offset, anchor='nw', image=ocr_canvas_img)

    # --- ズーム操作（マウスホイール） ---
    def on_ocr_canvas_zoom(event):
        nonlocal ocr_canvas_zoom
        if event.delta > 0:
            ocr_canvas_zoom = min(ocr_canvas_zoom + 0.1, 3.0)
        else:
            ocr_canvas_zoom = max(ocr_canvas_zoom - 0.1, 0.5)
        if ocr_preview_img is not None:
            draw_ocr_canvas_img(ocr_preview_img)
    ocr_canvas.bind('<MouseWheel>', on_ocr_canvas_zoom)
    # Linux/Mac用
    ocr_canvas.bind('<Button-4>', lambda e: (setattr(ocr_canvas_zoom, '__iadd__', 0.1), draw_ocr_canvas_img(ocr_preview_img) if ocr_preview_img is not None else None))
    ocr_canvas.bind('<Button-5>', lambda e: (setattr(ocr_canvas_zoom, '__isub__', 0.1), draw_ocr_canvas_img(ocr_preview_img) if ocr_preview_img is not None else None))

    # --- パン操作（右クリックドラッグ） ---
    def on_ocr_canvas_pan_start(event):
        nonlocal ocr_canvas_dragging, ocr_canvas_drag_start
        ocr_canvas_dragging = True
        ocr_canvas_drag_start = [event.x, event.y]
    def on_ocr_canvas_pan_drag(event):
        nonlocal ocr_canvas_dragging, ocr_canvas_drag_start, ocr_canvas_pan
        if ocr_canvas_dragging:
            dx = event.x - ocr_canvas_drag_start[0]
            dy = event.y - ocr_canvas_drag_start[1]
            ocr_canvas_pan[0] += dx
            ocr_canvas_pan[1] += dy
            ocr_canvas_drag_start = [event.x, event.y]
            if ocr_preview_img is not None:
                draw_ocr_canvas_img(ocr_preview_img)
    def on_ocr_canvas_pan_end(event):
        nonlocal ocr_canvas_dragging
        ocr_canvas_dragging = False
    # 左クリックバインドを削除し、右クリックに変更
    ocr_canvas.unbind('<ButtonPress-1>')
    ocr_canvas.unbind('<B1-Motion>')
    ocr_canvas.unbind('<ButtonRelease-1>')
    ocr_canvas.bind('<ButtonPress-3>', on_ocr_canvas_pan_start)
    ocr_canvas.bind('<B3-Motion>', on_ocr_canvas_pan_drag)
    ocr_canvas.bind('<ButtonRelease-3>', on_ocr_canvas_pan_end)

    # --- ボタン（右）: 右端に縦並びで固定 ---
    button_frame = tk.Frame(content_row)
    button_frame.pack(side='right', fill='y', padx=(0, 8), pady=0)

    # --- コールバック関数をここで定義 ---
    def on_start() -> None:
        nonlocal ocr_thread
        if not ocr_thread:
            running.set()
            ocr_thread = threading.Thread(target=ocr_loop, daemon=True)
            ocr_thread.start()
            set_status('Running')
            start_button.config(state=tk.DISABLED)
            stop_button.config(state=tk.NORMAL)

    def on_stop() -> None:
        running.clear()
        set_status('Stopped')
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)

    def on_capture_ocr() -> None:
        from src.services.ocr_service import OCRService
        from src.utils.config import Config
        config = Config()
        window_name = window_title or config.get("TARGET_WINDOW_TITLE", "LDPlayer")
        window_capture = WindowCapture(window_name)
        ocr_service = OCRService(config)
        frame = window_capture.capture()
        if frame is not None:
            frame = frame.transpose(Image.FLIP_TOP_BOTTOM)
            crop_img = frame
            roi_now = roi if roi is not None else None
            if roi_now is not None:
                x1, y1, x2, y2 = [int(round(v)) for v in roi_now]
                x1 = max(0, min(x1, frame.width-1))
                y1 = max(0, min(y1, frame.height-1))
                x2 = max(0, min(x2, frame.width))
                y2 = max(0, min(y2, frame.height))
                if x2 > x1 and y2 > y1:
                    crop_img = frame.crop((x1, y1, x2, y2))
            text = ocr_service.extract_text(crop_img)
            ocr_text_var.set(text or 'まだテキストは検出されていません')
        else:
            messagebox.showerror('エラー', 'ウィンドウキャプチャに失敗しました')

    def on_exit() -> None:
        running.clear()
        capture_running.clear()
        if ocr_thread:
            ocr_thread.join(timeout=1.0)
        if capture_thread:
            capture_thread.join(timeout=1.0)
        root.quit()

    # --- ここでボタンを生成 ---
    start_button = tk.Button(button_frame, text='Start', width=12, height=2, command=on_start)
    start_button.pack(pady=(0, 12), anchor='n')
    stop_button = tk.Button(button_frame, text='Stop', width=12, height=2, command=on_stop, state=tk.DISABLED)
    stop_button.pack(pady=(0, 12), anchor='n')
    capture_ocr_button = tk.Button(button_frame, text='読み取り', width=12, height=2, command=on_capture_ocr)
    capture_ocr_button.pack(pady=(0, 12), anchor='n')

    # プレビューCanvas（右側）
    preview_canvas = tk.Canvas(right_frame, bg='#222')
    preview_canvas.pack(fill='both', expand=True, pady=(30, 0))
    zoom_var = tk.DoubleVar(value=1.0)

    # ROIハンドルサイズ
    HANDLE_SIZE = 8
    handle_ids = [None, None, None, None]  # 左上, 右上, 右下, 左下
    active_handle = None

    pan_offset = [0, 0]
    pan_dragging = False
    pan_start = [0, 0]

    # ズーム倍率の最小値を「全体fit」に自動調整
    min_zoom = [1.0]  # リストで可変参照

    def update_min_zoom():
        if hasattr(on_zoom_change, 'last_img') and on_zoom_change.last_img is not None:
            frame_img = on_zoom_change.last_img
            img_width, img_height = frame_img.width, frame_img.height
            canvas_w = preview_canvas.winfo_width()
            canvas_h = preview_canvas.winfo_height()
            if canvas_w < 10 or canvas_h < 10:
                canvas_w, canvas_h = 400, 220
            fit_zoom = min(canvas_w / img_width, canvas_h / img_height)
            min_zoom[0] = fit_zoom
            if zoom_var.get() < fit_zoom:
                zoom_var.set(fit_zoom)
            zoom_slider.config(from_=fit_zoom)

    def clamp_pan_offset(canvas_w, canvas_h, disp_w, disp_h):
        # 画像がCanvasより小さい場合は中央揃え
        if disp_w <= canvas_w:
            pan_offset[0] = 0
        else:
            min_x = -(disp_w - canvas_w) // 2
            max_x = (disp_w - canvas_w) // 2
            pan_offset[0] = max(min_x, min(pan_offset[0], max_x))
        if disp_h <= canvas_h:
            pan_offset[1] = 0
        else:
            min_y = -(disp_h - canvas_h) // 2
            max_y = (disp_h - canvas_h) // 2
            pan_offset[1] = max(min_y, min(pan_offset[1], max_y))

    # ROIは常に元画像座標系で保持
    dragging = False
    drag_offset = (0, 0)
    img_width = None
    img_height = None

    def image_to_canvas(x, y):
        """画像座標→Canvas座標"""
        canvas_w = preview_canvas.winfo_width()
        canvas_h = preview_canvas.winfo_height()
        scale = min(canvas_w / img_width, canvas_h / img_height) * zoom_var.get()
        x_offset = (canvas_w - img_width * scale) // 2 + pan_offset[0]
        y_offset = (canvas_h - img_height * scale) // 2 + pan_offset[1]
        return x * scale + x_offset, y * scale + y_offset

    def canvas_to_image(x, y):
        """Canvas座標→画像座標"""
        canvas_w = preview_canvas.winfo_width()
        canvas_h = preview_canvas.winfo_height()
        scale = min(canvas_w / img_width, canvas_h / img_height) * zoom_var.get()
        x_offset = (canvas_w - img_width * scale) // 2 + pan_offset[0]
        y_offset = (canvas_h - img_height * scale) // 2 + pan_offset[1]
        return (x - x_offset) / scale, (y - y_offset) / scale

    def draw_preview_with_roi(frame_img: Image.Image) -> None:
        global roi
        nonlocal preview_img_on_canvas, roi_rect, preview_img_ref, img_width, img_height, handle_ids
        img = frame_img.transpose(Image.FLIP_TOP_BOTTOM)
        on_zoom_change.last_img = frame_img
        img_width, img_height = img.width, img.height
        canvas_w = preview_canvas.winfo_width()
        canvas_h = preview_canvas.winfo_height()
        if canvas_w < 10 or canvas_h < 10:
            canvas_w, canvas_h = 400, 220
        update_min_zoom()
        zoom = zoom_var.get()
        scale = min(canvas_w / img_width, canvas_h / img_height) * zoom
        disp_w, disp_h = int(img_width * scale), int(img_height * scale)
        clamp_pan_offset(canvas_w, canvas_h, disp_w, disp_h)
        img_disp = img.resize((disp_w, disp_h), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(img_disp)
        preview_canvas.delete('all')
        x_offset = (canvas_w - disp_w) // 2 + pan_offset[0]
        y_offset = (canvas_h - disp_h) // 2 + pan_offset[1]
        preview_img_on_canvas = preview_canvas.create_image(x_offset, y_offset, anchor='nw', image=tk_img)
        preview_img_ref = tk_img
        if roi is None:
            # 初期ROIは画像座標系で設定
            roi = [int(img_width*0.1), int(img_height*0.1), int(img_width*0.6), int(img_height*0.5)]
        # ROIの正規化と最新化
        x1, y1, x2, y2 = roi
        roi = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
        cx1, cy1 = image_to_canvas(roi[0], roi[1])
        cx2, cy2 = image_to_canvas(roi[2], roi[3])
        roi_rect = preview_canvas.create_rectangle(cx1, cy1, cx2, cy2, outline='red', width=2)
        handle_coords = [
            (cx1, cy1),
            (cx2, cy1),
            (cx2, cy2),
            (cx1, cy2),
        ]
        for i, (hx, hy) in enumerate(handle_coords):
            handle_ids[i] = preview_canvas.create_rectangle(
                hx - HANDLE_SIZE//2, hy - HANDLE_SIZE//2, hx + HANDLE_SIZE//2, hy + HANDLE_SIZE//2,
                fill='white', outline='black')
        # ROIをグローバルに最新化
        # globals()['roi'] = roi  # 旧方式

    def get_handle_at(x, y):
        # どのハンドルがクリックされたか判定（Canvas座標）
        for i, hid in enumerate(handle_ids):
            coords = preview_canvas.coords(hid)
            if coords and coords[0] <= x <= coords[2] and coords[1] <= y <= coords[3]:
                return i
        return None

    def on_canvas_press(event):
        nonlocal dragging, drag_offset, active_handle
        x, y = event.x, event.y
        handle = get_handle_at(x, y)
        if handle is not None:
            active_handle = handle
            dragging = True
        else:
            # ROI内クリックでドラッグ開始（Canvas→画像座標で判定）
            x1, y1, x2, y2 = roi
            ix, iy = canvas_to_image(x, y)
            if x1 <= ix <= x2 and y1 <= iy <= y2:
                dragging = True
                drag_offset = (ix - x1, iy - y1)
                active_handle = None

    def on_canvas_drag(event):
        global roi
        nonlocal dragging, active_handle
        if not dragging:
            return
        x, y = event.x, event.y
        x1, y1, x2, y2 = roi
        ix, iy = canvas_to_image(x, y)
        if active_handle is not None:
            # ハンドルでリサイズ（画像座標系で）
            if active_handle == 0:  # 左上
                roi = [ix, iy, x2, y2]
            elif active_handle == 1:  # 右上
                roi = [x1, iy, ix, y2]
            elif active_handle == 2:  # 右下
                roi = [x1, y1, ix, iy]
            elif active_handle == 3:  # 左下
                roi = [ix, y1, x2, iy]
            # 座標の正規化（x1<x2, y1<y2）
            x1, y1, x2, y2 = roi
            roi = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
        else:
            # ROI全体を移動（画像座標系で）
            dx, dy = drag_offset
            w, h = x2 - x1, y2 - y1
            nx1 = max(0, min(ix - dx, img_width - w))
            ny1 = max(0, min(iy - dy, img_height - h))
            roi = [nx1, ny1, nx1 + w, ny1 + h]
        draw_preview_with_roi(on_zoom_change.last_img)

    def on_canvas_release(event):
        nonlocal dragging, active_handle
        dragging = False
        active_handle = None
        # TODO: ROI座標を設定ファイルに保存

    preview_canvas.bind('<ButtonPress-1>', on_canvas_press)
    preview_canvas.bind('<B1-Motion>', on_canvas_drag)
    preview_canvas.bind('<ButtonRelease-1>', on_canvas_release)

    # --- ズームスライダーで必ず再描画
    def on_zoom_change(event=None):
        if hasattr(on_zoom_change, 'last_img') and on_zoom_change.last_img is not None:
            update_min_zoom()
            frame_img = on_zoom_change.last_img
            img_width, img_height = frame_img.width, frame_img.height
            canvas_w = preview_canvas.winfo_width()
            canvas_h = preview_canvas.winfo_height()
            zoom = zoom_var.get()
            scale = min(canvas_w / img_width, canvas_h / img_height) * zoom
            disp_w, disp_h = int(img_width * scale), int(img_height * scale)
            clamp_pan_offset(canvas_w, canvas_h, disp_w, disp_h)
            draw_preview_with_roi(frame_img)
    zoom_slider = tk.Scale(right_frame, from_=0.2, to=4.0, resolution=0.05, orient='horizontal', label='ズーム', variable=zoom_var, command=on_zoom_change)
    zoom_slider.pack(pady=(0, 10), fill='x')
    on_zoom_change.last_img = None

    preview_img_ref = None
    preview_img_on_canvas = None
    roi_rect = None

    # --- ズーム・パン操作時に即時再描画 ---
    def on_mouse_wheel(event):
        max_zoom = zoom_slider.cget('to')
        if event.delta > 0:
            zoom_var.set(min(zoom_var.get() + 0.1, max_zoom))
        else:
            zoom_var.set(max(zoom_var.get() - 0.1, 0.2))
        on_zoom_change()
    preview_canvas.bind('<MouseWheel>', on_mouse_wheel)
    preview_canvas.bind('<Button-4>', lambda e: (zoom_var.set(min(zoom_var.get() + 0.1, zoom_slider.cget('to'))), on_zoom_change()))
    preview_canvas.bind('<Button-5>', lambda e: (zoom_var.set(max(zoom_var.get() - 0.1, 0.2)), on_zoom_change()))

    def on_pan_start(event):
        nonlocal pan_dragging, pan_start
        pan_dragging = True
        pan_start = [event.x, event.y]

    def on_pan_drag(event):
        nonlocal pan_dragging, pan_start
        if pan_dragging and zoom_var.get() > min_zoom[0] + 1e-4:
            dx = event.x - pan_start[0]
            dy = event.y - pan_start[1]
            pan_offset[0] += dx
            pan_offset[1] += dy
            pan_start[0], pan_start[1] = event.x, event.y
            if hasattr(on_zoom_change, 'last_img') and on_zoom_change.last_img is not None:
                frame_img = on_zoom_change.last_img
                img_width, img_height = frame_img.width, frame_img.height
                canvas_w = preview_canvas.winfo_width()
                canvas_h = preview_canvas.winfo_height()
                zoom = zoom_var.get()
                scale = min(canvas_w / img_width, canvas_h / img_height) * zoom
                disp_w, disp_h = int(img_width * scale), int(img_height * scale)
                clamp_pan_offset(canvas_w, canvas_h, disp_w, disp_h)
                draw_preview_with_roi(frame_img)

    def on_pan_end(event):
        nonlocal pan_dragging
        pan_dragging = False

    preview_canvas.bind('<ButtonPress-3>', on_pan_start)
    preview_canvas.bind('<B3-Motion>', on_pan_drag)
    preview_canvas.bind('<ButtonRelease-3>', on_pan_end)

    # --- レイアウトの最小サイズ・レスポンシブ化 ---
    root.minsize(800, 400)  # より実用的な最小サイズに
    title_label.config(wraplength=600)  # タイトルが折り返されるように
    ocr_text_box.config(wraplength=600)
    # フレームのpackにexpand, fillを追加
    main_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
    left_frame.pack(side='left', fill='both', expand=True)
    right_frame.pack(side='right', fill='y', expand=False)
    # OCRプレビューのフレームも拡張
    ocr_preview_frame.pack(side='left', fill='both', expand=True, padx=(0, 16), pady=0)
    ocr_canvas.pack(fill='both', expand=True, padx=12, pady=(12, 0))
    # ボタンフレームも余白を調整
    button_frame.pack(side='right', fill='y', padx=(0, 8), pady=0)
    # preview_canvasも拡張
    preview_canvas.pack(fill='both', expand=True, pady=(30, 0))

    def set_status(state: str) -> None:
        """ステータスバーの状態とスタイルを更新"""
        status_var.set(state)
        if state == 'Running':
            status_bar.config(bg='#e6ffe6')  # 薄緑
        elif state == 'Stopped':
            status_bar.config(bg='#ffe6e6')  # 薄赤
        else:
            status_bar.config(bg='#f0f0f0')  # デフォルト
        status_bar.update()

    def capture_loop():
        """画面キャプチャとプレビュー表示を行うループ"""
        global roi
        nonlocal capture_thread
        from src.utils.config import Config
        window_capture = None
        logger.info("キャプチャループを開始")
        try:
            while capture_running.is_set():
                config = Config()
                window_name = config.get("TARGET_WINDOW_TITLE", "LDPlayer")
                capture_interval = 1.0
                try:
                    capture_interval = float(config.get("CAPTURE_INTERVAL", "1.0"))
                except Exception:
                    pass
                if window_capture is None or window_capture.window_title != window_name:
                    from src.services.window_capture import WindowCapture
                    window_capture = WindowCapture(window_name)
                frame = window_capture.capture()
                if frame is None:
                    logger.warning("キャプチャ画像が取得できませんでした（Noneが返却されました）")
                    time.sleep(0.2)
                    continue
                frame_pil = None
                if isinstance(frame, np.ndarray):
                    try:
                        frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    except Exception as e:
                        logger.error(f"キャプチャ画像の変換に失敗: {e}", exc_info=True)
                        time.sleep(0.2)
                        continue
                elif isinstance(frame, Image.Image):
                    frame_pil = frame
                else:
                    logger.warning(f"キャプチャ画像の型が不正です: {type(frame)}")
                    time.sleep(0.2)
                    continue
                root.after(0, lambda: draw_preview_with_roi(frame_pil))
                # --- OCR前処理プレビューも常時表示（ROIでクロップ） ---
                try:
                    # 画像を上下反転（OCRループと同じ処理）
                    frame_flipped = frame_pil.transpose(Image.FLIP_TOP_BOTTOM)
                    # ROIでクロップ
                    crop_img = frame_flipped
                    roi_now = roi if roi is not None else None
                    if roi_now is not None:
                        x1, y1, x2, y2 = [int(round(v)) for v in roi_now]
                        x1 = max(0, min(x1, frame_flipped.width-1))
                        y1 = max(0, min(y1, frame_flipped.height-1))
                        x2 = max(0, min(x2, frame_flipped.width))
                        y2 = max(0, min(y2, frame_flipped.height))
                        if x2 > x1 and y2 > y1:
                            crop_img = frame_flipped.crop((x1, y1, x2, y2))
                    # クロップした画像を処理（グレースケール・二値化）
                    frame_cv = np.array(crop_img)
                    if frame_cv.ndim == 3:
                        gray = cv2.cvtColor(frame_cv, cv2.COLOR_RGB2GRAY)
                    else:
                        gray = frame_cv
                    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    thresh_rgb = cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)
                    thresh_pil = Image.fromarray(thresh_rgb)
                    thresh_pil.thumbnail((200, 200), Image.LANCZOS)
                    global ocr_preview_img
                    ocr_preview_img = thresh_pil
                    root.after(0, lambda img=ocr_preview_img: draw_ocr_canvas_img(img))
                except Exception as e:
                    logger.error(f"OCRプレビュー画像の生成に失敗: {e}", exc_info=True)
                time.sleep(capture_interval)
        except Exception as e:
            logger.error(f"キャプチャループでエラー発生: {e}", exc_info=True)
        finally:
            logger.info("キャプチャループを終了")
            capture_thread = None

    def ocr_loop():
        """OCRと読み上げを行うループ"""
        global roi
        nonlocal ocr_thread
        from src.utils.config import Config
        from src.services.ocr_service import OCRService
        from src.services.bouyomi_client import BouyomiClient
        window_capture = None
        ocr_service = None
        bouyomi_client = None
        last_text = ''
        logger.info("OCRループを開始")
        try:
            while running.is_set():
                config = Config()
                window_name = config.get("TARGET_WINDOW_TITLE", "LDPlayer")
                if window_capture is None or window_capture.window_title != window_name:
                    from src.services.window_capture import WindowCapture
                    window_capture = WindowCapture(window_name)
                if ocr_service is None or ocr_service.config.get("TARGET_WINDOW_TITLE") != window_name:
                    ocr_service = OCRService(config)
                bouyomi_enabled = str(config.get("BOUYOMI_ENABLED", "true")).lower() == "true"
                if bouyomi_enabled and (bouyomi_client is None or bouyomi_client.config.get("BOUYOMI_PORT") != config.get("BOUYOMI_PORT")):
                    bouyomi_client = BouyomiClient(config)
                frame = window_capture.capture()
                if frame is None:
                    logger.warning("OCR用キャプチャ画像が取得できませんでした（Noneが返却されました）")
                    time.sleep(0.2)
                    continue
                frame_pil = None
                if isinstance(frame, np.ndarray):
                    try:
                        frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    except Exception as e:
                        logger.error(f"OCR用画像の変換に失敗: {e}", exc_info=True)
                        time.sleep(0.2)
                        continue
                elif isinstance(frame, Image.Image):
                    frame_pil = frame
                else:
                    logger.warning(f"OCR用キャプチャ画像の型が不正です: {type(frame)}")
                    time.sleep(0.2)
                    continue
                frame_pil = frame_pil.transpose(Image.FLIP_TOP_BOTTOM)
                crop_img = frame_pil
                roi_now = roi if roi is not None else None
                if roi_now is not None:
                    x1, y1, x2, y2 = [int(round(v)) for v in roi_now]
                    x1 = max(0, min(x1, frame_pil.width-1))
                    y1 = max(0, min(y1, frame_pil.height-1))
                    x2 = max(0, min(x2, frame_pil.width))
                    y2 = max(0, min(y2, frame_pil.height))
                    if x2 > x1 and y2 > y1:
                        crop_img = frame_pil.crop((x1, y1, x2, y2))
                try:
                    text = ocr_service.extract_text(crop_img)
                    if text and text != last_text:
                        ocr_text_queue.put(text)
                        last_text = text
                        if bouyomi_enabled and bouyomi_client is not None:
                            try:
                                bouyomi_client.talk(text)
                                logger.info(f"棒読みちゃんで読み上げ: {text}")
                            except Exception as e:
                                logger.error(f"棒読みちゃん読み上げエラー: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"OCR処理でエラー: {e}", exc_info=True)
                time.sleep(0.5)
        except Exception as e:
            logger.error(f"OCRループでエラー発生: {e}", exc_info=True)
        finally:
            if bouyomi_client is not None:
                try:
                    bouyomi_client.close()
                    logger.info("BouyomiClientをクローズしました（GUI）")
                except Exception as e:
                    logger.error(f"BouyomiClientのクローズに失敗: {e}", exc_info=True)
            logger.info("OCRループを終了")
            ocr_thread = None
            set_status('Stopped')

    def update_ocr_text():
        """OCRテキストのライブ更新処理（Tkinterのafterで定期実行）。"""
        try:
            while True:
                text = ocr_text_queue.get_nowait()
                ocr_text_var.set(text)
        except queue.Empty:
            pass
        # テキストが空の場合はプレースホルダー
        if not ocr_text_var.get():
            ocr_text_var.set('まだテキストは検出されていません')
        root.after(300, update_ocr_text)

    def get_window_titles() -> list[str]:
        """
        現在表示中のウィンドウタイトル一覧を取得します。
        Returns:
            list[str]: ウィンドウタイトルのリスト
        """
        titles = []
        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
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

    def show_settings_dialog() -> None:
        """
        簡易設定パネル（ダイアログ）を表示し、主要な設定値を編集できるようにする。
        設定変更時は.envファイルを直接書き換える。
        """
        from src.utils.config import Config
        config = Config()
        window_titles = get_window_titles()
        settings_keys = [
            ("TARGET_WINDOW_TITLE", "ウィンドウタイトル", config.get("TARGET_WINDOW_TITLE", "LDPlayer")),
            ("CAPTURE_INTERVAL", "キャプチャ間隔（秒）", config.get("CAPTURE_INTERVAL", "1.0")),
            ("BOUYOMI_PORT", "棒読みちゃんポート", config.get("BOUYOMI_PORT", "50001")),
            ("BOUYOMI_VOICE_TYPE", "棒読みちゃん声質", config.get("BOUYOMI_VOICE_TYPE", "0")),
        ]
        dialog = tk.Toplevel(root)
        dialog.title('設定')
        dialog.geometry('400x320')
        dialog.resizable(False, False)
        entries = {}
        for i, (key, label, value) in enumerate(settings_keys):
            tk.Label(dialog, text=label, anchor='w').grid(row=i, column=0, padx=10, pady=8, sticky='w')
            if key == "TARGET_WINDOW_TITLE":
                combo = ttk.Combobox(dialog, values=window_titles, width=38, state="readonly")  # 幅を広げる
                combo.set(value)
                combo.grid(row=i, column=1, padx=10, pady=8)
                entries[key] = combo
            else:
                entry = tk.Entry(dialog, width=30)
                entry.insert(0, value)
                entry.grid(row=i, column=1, padx=10, pady=8)
                entries[key] = entry
        def on_save():
            nonlocal capture_thread, ocr_thread
            for key, _, _ in settings_keys:
                config[key] = entries[key].get()
            config.save()
            # タイトルラベルを即時更新（省略処理付き）
            display_title = ellipsize(config.get("TARGET_WINDOW_TITLE", "(未設定)"))
            title_var.set(f'ターゲットウィンドウ: {display_title}')
            # OCR・キャプチャスレッドを再起動して設定を即時反映
            on_stop()
            # キャプチャスレッド再起動
            if capture_thread is None:
                capture_running.set()
                capture_thread = threading.Thread(target=capture_loop, daemon=True)
                capture_thread.start()
            # OCRスレッド再起動（Startボタンが有効な場合のみ）
            if ocr_thread is None and running.is_set():
                ocr_thread = threading.Thread(target=ocr_loop, daemon=True)
                ocr_thread.start()
            dialog.destroy()
        def on_cancel():
            dialog.destroy()
        save_btn = tk.Button(dialog, text='保存', width=10, command=on_save)
        save_btn.grid(row=len(settings_keys), column=0, padx=10, pady=20)
        cancel_btn = tk.Button(dialog, text='キャンセル', width=10, command=on_cancel)
        cancel_btn.grid(row=len(settings_keys), column=1, padx=10, pady=20)

    # キャプチャスレッドを開始
    capture_thread = threading.Thread(target=capture_loop, daemon=True)
    capture_thread.start()

    root.mainloop()


if __name__ == '__main__':
    main(window_title="LDPlayer")
