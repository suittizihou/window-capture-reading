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


def main(window_title: Optional[str] = None) -> None:
    """
    Tkinterで実装したOCRテキストライブプレビュー付きGUI。
    - 最新のOCR認識テキストをリアルタイムで表示
    - Start/Stopボタンでメイン処理を制御
    - ステータスバーでシステム状態を表示

    Args:
        window_title: 現在ターゲットとなっているウィンドウ名
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    root = tk.Tk()
    root.title('Window Capture Reading')
    root.geometry('900x300')  # 横長に拡張
    root.resizable(True, True)  # ウィンドウをリサイズ可能に

    # フォント設定
    title_font = tkfont.Font(family="Meiryo", size=14)
    status_font = tkfont.Font(family="Meiryo", size=10)
    ocr_font = tkfont.Font(family="Meiryo", size=12)

    # タイトルラベル
    title_var = tk.StringVar()
    title_var.set(f'ターゲットウィンドウ: {window_title or "(未設定)"}')

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

    # --- レイアウトの土台だけ先に作る ---
    main_frame = tk.Frame(root)
    main_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
    left_frame = tk.Frame(main_frame, width=450)
    left_frame.pack(side='left', fill='both', expand=True)
    right_frame = tk.Frame(main_frame, width=420)
    right_frame.pack(side='right', fill='y')

    # タイトル・テキストエリア（左側）
    title_label = tk.Label(left_frame, textvariable=title_var, font=title_font, anchor='w')
    title_label.pack(pady=(20, 10), padx=0, anchor='w')
    ocr_text_box = tk.Label(left_frame, textvariable=ocr_text_var, font=ocr_font, width=60, height=4, anchor='nw', justify='left', bg='#f8f8f8', relief=tk.SUNKEN, bd=1)
    ocr_text_box.pack(pady=(0, 10), padx=0, fill='x')

    # --- OCR前処理画像プレビュー用ラベルを追加 ---
    ocr_img_preview_label = tk.Label(left_frame)
    ocr_img_preview_label.pack(pady=(0, 10), padx=0, anchor='w')

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
    roi = None  # [x1, y1, x2, y2] 画像座標
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
        nonlocal preview_img_on_canvas, roi_rect, preview_img_ref, roi, img_width, img_height, handle_ids
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
        x1, y1, x2, y2 = roi
        cx1, cy1 = image_to_canvas(x1, y1)
        cx2, cy2 = image_to_canvas(x2, y2)
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
        nonlocal dragging, roi, active_handle
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

    # ズームスライダーで必ず再描画
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
    zoom_slider = tk.Scale(right_frame, from_=0.2, to=2.0, resolution=0.05, orient='horizontal', label='ズーム', variable=zoom_var, command=on_zoom_change)
    zoom_slider.pack(pady=(0, 10))
    on_zoom_change.last_img = None

    preview_img_ref = None
    preview_img_on_canvas = None
    roi_rect = None

    def set_status(state: str) -> None:
        """ステータスバーの状態を更新する。"""
        status_var.set(state)
        if state == 'Running':
            status_bar.config(bg='#d0ffd0')
        elif state == 'Error':
            status_bar.config(bg='#ffd0d0')
        else:
            status_bar.config(bg='#f0f0f0')

    def ocr_loop():
        """OCR・読み上げメインループを別スレッドで実行し、テキストをキューに送る。
        棒読みちゃん連携も行う。
        """
        from src.services.window_capture import WindowCapture
        from src.services.ocr_service import OCRService
        from src.services.bouyomi_client import BouyomiClient
        from src.utils.config import Config
        config = Config()
        window_capture = WindowCapture(config.get("TARGET_WINDOW_TITLE", "LDPlayer"))
        ocr_service = OCRService(config)
        bouyomi_enabled = str(config.get("BOUYOMI_ENABLED", "true")).lower() == "true"
        bouyomi_client = None
        if bouyomi_enabled:
            try:
                bouyomi_client = BouyomiClient(config)
                logger.info("BouyomiClientを初期化しました（GUI）")
            except Exception as e:
                logger.error(f"BouyomiClientの初期化に失敗しました: {e}", exc_info=True)
                bouyomi_client = None
        last_text = ''
        try:
            while running.is_set():
                frame = window_capture.capture()
                if frame is not None:
                    # プレビュー描画（必ず最新画像で）
                    on_zoom_change.last_img = frame
                    draw_preview_with_roi(frame)
                    # --- まずキャプチャ画像を上下反転 ---
                    flipped_frame = frame.transpose(Image.FLIP_TOP_BOTTOM)
                    # ROI座標でクロップしてOCR
                    crop_img = flipped_frame
                    if roi is not None:
                        x1, y1, x2, y2 = [int(round(v)) for v in roi]
                        x1 = max(0, min(x1, flipped_frame.width-1))
                        y1 = max(0, min(y1, flipped_frame.height-1))
                        x2 = max(0, min(x2, flipped_frame.width))
                        y2 = max(0, min(y2, flipped_frame.height))
                        if x2 > x1 and y2 > y1:
                            crop_img = flipped_frame.crop((x1, y1, x2, y2))
                    # --- 前処理（グレースケール・リサイズ・コントラスト・二値化） ---
                    img_np = np.array(crop_img)
                    if img_np.ndim == 3:
                        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                    h, w = img_np.shape[:2]
                    if h < 40:
                        scale = 40 / h
                        img_np = cv2.resize(img_np, (int(w * scale), 40), interpolation=cv2.INTER_LANCZOS4)
                    img_np = cv2.convertScaleAbs(img_np, alpha=1.5, beta=10)
                    _, img_np = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    preprocessed_img = Image.fromarray(img_np)
                    # --- プレビュー用画像を表示（幅200pxでリサイズ） ---
                    preview_disp_img = preprocessed_img.copy()
                    disp_w = 200
                    disp_h = int(preview_disp_img.height * disp_w / preview_disp_img.width)
                    preview_disp_img = preview_disp_img.resize((disp_w, disp_h), Image.LANCZOS)
                    tk_preview_img = ImageTk.PhotoImage(preview_disp_img)
                    def update_preview():
                        ocr_img_preview_label.config(image=tk_preview_img)
                        ocr_img_preview_label.image = tk_preview_img  # 参照保持
                    ocr_img_preview_label.after(0, update_preview)
                    # --- OCR ---
                    text = ocr_service.extract_text(preprocessed_img)
                    if text and text != last_text:
                        ocr_text_queue.put(text)
                        last_text = text
                        if bouyomi_enabled and bouyomi_client is not None:
                            try:
                                bouyomi_client.talk(text)
                                logger.info(f"棒読みちゃんで読み上げ: {text}")
                            except Exception as e:
                                logger.error(f"棒読みちゃん読み上げエラー: {e}", exc_info=True)
                time.sleep(float(config.get("CAPTURE_INTERVAL", "1.0")))
        finally:
            if bouyomi_client is not None:
                try:
                    bouyomi_client.close()
                    logger.info("BouyomiClientをクローズしました（GUI）")
                except Exception as e:
                    logger.error(f"BouyomiClientのクローズに失敗: {e}", exc_info=True)

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
                combo = ttk.Combobox(dialog, values=window_titles, width=28, state="readonly")
                combo.set(value)
                combo.grid(row=i, column=1, padx=10, pady=8)
                entries[key] = combo
            else:
                entry = tk.Entry(dialog, width=30)
                entry.insert(0, value)
                entry.grid(row=i, column=1, padx=10, pady=8)
                entries[key] = entry
        def on_save():
            for key, _, _ in settings_keys:
                config[key] = entries[key].get()
            config.save()
            # タイトルラベルを即時更新
            title_var.set(f'ターゲットウィンドウ: {config.get("TARGET_WINDOW_TITLE", "(未設定)")}')
            # OCRスレッドを再起動して設定を即時反映
            on_stop()
            on_start()
            messagebox.showinfo('情報', '設定を保存し即時反映しました。')
            dialog.destroy()
        def on_cancel():
            dialog.destroy()
        save_btn = tk.Button(dialog, text='保存', width=10, command=on_save)
        save_btn.grid(row=len(settings_keys), column=0, padx=10, pady=20)
        cancel_btn = tk.Button(dialog, text='キャンセル', width=10, command=on_cancel)
        cancel_btn.grid(row=len(settings_keys), column=1, padx=10, pady=20)

    def on_start() -> None:
        if not running.is_set():
            running.set()
            set_status('Running')
            start_button.config(state=tk.DISABLED)
            stop_button.config(state=tk.NORMAL)
            global ocr_thread
            ocr_thread = threading.Thread(target=ocr_loop, daemon=True)
            ocr_thread.start()

    def on_stop() -> None:
        running.clear()
        set_status('Stopped')
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)

    def on_exit() -> None:
        running.clear()
        root.destroy()

    # --- ボタンフレーム（関数定義後に生成） ---
    button_frame = tk.Frame(left_frame)
    button_frame.pack(pady=(0, 10))
    start_button = tk.Button(button_frame, text='Start', width=10, command=on_start)
    start_button.grid(row=0, column=0, padx=10)
    stop_button = tk.Button(button_frame, text='Stop', width=10, command=on_stop, state=tk.DISABLED)
    stop_button.grid(row=0, column=1, padx=10)
    exit_button = tk.Button(button_frame, text='終了', width=10, command=on_exit)
    exit_button.grid(row=0, column=2, padx=10)
    settings_button = tk.Button(button_frame, text='設定', width=10, command=show_settings_dialog)
    settings_button.grid(row=0, column=3, padx=10)

    # OCRテキストのライブ更新を開始
    root.after(300, update_ocr_text)

    # マウスホイールでズーム
    def on_mouse_wheel(event):
        if event.delta > 0:
            zoom_var.set(min(zoom_var.get() + 0.1, 2.0))
        else:
            zoom_var.set(max(zoom_var.get() - 0.1, 0.2))
        on_zoom_change()
    preview_canvas.bind('<MouseWheel>', on_mouse_wheel)
    # Linux/Mac用
    preview_canvas.bind('<Button-4>', lambda e: (zoom_var.set(min(zoom_var.get() + 0.1, 2.0)), on_zoom_change()))
    preview_canvas.bind('<Button-5>', lambda e: (zoom_var.set(max(zoom_var.get() - 0.1, 0.2)), on_zoom_change()))

    # --- 右クリックでプレビュー画像のパン ---
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

    root.mainloop()


if __name__ == '__main__':
    main(window_title="LDPlayer")
