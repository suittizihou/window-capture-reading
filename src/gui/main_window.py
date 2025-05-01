"""メインウィンドウモジュール。

アプリケーションのメインウィンドウを提供します。
"""

import os
import sys
import time
import threading
import queue
import datetime
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Any, List, Optional, Tuple, Callable, cast, Union, TypeVar
import numpy as np
from PIL import Image
from PIL.Image import Image as PILImage  # 型アノテーション用
import ctypes
import ctypes.wintypes
from PIL import Image, ImageTk
import cv2
from pathlib import Path
from src.main import run_main_loop
from src.utils.logging_config import setup_logging
from src.utils.config import Config, get_config
from src.services.window_capture import WindowCapture
from src.services.difference_detector import DifferenceDetector
from src.gui.utils import pil_to_cv, cv_to_pil, play_notification_sound, ellipsize
from src.gui.diff_canvas import DiffCanvas
from src.gui.preview_canvas import PreviewCanvas
from src.gui.settings_dialog import show_settings_dialog

T = TypeVar('T')

class MainWindow:
    """メインウィンドウクラス。"""

    def __init__(self) -> None:
        """メインウィンドウを初期化します。"""
        # 設定の読み込み
        self.config = get_config()
        
        # ロガーのセットアップ
        setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # ウィンドウの設定
        self.root = tk.Tk()
        self.root.title("Window Capture Reading")
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        
        # キャプチャ関連の変数
        self.window_capture: Optional[WindowCapture] = None
        self.capture_running = False
        self.detector: Optional[DifferenceDetector] = None
        self.prev_image: Optional[Image.Image] = None
        self.diff_preview_img: Optional[Image.Image] = None
        
        # キャプチャ対象ウィンドウ
        self.window_title_var = tk.StringVar(value=self.config.window_title or "")
        
        # キャプチャスレッド関連
        self.capture_thread: Optional[threading.Thread] = None
        self.diff_detection_thread: Optional[threading.Thread] = None
        self.capture_queue: "queue.Queue[Optional[Image.Image]]" = queue.Queue()
        self.stop_event = threading.Event()
        
        # 状態表示
        self.status_var = tk.StringVar(value="停止中")
        
        # UIの作成
        self._create_ui()
        
        # ウィンドウタイトルとバージョン情報の更新
        self._update_window_title()
        
        # 初期設定
        self._update_ui_state()

    def _create_ui(self) -> None:
        """UIを作成します。"""
        # メニューバーの作成
        self._create_menu()
        
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True)
        
        # 左パネル（プレビュー）
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # ウィンドウ選択部分
        window_frame = ttk.Frame(left_panel)
        window_frame.pack(fill="x", pady=5)
        
        ttk.Label(window_frame, text="キャプチャ対象:").pack(side="left", padx=5)
        
        # ウィンドウタイトル入力とドロップダウン
        self.window_combo = ttk.Combobox(window_frame, textvariable=self.window_title_var)
        self.window_combo.pack(side="left", fill="x", expand=True, padx=5)
        self.window_combo.bind("<<ComboboxSelected>>", self._on_window_selected)
        
        # リフレッシュボタン
        refresh_button = ttk.Button(window_frame, text="更新", command=self._refresh_window_list)
        refresh_button.pack(side="left", padx=5)
        
        # プレビューキャンバス
        preview_frame = ttk.LabelFrame(left_panel, text="プレビュー")
        preview_frame.pack(fill="both", expand=True, pady=5)
        
        self.preview_canvas_container = ttk.Frame(preview_frame)
        self.preview_canvas_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.preview_canvas = PreviewCanvas(self.preview_canvas_container)
        
        # ROI変更通知を設定
        self.preview_canvas.on_roi_changed = self._on_roi_changed
        
        # ボタンフレーム
        button_frame = ttk.Frame(left_panel)
        button_frame.pack(fill="x", pady=5)
        
        self.start_button = ttk.Button(button_frame, text="開始", command=self.on_start)
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="停止", command=self.on_stop, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        
        self.capture_button = ttk.Button(button_frame, text="今すぐキャプチャ", command=self.on_capture_diff)
        self.capture_button.pack(side="left", padx=5)
        
        # 状態表示
        status_frame = ttk.Frame(left_panel)
        status_frame.pack(fill="x", pady=5)
        
        ttk.Label(status_frame, text="状態:").pack(side="left", padx=5)
        ttk.Label(status_frame, textvariable=self.status_var).pack(side="left", padx=5)
        
        # 右パネル（差分表示）
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        # 差分表示キャンバス
        diff_frame = ttk.LabelFrame(right_panel, text="差分表示")
        diff_frame.pack(fill="both", expand=True, pady=5)
        
        self.diff_canvas_container = ttk.Frame(diff_frame)
        self.diff_canvas_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.diff_canvas = DiffCanvas(self.diff_canvas_container)
        
        # ウィンドウリストの初期化
        self._refresh_window_list()

    def _create_menu(self) -> None:
        """メニューバーを作成します。"""
        menubar = tk.Menu(self.root)
        
        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="設定を保存", command=self._menu_save_config)
        file_menu.add_command(label="設定を読み込み", command=self._menu_load_config)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.on_exit)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        
        # 編集メニュー
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="設定", command=self._menu_settings)
        menubar.add_cascade(label="編集", menu=edit_menu)
        
        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="バージョン情報", command=self._menu_about)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        
        self.root.config(menu=menubar)

    def _refresh_window_list(self) -> None:
        """ウィンドウリストを更新します。"""
        titles = self._get_window_titles()
        self.window_combo["values"] = titles

    def _get_window_titles(self) -> List[str]:
        """利用可能なウィンドウのタイトル一覧を取得します。

        Returns:
            ウィンドウタイトルのリスト
        """
        titles: List[str] = []
        
        def foreach_window(hwnd: int, _: Any) -> bool:
            if ctypes.windll.user32.IsWindowVisible(hwnd):
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    if title and title not in titles:
                        titles.append(title)
            return True
        
        enum_windows_proc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int)
        )(foreach_window)
        
        ctypes.windll.user32.EnumWindows(enum_windows_proc, 0)
        return titles

    def _update_window_title(self) -> None:
        """ウィンドウタイトルを更新します。"""
        title = "Window Capture Reading"
        
        # キャプチャ対象ウィンドウタイトルを追加
        window_title = self.window_title_var.get()
        if window_title:
            title += f" - {ellipsize(window_title)}"
            
        self.root.title(title)

    def _update_ui_state(self) -> None:
        """UIの状態を更新します。"""
        running = self.capture_running
        
        # ボタンの状態設定
        self.start_button["state"] = "disabled" if running else "normal"
        self.stop_button["state"] = "normal" if running else "disabled"
        
        # 状態表示の更新
        self.status_var.set("実行中" if running else "停止中")

    def _on_window_selected(self, event: tk.Event) -> None:
        """ウィンドウ選択時の処理。

        Args:
            event: イベントオブジェクト
        """
        self._update_window_title()

    def _on_roi_changed(self, roi: List[int]) -> None:
        """ROI変更時のコールバック。

        Args:
            roi: 新しいROI座標 [x1, y1, x2, y2]
        """
        self.logger.debug(f"ROIが変更されました: {roi}")

    def _menu_save_config(self) -> None:
        """設定を保存します。"""
        # 現在の設定を取得
        window_title = self.window_title_var.get()
        if window_title:
            self.config.window_title = window_title
            
        # 保存先を選択
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="設定の保存先を選択"
        )
        
        if file_path:
            try:
                # PathオブジェクトとしてパスをPython内で扱う
                config_path = Path(file_path)
                
                # パスを文字列として保存する際には単純にstrで変換
                self.config.save(str(config_path))
                messagebox.showinfo("設定保存", "設定を保存しました。")
            except Exception as e:
                self.logger.error(f"設定の保存に失敗しました: {e}")
                messagebox.showerror("エラー", f"設定の保存に失敗しました: {e}")

    def _menu_load_config(self) -> None:
        """設定を読み込みます。"""
        # 読み込むファイルを選択
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="読み込む設定ファイルを選択"
        )
        
        if file_path:
            try:
                # PathオブジェクトとしてパスをPython内で扱う
                config_path = Path(file_path)
                
                # パスを文字列として読み込む際には単純にstrで変換
                self.config = Config.load(str(config_path))
                
                # UI更新
                self.window_title_var.set(self.config.window_title or "")
                self._update_window_title()
                
                messagebox.showinfo("設定読み込み", "設定を読み込みました。")
            except Exception as e:
                self.logger.error(f"設定の読み込みに失敗しました: {e}")
                messagebox.showerror("エラー", f"設定の読み込みに失敗しました: {e}")

    def _menu_settings(self) -> None:
        """設定ダイアログを表示します。"""
        # 現在の設定を反映
        window_title = self.window_title_var.get()
        if window_title:
            self.config.window_title = window_title
            
        # 設定ダイアログを表示
        show_settings_dialog(self.root, self.config, self._on_settings_saved)

    def _on_settings_saved(self, config: Config) -> None:
        """設定保存時のコールバック。

        Args:
            config: 新しい設定オブジェクト
        """
        self.config = config
        
        # UIに反映
        self.window_title_var.set(config.window_title or "")
        self._update_window_title()
        
        # 実行中であれば再起動を促す
        if self.capture_running:
            messagebox.showinfo("設定変更", "設定を変更しました。変更を反映するには一度停止してから再度開始してください。")

    def _menu_about(self) -> None:
        """バージョン情報を表示します。"""
        messagebox.showinfo(
            "バージョン情報",
            "Window Capture Reading\nVersion 1.0.0\n\n"
            "ウィンドウをキャプチャして変化を検出するツールです。"
        )

    def on_start(self) -> None:
        """キャプチャを開始します。"""
        window_title = self.window_title_var.get()
        if not window_title:
            messagebox.showerror("エラー", "キャプチャ対象のウィンドウを選択してください。")
            return
            
        # 設定を保存
        self.config.window_title = window_title
        
        # 差分検出器の初期化
        self.detector = DifferenceDetector(
            threshold=self.config.diff_threshold,
            ocr_enabled=self.config.ocr_enabled,
            ocr_language=self.config.ocr_language,
            ocr_threshold=self.config.ocr_threshold
        )
        
        # スレッド起動前の状態設定
        self.capture_running = True
        self.stop_event.clear()
        
        # キャプチャスレッドの開始
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        
        # 差分検出スレッドの開始
        self.diff_detection_thread = threading.Thread(target=self._diff_detection_loop)
        self.diff_detection_thread.daemon = True
        self.diff_detection_thread.start()
        
        # UI状態の更新
        self._update_ui_state()
        self.logger.info(f"キャプチャを開始しました: {window_title}")

    def on_stop(self) -> None:
        """キャプチャを停止します。"""
        # 停止フラグを立てる
        self.stop_event.set()
        self.capture_running = False
        
        # キューをクリア
        while not self.capture_queue.empty():
            try:
                self.capture_queue.get_nowait()
            except queue.Empty:
                break
        
        # UI状態の更新
        self._update_ui_state()
        self.logger.info("キャプチャを停止しました")

    def on_capture_diff(self) -> None:
        """手動で差分キャプチャを実行します。"""
        window_title = self.window_title_var.get()
        if not window_title:
            messagebox.showerror("エラー", "キャプチャ対象のウィンドウを選択してください。")
            return
            
        try:
            # ウィンドウキャプチャの初期化
            self.window_capture = WindowCapture(window_title)
            
            # キャプチャ実行
            frame = self.window_capture.capture()
            if frame is None:
                messagebox.showerror("エラー", "ウィンドウのキャプチャに失敗しました。")
                return
                
            # PIL画像に変換
            frame_img = cv_to_pil(frame)
            
            # ROIの適用
            roi = self.preview_canvas.get_roi()
            if roi is not None:
                x1, y1, x2, y2 = roi
                frame_img = frame_img.crop((x1, y1, x2, y2))
            
            # プレビューに表示
            self.preview_canvas.set_image(frame_img)
            
            # 差分検出
            if self.prev_image is not None:
                # 差分検出器がなければ初期化
                if self.detector is None:
                    self.detector = DifferenceDetector(
                        threshold=self.config.diff_threshold,
                        ocr_enabled=self.config.ocr_enabled,
                        ocr_language=self.config.ocr_language,
                        ocr_threshold=self.config.ocr_threshold
                    )
                    
                # サイズ調整
                if self.prev_image.size != frame_img.size:
                    self.prev_image = self.prev_image.resize(frame_img.size, Image.LANCZOS)
                
                # 差分検出
                diff_result = self.detector.detect(
                    pil_to_cv(self.prev_image),
                    pil_to_cv(frame_img)
                )
                
                if diff_result.has_difference:
                    # 差分があった場合
                    self.logger.info(f"差分を検出しました: {diff_result.score:.2f}")
                    
                    # 差分画像の表示
                    self.diff_preview_img = cv_to_pil(diff_result.diff_image)
                    self.diff_canvas.set_image(self.diff_preview_img)
                    
                    # 通知
                    if self.config.notification_sound:
                        notify_sound = play_notification_sound
                        self.root.after(0, notify_sound)
                        
                    if self.config.notification_popup:
                        messagebox.showinfo("差分検出", f"差分を検出しました。\n差分スコア: {diff_result.score:.2f}")
                        
                else:
                    # 差分がなかった場合
                    self.logger.info("差分はありませんでした")
                    messagebox.showinfo("差分検出", "差分はありませんでした。")
            
            # 現在のフレームを保存
            self.prev_image = frame_img
            
        except Exception as e:
            self.logger.error(f"キャプチャ処理でエラーが発生しました: {e}")
            messagebox.showerror("エラー", f"キャプチャ処理に失敗しました: {e}")

    def _capture_loop(self) -> None:
        """キャプチャループを実行します。"""
        self.logger.debug("キャプチャループを開始します")
        window_title = self.window_title_var.get()
        
        try:
            # ウィンドウキャプチャの初期化
            self.window_capture = WindowCapture(window_title)
            
            while not self.stop_event.is_set():
                try:
                    # キャプチャ実行
                    frame = self.window_capture.capture()
                    if frame is None:
                        self.logger.warning("ウィンドウのキャプチャに失敗しました")
                        time.sleep(1)  # エラー時は少し待機
                        continue
                        
                    # PIL画像に変換
                    frame_img = cv_to_pil(frame)
                    
                    # ROIの適用
                    roi = self.preview_canvas.get_roi()
                    if roi is not None:
                        x1, y1, x2, y2 = roi
                        frame_img = frame_img.crop((x1, y1, x2, y2))
                    
                    # プレビュー表示を更新（メインスレッドで）
                    update_preview = lambda img=frame_img: self.preview_canvas.set_image(img)
                    self.root.after(0, update_preview)
                    
                    # キューに追加
                    self.capture_queue.put(frame_img)
                    
                    # 待機
                    time.sleep(self.config.capture_interval)
                    
                except Exception as e:
                    self.logger.error(f"キャプチャ処理でエラーが発生しました: {e}")
                    time.sleep(1)  # エラー時は少し待機
                    
        except Exception as e:
            self.logger.error(f"キャプチャループでエラーが発生しました: {e}")
            # UI更新（メインスレッドで）
            show_error = lambda err=e: messagebox.showerror("エラー", f"キャプチャ処理に失敗しました: {err}")
            stop_capture = lambda: self.on_stop()
            self.root.after(0, show_error)
            self.root.after(0, stop_capture)
            
        self.logger.debug("キャプチャループを終了します")

    def _diff_detection_loop(self) -> None:
        """差分検出ループを実行します。"""
        self.logger.debug("差分検出ループを開始します")
        
        try:
            while not self.stop_event.is_set():
                try:
                    # キューから取得（タイムアウト付き）
                    frame_img = self.capture_queue.get(timeout=1.0)
                    
                    if frame_img is not None and self.detector is not None:
                        # 初回は前回画像として保存して終了
                        if self.prev_image is None:
                            self.prev_image = frame_img
                            self.capture_queue.task_done()
                            continue
                            
                        # サイズ調整
                        if self.prev_image.size != frame_img.size:
                            self.prev_image = self.prev_image.resize(frame_img.size, Image.LANCZOS)
                        
                        # 差分検出
                        diff_result = self.detector.detect(
                            pil_to_cv(self.prev_image),
                            pil_to_cv(frame_img)
                        )
                        
                        if diff_result.has_difference:
                            # 差分があった場合
                            self.logger.info(
                                f"差分を検出しました: {diff_result.score:.2f} "
                                f"(時刻: {datetime.datetime.now().strftime('%H:%M:%S')})"
                            )
                            
                            # 差分画像の表示（メインスレッドで）
                            diff_img = cv_to_pil(diff_result.diff_image)
                            self.diff_preview_img = diff_img
                            update_diff_view = lambda img=diff_img: self.diff_canvas.set_image(img)
                            self.root.after(0, update_diff_view)
                            
                            # 通知（メインスレッドで）
                            if self.config.notification_sound:
                                notify_sound = play_notification_sound
                                self.root.after(0, notify_sound)
                                
                            if self.config.notification_popup:
                                score = diff_result.score
                                show_notification = lambda s=score: messagebox.showinfo(
                                    "差分検出", 
                                    f"差分を検出しました。\n差分スコア: {s:.2f}"
                                )
                                self.root.after(0, show_notification)
                                
                        # 現在のフレームを保存
                        self.prev_image = frame_img
                    
                    # タスク完了を通知
                    self.capture_queue.task_done()
                    
                except queue.Empty:
                    # タイムアウト時は何もしない
                    pass
                except Exception as e:
                    self.logger.error(f"差分検出処理でエラーが発生しました: {e}")
                    
        except Exception as e:
            self.logger.error(f"差分検出ループでエラーが発生しました: {e}")
            
        self.logger.debug("差分検出ループを終了します")

    def on_exit(self) -> None:
        """アプリケーションを終了します。"""
        if self.capture_running:
            if not messagebox.askyesno("確認", "キャプチャ実行中ですが、終了しますか？"):
                return
            self.on_stop()
            
        self.root.quit()

    def run(self) -> None:
        """メインループを実行します。"""
        self.root.mainloop()

def main() -> None:
    """アプリケーションを起動します。"""
    app = MainWindow()
    app.run() 