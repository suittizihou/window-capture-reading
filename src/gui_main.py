import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import Optional
import queue
import time
from src.main import run_main_loop
from src.utils.logging_config import setup_logging
import logging


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
    root.geometry('600x260')
    root.resizable(False, False)

    # フォント設定
    title_font = tkfont.Font(family="Meiryo", size=14)
    status_font = tkfont.Font(family="Meiryo", size=10)
    ocr_font = tkfont.Font(family="Meiryo", size=12)

    # タイトルラベル
    title_var = tk.StringVar()
    title_var.set(f'ターゲットウィンドウ: {window_title or "(未設定)"}')
    title_label = tk.Label(root, textvariable=title_var, font=title_font, width=50, anchor='w')
    title_label.pack(pady=(20, 10), padx=20)

    # OCRテキスト表示エリア
    ocr_text_var = tk.StringVar()
    ocr_text_var.set('まだテキストは検出されていません')
    ocr_text_box = tk.Label(root, textvariable=ocr_text_var, font=ocr_font, width=60, height=4, anchor='nw', justify='left', bg='#f8f8f8', relief=tk.SUNKEN, bd=1)
    ocr_text_box.pack(pady=(0, 10), padx=20, fill='x')

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
                    text = ocr_service.extract_text(frame)
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

    # Start/Stop/終了ボタン
    button_frame = tk.Frame(root)
    button_frame.pack(pady=(0, 10))

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

    start_button = tk.Button(button_frame, text='Start', width=10, command=on_start)
    start_button.grid(row=0, column=0, padx=10)
    stop_button = tk.Button(button_frame, text='Stop', width=10, command=on_stop, state=tk.DISABLED)
    stop_button.grid(row=0, column=1, padx=10)
    exit_button = tk.Button(button_frame, text='終了', width=10, command=on_exit)
    exit_button.grid(row=0, column=2, padx=10)

    # OCRテキストのライブ更新を開始
    root.after(300, update_ocr_text)
    root.mainloop()


if __name__ == '__main__':
    main(window_title="LDPlayer")
