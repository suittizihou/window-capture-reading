import tkinter as tk
from tkinter import font as tkfont
from typing import Optional


def main(window_title: Optional[str] = None) -> None:
    """
    ウィンドウキャプチャ対象のウィンドウタイトルをGUI上部に表示するシンプルなTkinter GUI。

    Args:
        window_title: 現在ターゲットとなっているウィンドウ名
    """
    root = tk.Tk()
    root.title('Window Capture Reading')
    root.geometry('500x120')
    root.resizable(False, False)

    # フォント設定
    title_font = tkfont.Font(family="Meiryo", size=14)

    # タイトルラベル
    title_var = tk.StringVar()
    title_var.set(f'ターゲットウィンドウ: {window_title or "(未設定)"}')
    title_label = tk.Label(root, textvariable=title_var, font=title_font, width=40, anchor='w')
    title_label.pack(pady=(20, 10), padx=20)

    # 終了ボタン
    def on_exit() -> None:
        """終了ボタン押下時の処理。"""
        root.destroy()

    exit_button = tk.Button(root, text='終了', command=on_exit, width=10)
    exit_button.pack(pady=(0, 10))

    # メインループ
    root.mainloop()


if __name__ == '__main__':
    # 仮のウィンドウタイトルで起動
    main(window_title="LDPlayer") 
