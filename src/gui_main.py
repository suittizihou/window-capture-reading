import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import Optional
import time
from src.main import run_main_loop


def main(window_title: Optional[str] = None) -> None:
    """
    ウィンドウキャプチャ対象のウィンドウタイトルをGUI上部に表示し、
    Start/Stopボタンでメイン処理（OCR・読み上げループ）を制御できるTkinter GUI。
    下部にシステム状態（Running/Error/Stopped）を表示するステータスバー付き。

    Args:
        window_title: 現在ターゲットとなっているウィンドウ名
    """
    root = tk.Tk()
    root.title('Window Capture Reading')
    root.geometry('500x210')
    root.resizable(False, False)

    # フォント設定
    title_font = tkfont.Font(family="Meiryo", size=14)
    status_font = tkfont.Font(family="Meiryo", size=10)

    # タイトルラベル
    title_var = tk.StringVar()
    title_var.set(f'ターゲットウィンドウ: {window_title or "(未設定)"}')
    title_label = tk.Label(root, textvariable=title_var, font=title_font, width=40, anchor='w')
    title_label.pack(pady=(20, 10), padx=20)

    # ステータスバー
    status_var = tk.StringVar()
    status_var.set('Stopped')
    status_bar = tk.Label(root, textvariable=status_var, font=status_font, bd=1, relief=tk.SUNKEN, anchor='w', bg='#f0f0f0')
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # スレッド制御用
    loop_thread = None
    running = tk.BooleanVar(value=False)

    def set_status(state: str) -> None:
        """ステータスバーの状態を更新する。"""
        status_var.set(state)
        if state == 'Running':
            status_bar.config(bg='#d0ffd0')
        elif state == 'Error':
            status_bar.config(bg='#ffd0d0')
        else:
            status_bar.config(bg='#f0f0f0')

    def start_main_loop() -> None:
        """メイン処理を別スレッドで開始する。"""
        nonlocal loop_thread
        if running.get():
            return
        running.set(True)
        set_status('Running')
        start_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.NORMAL)

        def run():
            try:
                run_main_loop(lambda: running.get())
            except Exception as e:
                set_status('Error')
            finally:
                running.set(False)
                if status_var.get() != 'Error':
                    set_status('Stopped')
                start_button.config(state=tk.NORMAL)
                stop_button.config(state=tk.DISABLED)

        loop_thread = threading.Thread(target=run, daemon=True)
        loop_thread.start()

    def stop_main_loop() -> None:
        """メイン処理の停止を指示する。"""
        running.set(False)
        set_status('Stopped')
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)

    # Start/Stopボタン
    button_frame = tk.Frame(root)
    button_frame.pack(pady=(0, 10))

    start_button = tk.Button(button_frame, text='Start', width=10, command=start_main_loop)
    start_button.grid(row=0, column=0, padx=10)

    stop_button = tk.Button(button_frame, text='Stop', width=10, command=stop_main_loop, state=tk.DISABLED)
    stop_button.grid(row=0, column=1, padx=10)

    # 終了ボタン
    def on_exit() -> None:
        """終了ボタン押下時の処理。"""
        stop_main_loop()
        root.destroy()

    exit_button = tk.Button(root, text='終了', command=on_exit, width=10)
    exit_button.pack(pady=(0, 10))

    root.mainloop()


if __name__ == '__main__':
    main(window_title="LDPlayer")
