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
import datetime
from src.utils.config import Config, get_config
from src.services.difference_detector import DifferenceDetector

# グローバル変数の初期化
roi = None  # ROI矩形座標 [x1, y1, x2, y2]
prev_image = None  # 前回のキャプチャ画像
diff_preview_img = None  # 差分プレビュー用画像を保持
detector = None  # 差分検知器

# 省略表示用関数を追加
MAX_TITLE_DISPLAY_LENGTH = 24  # 表示上限（全角換算で調整可）

# 通知音ファイルのパスを取得する関数
def get_sound_file_path() -> str:
    """
    通知音ファイルのパスを返す。exe化された場合とそうでない場合に対応。
    
    Returns:
        str: 通知音ファイルのパス
    """
    # exe化されている場合
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
    else:
        # 通常実行の場合
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    # 通知音ファイルのパス
    sound_path = os.path.join(base_dir, 'resources', 'notification_sound.wav')
    
    return sound_path

# 音声を再生する関数
def play_notification_sound() -> bool:
    """
    通知音を再生する。
    
    Returns:
        bool: 再生に成功した場合はTrue、失敗した場合はFalse
    """
    try:
        import winsound
        sound_path = get_sound_file_path()
        if not os.path.exists(sound_path):
            logging.warning(f"通知音ファイルが見つかりません: {sound_path}")
            return False
            
        winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        return True
    except Exception as e:
        logging.error(f"通知音の再生に失敗しました: {e}")
        return False

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
    Tkinterで実装したGUI。
    - 画面キャプチャとプレビューを常時表示
    - Start/Stopボタンで差分検知と通知を制御
    - ステータスバーでシステム状態を表示

    Args:
        window_title: 現在ターゲットとなっているウィンドウ名
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 設定を初期化（必要に応じてグローバル変数を使用）
    config = get_config()
    
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
        config = get_config()
        path = filedialog.asksaveasfilename(
            defaultextension='.ini',
            filetypes=[('INI', '*.ini')],
            title='設定ファイルを保存',
            initialdir=default_dir
        )
        if path:
            # 現在の設定を保存
            config.config_path = path
            config.save()
            messagebox.showinfo('設定保存完了', f'設定を {path} に保存しました。')

    def menu_load_config():
        config = get_config()
        path = filedialog.askopenfilename(
            defaultextension='.ini',
            filetypes=[('INI', '*.ini')],
            title='設定ファイルを読み込み',
            initialdir=default_dir
        )
        if path:
            try:
                # 選択されたファイルを読み込む
                config.config_parser.read(path, encoding='utf-8')
                # 保存
                config.save()
                
                # 再起動して反映
                messagebox.showinfo('設定読み込み完了', '設定を読み込みました。アプリケーションを再起動します。')
                
                # ウィンドウタイトルをWindowセクションから取得
                main_title = config.get('TARGET_WINDOW_TITLE', 'LDPlayer')
                
                # アプリケーション再起動
                root.destroy()
                from src.gui_main import main as gui_main_entry
                gui_main_entry(window_title=main_title)
            except Exception as e:
                messagebox.showerror('エラー', f'設定ファイルの読み込みに失敗しました: {e}')

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

    # OCRプレビューを差分検知プレビューに変更
    diff_preview_frame = tk.LabelFrame(content_row, text='差分検知プレビュー', labelanchor='n', font=ocr_font, bg='#f8f8ff')
    diff_preview_frame.pack(side='left', fill='both', expand=True, padx=(0, 16), pady=0)

    # --- 差分プレビューCanvas ---
    DIFF_CANVAS_W, DIFF_CANVAS_H = 320, 240
    diff_canvas = tk.Canvas(diff_preview_frame, width=DIFF_CANVAS_W, height=DIFF_CANVAS_H, bg='#fff', relief=tk.SUNKEN, bd=1, highlightthickness=0)
    diff_canvas.pack(fill='both', expand=True, padx=12, pady=(12, 0))
    diff_canvas_img = None
    diff_canvas_img_obj = None
    diff_canvas_zoom = 1.0
    diff_canvas_pan = [0, 0]
    diff_canvas_dragging = False
    diff_canvas_drag_start = [0, 0]

    def draw_diff_canvas_img(img: Image.Image):
        nonlocal diff_canvas_img, diff_canvas_img_obj
        # ズーム・パンを反映して表示
        canvas_w = diff_canvas.winfo_width() or DIFF_CANVAS_W
        canvas_h = diff_canvas.winfo_height() or DIFF_CANVAS_H
        zoom = diff_canvas_zoom
        disp_w, disp_h = int(img.width * zoom), int(img.height * zoom)
        img_disp = img.resize((disp_w, disp_h), Image.LANCZOS)
        # パン（中央基準）
        x_offset = (canvas_w - disp_w) // 2 + diff_canvas_pan[0]
        y_offset = (canvas_h - disp_h) // 2 + diff_canvas_pan[1]
        diff_canvas.delete('all')
        diff_canvas_img = ImageTk.PhotoImage(img_disp)
        diff_canvas_img_obj = diff_canvas.create_image(x_offset, y_offset, anchor='nw', image=diff_canvas_img)

    # --- ズーム操作（マウスホイール） ---
    def on_diff_canvas_zoom(event):
        nonlocal diff_canvas_zoom
        if event.delta > 0:
            diff_canvas_zoom = min(diff_canvas_zoom + 0.1, 3.0)
        else:
            diff_canvas_zoom = max(diff_canvas_zoom - 0.1, 0.5)
        if diff_preview_img is not None:
            draw_diff_canvas_img(diff_preview_img)
    diff_canvas.bind('<MouseWheel>', on_diff_canvas_zoom)
    # Linux/Mac用
    diff_canvas.bind('<Button-4>', lambda e: (setattr(diff_canvas_zoom, '__iadd__', 0.1), draw_diff_canvas_img(diff_preview_img) if diff_preview_img is not None else None))
    diff_canvas.bind('<Button-5>', lambda e: (setattr(diff_canvas_zoom, '__isub__', 0.1), draw_diff_canvas_img(diff_preview_img) if diff_preview_img is not None else None))

    # --- パン操作（右クリックドラッグ） ---
    def on_diff_canvas_pan_start(event):
        nonlocal diff_canvas_dragging, diff_canvas_drag_start
        diff_canvas_dragging = True
        diff_canvas_drag_start = [event.x, event.y]
    def on_diff_canvas_pan_drag(event):
        nonlocal diff_canvas_dragging, diff_canvas_drag_start, diff_canvas_pan
        if diff_canvas_dragging:
            dx = event.x - diff_canvas_drag_start[0]
            dy = event.y - diff_canvas_drag_start[1]
            diff_canvas_pan[0] += dx
            diff_canvas_pan[1] += dy
            diff_canvas_drag_start = [event.x, event.y]
            if diff_preview_img is not None:
                draw_diff_canvas_img(diff_preview_img)
    def on_diff_canvas_pan_end(event):
        nonlocal diff_canvas_dragging
        diff_canvas_dragging = False
    # 左クリックバインドを削除し、右クリックに変更
    diff_canvas.unbind('<ButtonPress-1>')
    diff_canvas.unbind('<B1-Motion>')
    diff_canvas.unbind('<ButtonRelease-1>')
    diff_canvas.bind('<ButtonPress-3>', on_diff_canvas_pan_start)
    diff_canvas.bind('<B3-Motion>', on_diff_canvas_pan_drag)
    diff_canvas.bind('<ButtonRelease-3>', on_diff_canvas_pan_end)

    # --- ボタン（右）: 右端に縦並びで固定 ---
    button_frame = tk.Frame(content_row)
    button_frame.pack(side='right', fill='y', padx=(0, 8), pady=0)

    # --- コールバック関数をここで定義 ---
    def on_start() -> None:
        nonlocal ocr_thread
        if not ocr_thread:
            running.set()
            ocr_thread = threading.Thread(target=diff_detection_loop, daemon=True)
            ocr_thread.start()
            set_status('Running')
            start_button.config(state=tk.DISABLED)
            stop_button.config(state=tk.NORMAL)

    def on_stop() -> None:
        running.clear()
        set_status('Stopped')
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)

    def on_capture_diff() -> None:
        """画面の差分を検知して表示する"""
        global roi, prev_image, diff_preview_img, detector
        
        config = get_config()
        window_name = window_title or config.get("TARGET_WINDOW_TITLE", "LDPlayer")
        window_capture = WindowCapture(window_name)
        
        # 差分検知器の更新 - 設定が変更された場合に再生成
        detector_threshold = float(config.get("DIFF_THRESHOLD", "0.05"))
        if detector is None or detector.threshold != detector_threshold:
            detector = DifferenceDetector(config)
            logger.info(f"差分検知感度を{detector_threshold}に設定しました")
        
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
            
            if prev_image is None:
                prev_image = crop_img
                diff_preview_img = crop_img
                root.after(0, lambda img=diff_preview_img: draw_diff_canvas_img(img))
                return
            
            # 差分検知
            try:
                has_diff, diff_ratio, diff_image = detector.detect_difference(prev_image, crop_img)
                
                if has_diff:
                    ocr_text_var.set(f'差分を検出しました (変化率: {diff_ratio:.2f}%)')
                    # 差分画像をプレビューに表示
                    diff_preview_img = diff_image
                    draw_diff_canvas_img(diff_preview_img)
                else:
                    ocr_text_var.set('差分は検出されませんでした')
                
                # 現在の画像を保存
                prev_image = crop_img
                
            except Exception as e:
                logger.error(f"差分検知処理でエラー: {e}", exc_info=True)
                ocr_text_var.set(f'エラー: {str(e)}')
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
    diff_preview_frame.pack(side='left', fill='both', expand=True, padx=(0, 16), pady=0)
    diff_canvas.pack(fill='both', expand=True, padx=12, pady=(12, 0))
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
        global roi, prev_image, diff_preview_img, detector
        
        config = get_config()
        capture_running = threading.Event()
        capture_running.set()
        capture_thread = threading.current_thread()
        window_capture = None
        
        try:
            while capture_running.is_set():
                window_name = config.get("TARGET_WINDOW_TITLE", "LDPlayer")
                capture_interval = 1.0
                try:
                    capture_interval = float(config.get("CAPTURE_INTERVAL", "1.0"))
                except Exception:
                    pass
                if window_capture is None or window_capture.window_title != window_name:
                    from src.services.window_capture import WindowCapture
                    window_capture = WindowCapture(window_name)
                
                # 差分検知器の更新 - 設定が変更された場合に再生成
                detector_threshold = float(config.get("DIFF_THRESHOLD", "0.05"))
                if detector is None or detector.threshold != detector_threshold:
                    detector = DifferenceDetector(config)
                    logger.info(f"差分検知感度を{detector_threshold}に設定しました")
                
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
                
                # 差分検知処理
                try:
                    # 画像を上下反転
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
                    
                    # 初回キャプチャ時または前回画像がない場合
                    if prev_image is None:
                        prev_image = crop_img
                        diff_preview_img = crop_img
                        root.after(0, lambda img=diff_preview_img: draw_diff_canvas_img(img))
                        continue
                    
                    # 差分検知
                    has_diff, diff_ratio, diff_image = detector.detect_difference(prev_image, crop_img)
                    diff_preview_img = diff_image
                    root.after(0, lambda img=diff_preview_img: draw_diff_canvas_img(img))
                    
                    if running.is_set():
                        # 差分テキストを更新
                        if has_diff:
                            diff_text = f'差分を検出しました (変化率: {diff_ratio:.2f}%)'
                        else:
                            diff_text = '差分は検出されませんでした'
                        
                        # ローカル表示を更新（直接のGUI操作はメインスレッドで行う）
                        root.after(0, lambda txt=diff_text: ocr_text_var.set(txt))
                    
                    # 現在の画像を保存
                    prev_image = crop_img
                    
                except Exception as e:
                    logger.error(f"差分検知処理でエラー: {e}", exc_info=True)
                
                time.sleep(capture_interval)
        except Exception as e:
            logger.error(f"キャプチャループでエラー発生: {e}", exc_info=True)
        finally:
            logger.info("キャプチャループを終了")
            capture_thread = None

    def diff_detection_loop():
        """
        差分検知のメインループ。
        """
        global prev_image, diff_preview_img
        
        config = get_config()
        logger = logging.getLogger(__name__)
        
        # 前回の通知時刻を記録
        last_notification_time = 0
        # インターバル中に差分が検知されたかのフラグ
        diff_detected_during_cooldown = False
        
        while running.is_set():
            try:
                # 前回の画像がない場合はスキップ
                if prev_image is None:
                    time.sleep(0.1)
                    continue
                
                current_time = time.time()
                notification_cooldown = float(config.get('NOTIFICATION_COOLDOWN', '2.0'))
                
                # 差分を検知
                if diff_preview_img is not None:
                    diff_result = detector.detect_difference(prev_image, diff_preview_img)
                    
                    if diff_result[0]:  # has_difference
                        # インターバル中かどうかチェック
                        if current_time - last_notification_time < notification_cooldown:
                            # インターバル中なので、検知フラグをオンにするだけ
                            diff_detected_during_cooldown = True
                        else:
                            # インターバル終了後、または最初の差分検知時
                            
                            # 通知音を再生（設定が有効な場合）
                            if config.get('NOTIFICATION_SOUND', 'true').lower() == 'true':
                                play_notification_sound()
                            
                            # 通知時刻を更新
                            last_notification_time = current_time
                            # 検知フラグをリセット
                            diff_detected_during_cooldown = False
                
                # インターバル中の差分検知フラグがあり、インターバルが終了した場合
                elif diff_detected_during_cooldown and current_time - last_notification_time >= notification_cooldown:
                    # 通知音を再生（設定が有効な場合）
                    if config.get('NOTIFICATION_SOUND', 'true').lower() == 'true':
                        play_notification_sound()
                    
                    # 通知時刻を更新
                    last_notification_time = current_time
                    # 検知フラグをリセット
                    diff_detected_during_cooldown = False
                
                # 短い待機時間
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"差分検知処理でエラーが発生しました: {e}", exc_info=True)
                time.sleep(1.0)  # エラー時は少し待機

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

    def create_settings_ui(tab, settings_list, entries_dict, config):
        """設定項目のUIを作成する"""
        for i, (key, label, input_type, *args) in enumerate(settings_list):
            frame = ttk.Frame(tab)
            frame.pack(fill='x', padx=5, pady=2)
            
            # ラベル
            ttk.Label(frame, text=label).pack(side='left', padx=5)
            
            # 入力ウィジェット
            if input_type == 'entry':
                entry = ttk.Entry(frame)
                entry.insert(0, config.get(key, ''))
                entry.pack(side='right', padx=5)
                entries_dict[key] = entry
            
            elif input_type == 'checkbox':
                var = tk.BooleanVar(value=config.get(key, 'false').lower() == 'true')
                checkbox = ttk.Checkbutton(frame, variable=var)
                checkbox.pack(side='right', padx=5)
                entries_dict[key] = var
            
            elif input_type == 'combobox':
                values = args[0] if args else []
                combo = ttk.Combobox(frame, values=values, state='readonly')
                current_value = config.get(key, '')
                if current_value in values:
                    combo.set(current_value)
                elif values:
                    combo.set(values[0])
                combo.pack(side='right', padx=5)
                entries_dict[key] = combo
            
            elif input_type == 'scale':
                min_val, max_val = args[0] if args else (0, 100)
                frame.pack_forget()  # スケール用に特別なレイアウト
                
                scale_frame = ttk.Frame(tab)
                scale_frame.pack(fill='x', padx=5, pady=2)
                
                ttk.Label(scale_frame, text=label).pack(side='left', padx=5)
                
                # パーセンテージ表示用ラベル
                percentage_label = ttk.Label(scale_frame, text="0%")
                percentage_label.pack(side='right', padx=5)
                
                # スケール
                scale = ttk.Scale(scale_frame, from_=min_val, to=max_val, orient='horizontal')
                current_value = float(config.get(key, '0.05')) * 100
                scale.set(current_value)
                scale.pack(side='right', fill='x', expand=True, padx=5)
                entries_dict[key] = scale
                
                # スケールの値が変更されたときの処理
                def on_slider_change(event):
                    current_value = scale.get()
                    current_percentage = int(float(current_value))
                    percentage_label.config(text=f"{current_percentage}%")
                
                scale.bind('<Motion>', on_slider_change)
                scale.bind('<ButtonRelease-1>', on_slider_change)
                
                # 初期値を表示
                on_slider_change(None)

    def show_settings_dialog() -> None:
        """
        設定ダイアログを表示する。
        """
        config = get_config()
        dialog = tk.Toplevel()
        dialog.title('設定')
        dialog.geometry('500x400')
        dialog.resizable(False, False)
        
        # ダイアログを親ウィンドウの中央に配置
        dialog.transient(dialog.master)
        dialog.grab_set()
        
        def center_dialog():
            dialog.update_idletasks()
            parent = dialog.master
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()
            dialog_width = dialog.winfo_width()
            dialog_height = dialog.winfo_height()
            
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2
            dialog.geometry(f'+{x}+{y}')
        
        # タブコントロールの作成
        tab_control = ttk.Notebook(dialog)
        
        # ウィンドウ設定タブ
        window_tab = ttk.Frame(tab_control)
        tab_control.add(window_tab, text='ウィンドウ')
        
        # 差分検知タブ
        difference_tab = ttk.Frame(tab_control)
        tab_control.add(difference_tab, text='差分検知')
        
        # 通知タブ
        notification_tab = ttk.Frame(tab_control)
        tab_control.add(notification_tab, text='通知')
        
        tab_control.pack(expand=True, fill='both', padx=5, pady=5)
        
        # 設定項目の辞書（キーと対応するウィジェットを保持）
        entries_dict = {}
        
        # ウィンドウ設定
        window_settings = [
            ('TARGET_WINDOW_TITLE', 'ターゲットウィンドウ', 'combobox', get_window_titles()),
            ('CAPTURE_INTERVAL', 'キャプチャ間隔（秒）', 'entry'),
        ]
        
        # 差分検知設定
        difference_settings = [
            ('DIFF_THRESHOLD', '差分検知感度', 'scale', (0, 100)),
            ('DIFF_METHOD', '差分検知方式', 'combobox', ['ssim', 'mse']),
            ('DIFF_MAX_HISTORY', '履歴保持数', 'entry'),
            ('DIFF_DEBUG_MODE', 'デバッグモード', 'checkbox'),
        ]
        
        # 通知設定
        notification_settings = [
            ('NOTIFICATION_SOUND', '通知音を再生', 'checkbox'),
            ('NOTIFICATION_COOLDOWN', '通知クールダウン（秒）', 'entry'),
        ]
        
        # 各タブの設定項目を作成
        create_settings_ui(window_tab, window_settings, entries_dict, config)
        create_settings_ui(difference_tab, difference_settings, entries_dict, config)
        create_settings_ui(notification_tab, notification_settings, entries_dict, config)
        
        def on_save():
            """設定を保存する"""
            try:
                for key, widget in entries_dict.items():
                    if isinstance(widget, ttk.Entry):
                        value = widget.get()
                    elif isinstance(widget, tk.BooleanVar):
                        value = str(widget.get()).lower()
                    elif isinstance(widget, ttk.Combobox):
                        value = widget.get()
                    elif isinstance(widget, ttk.Scale):
                        value = str(widget.get() / 100.0)
                    
                    config.set(key, str(value))
                
                config.save()
                messagebox.showinfo('設定保存', '設定を保存しました。')
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror('エラー', f'設定の保存に失敗しました：{e}')
        
        def on_cancel():
            """設定をキャンセルする"""
            dialog.destroy()
        
        # ボタンフレーム
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(button_frame, text='保存', command=on_save).pack(side='right', padx=5)
        ttk.Button(button_frame, text='キャンセル', command=on_cancel).pack(side='right', padx=5)
        
        # ダイアログを中央に配置
        center_dialog()
        
        dialog.wait_window()

    # キャプチャスレッドを開始
    capture_thread = threading.Thread(target=capture_loop, daemon=True)
    capture_thread.start()

    root.mainloop()


if __name__ == '__main__':
    main(window_title="LDPlayer")
