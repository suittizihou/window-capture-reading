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
from PIL import Image, ImageTk
from PIL.Image import Image as PILImage  # 型アノテーション用
import ctypes
import ctypes.wintypes
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
from ctypes import windll

T = TypeVar("T")


class MainWindow:
    """メインウィンドウクラス。"""

    def __init__(self) -> None:
        """メインウィンドウを初期化します。"""
        # 設定の読み込み
        self.config = get_config()

        # DPIスケーリング対応
        try:
            windll.user32.SetProcessDPIAware()
        except Exception as e:
            self.logger.warning(f"DPIスケーリング設定に失敗しました: {e}")

        # ロガーのセットアップ
        setup_logging()
        self.logger = logging.getLogger(__name__)

        # ウィンドウの設定
        self.root = tk.Tk()
        self.root.minsize(1200, 700)
        self.root.title("Window Capture Reading")

        # Windows固有の設定
        if hasattr(self.root, "attributes"):
            try:
                # ツールウィンドウ設定を無効化
                self.root.attributes("-toolwindow", 0)
                # 通常のウィンドウスタイルを強制
                self.root.attributes("-alpha", 1.0)

                # DWMコンポジションの影響を最小限に
                if hasattr(ctypes.windll.dwmapi, "DwmSetWindowAttribute"):
                    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                    set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
                    hwnd = self.root.winfo_id()
                    value = 0
                    set_window_attribute(
                        hwnd,
                        DWMWA_USE_IMMERSIVE_DARK_MODE,
                        ctypes.byref(ctypes.c_int(value)),
                        ctypes.sizeof(ctypes.c_int),
                    )
            except tk.TclError:
                self.logger.warning("Windowsの特殊な設定の適用に失敗しました")
                pass

        # メニューバーの作成
        self._create_menu()

        # キャプチャ関連の変数
        self.window_capture: Optional[WindowCapture] = None
        self.capture_running = False
        self.detector: Optional[DifferenceDetector] = None
        self.prev_image: Optional[Image.Image] = None
        self.diff_preview_img: Optional[Image.Image] = None
        self.original_frame: Optional[Image.Image] = None

        # キャプチャ対象ウィンドウ
        self.window_title_var = tk.StringVar(value=self.config.window_title or "")

        # キャプチャスレッド関連
        self.capture_thread: Optional[threading.Thread] = None
        self.diff_detection_thread: Optional[threading.Thread] = None
        self.capture_queue: "queue.Queue[Optional[Tuple[Image.Image, Image.Image]]]" = (
            queue.Queue()
        )
        self.stop_event = threading.Event()

        # 状態表示
        self.status_var = tk.StringVar(value="停止中")
        self.diff_score_var = tk.StringVar(value="差分スコア: -")

        # UIの作成
        self._create_ui()

        # ウィンドウタイトルとバージョン情報の更新
        self._update_window_title()

        # 初期設定
        self._update_ui_state()

        # ROIの初期設定
        self.root.after(500, self._init_default_roi)

        # 保存されているウィンドウタイトルが利用可能な場合、プレビューを表示
        self.root.after(1000, self._init_saved_window_preview)

        # ウィンドウの再描画を確実に行うための設定
        self.root.after(100, self._ensure_menu_visible)

        # ウィンドウサイズ保持フラグ
        self.keep_window_size = False
        self.target_width = 1200
        self.target_height = 800

    def _ensure_menu_visible(self) -> None:
        """メニューバーが確実に表示されるようにします。"""
        # ウィンドウの再描画を促す
        self.root.update_idletasks()

        # 定期的に呼び出し
        self.root.after(1000, self._ensure_menu_visible)

    def _create_menu(self) -> None:
        """メニューバーを作成します。"""
        # 既存のメニューバーをクリア（念のため）
        if hasattr(self.root, "config") and callable(self.root.config):
            self.root.config(menu=None)

        # 新しいメニューバーを作成
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 以下設定を追加
        self.root.option_add("*tearOff", False)  # tearOffメニューを無効化

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

        # メニューバーが確実に表示されるようにする
        self.root.update_idletasks()

    def _create_ui(self) -> None:
        """UIを作成します。"""
        # メインコンテナを作成（バグ対応のためにFrame継承のttkではなく純粋なtkを使用）
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)

        # メインコンテナに2列レイアウトを設定
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)

        # 左パネル（プレビュー）
        left_panel = ttk.Frame(main_container)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # 左パネルの行設定
        left_panel.grid_rowconfigure(2, weight=1)  # プレビューキャンバス行
        left_panel.grid_columnconfigure(0, weight=1)

        # ウィンドウ選択部分
        window_frame = ttk.Frame(left_panel)
        window_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # ウィンドウ選択フレームの列設定
        window_frame.grid_columnconfigure(1, weight=1)  # コンボボックスが伸縮

        ttk.Label(window_frame, text="キャプチャ対象:").grid(
            row=0, column=0, padx=(0, 5)
        )

        # ウィンドウタイトル入力とドロップダウン
        self.window_combo = ttk.Combobox(
            window_frame, textvariable=self.window_title_var, state="readonly"
        )
        self.window_combo.grid(row=0, column=1, sticky="ew")
        self.window_combo.bind("<<ComboboxSelected>>", self._on_window_selected)

        # リフレッシュボタン
        refresh_button = ttk.Button(
            window_frame, text="更新", command=self._refresh_and_capture
        )
        refresh_button.grid(row=0, column=2, padx=(5, 0))

        # プレビューキャンバス
        preview_frame = ttk.LabelFrame(left_panel, text="プレビュー")
        preview_frame.grid(row=2, column=0, sticky="nsew")
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        self.preview_canvas_container = ttk.Frame(preview_frame)
        self.preview_canvas_container.grid(
            row=0, column=0, sticky="nsew", padx=5, pady=5
        )
        self.preview_canvas_container.grid_rowconfigure(0, weight=1)
        self.preview_canvas_container.grid_columnconfigure(0, weight=1)

        self.preview_canvas = PreviewCanvas(self.preview_canvas_container)
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")

        # ROI変更通知を設定
        self.preview_canvas.on_roi_changed = self._on_roi_changed

        # ボタンフレーム
        button_frame = ttk.Frame(left_panel)
        button_frame.grid(row=3, column=0, sticky="ew", pady=(5, 0))

        self.start_button = ttk.Button(button_frame, text="開始", command=self.on_start)
        self.start_button.grid(row=0, column=0, padx=(0, 5))

        self.stop_button = ttk.Button(
            button_frame, text="停止", command=self.on_stop, state="disabled"
        )
        self.stop_button.grid(row=0, column=1)

        # 状態表示
        status_frame = ttk.Frame(left_panel)
        status_frame.grid(row=4, column=0, sticky="ew", pady=(5, 0))

        ttk.Label(status_frame, text="状態:").grid(row=0, column=0, padx=(0, 5))
        ttk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=1)

        # 右パネル（差分表示）
        right_panel = ttk.Frame(main_container)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        right_panel.grid_rowconfigure(0, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        # 差分表示キャンバス
        diff_frame = ttk.LabelFrame(right_panel, text="差分表示")
        diff_frame.grid(row=0, column=0, sticky="nsew")
        diff_frame.grid_rowconfigure(1, weight=1)
        diff_frame.grid_columnconfigure(0, weight=1)

        # 差分スコア表示
        self.diff_score_label = ttk.Label(
            diff_frame, textvariable=self.diff_score_var, foreground="black"
        )
        self.diff_score_label.grid(row=0, column=0, sticky="w", padx=5, pady=2)

        self.diff_canvas_container = ttk.Frame(diff_frame)
        self.diff_canvas_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.diff_canvas_container.grid_rowconfigure(0, weight=1)
        self.diff_canvas_container.grid_columnconfigure(0, weight=1)

        self.diff_canvas = DiffCanvas(self.diff_canvas_container, bg="black")
        self.diff_canvas.grid(row=0, column=0, sticky="nsew")
        self.diff_canvas_container.grid_rowconfigure(
            1, weight=0
        )  # コントロールフレーム用

        # ウィンドウリストの初期化
        self._refresh_window_list()

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

        # 選択されたウィンドウタイトルを設定に保存
        window_title = self.window_title_var.get()
        if window_title:
            self.config.window_title = window_title
            self.logger.info(f"キャプチャ対象を選択しました: {window_title}")

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
            title="設定の保存先を選択",
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
            title="読み込む設定ファイルを選択",
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
            messagebox.showinfo(
                "設定変更",
                "設定を変更しました。変更を反映するには一度停止してから再度開始してください。",
            )

    def _menu_about(self) -> None:
        """バージョン情報を表示します。"""
        messagebox.showinfo(
            "バージョン情報",
            "Window Capture Reading\nVersion 1.0.0\n\n"
            "ウィンドウをキャプチャして変化を検出するツールです。",
        )

    def on_start(self) -> None:
        """キャプチャを開始します。"""
        window_title = self.window_title_var.get()
        if not window_title:
            messagebox.showerror(
                "エラー", "キャプチャ対象のウィンドウを選択してください。"
            )
            return

        # 設定を保存
        self.config.window_title = window_title

        # 差分検出器の初期化
        self.detector = DifferenceDetector(
            threshold=self.config.diff_threshold,
            diff_method=self.config.diff_method,
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

        # 短い間隔でウィンドウサイズをチェックして復元
        self.root.after(10, self._check_and_restore_window_size)

    def _check_and_restore_window_size(self) -> None:
        """ウィンドウサイズをチェックして必要に応じて復元します。"""
        if not hasattr(self, "keep_window_size") or not self.keep_window_size:
            return

        current_width = self.root.winfo_width()
        current_height = self.root.winfo_height()
        current_x = self.root.winfo_x()
        current_y = self.root.winfo_y()

        if hasattr(self, "target_width") and hasattr(self, "target_height"):
            # サイズと位置の変更を検出
            size_changed = (
                abs(current_width - self.target_width) > 2
                or abs(current_height - self.target_height) > 2
            )
            position_changed = (
                abs(current_x - self.target_x) > 2 or abs(current_y - self.target_y) > 2
            )

            if size_changed or position_changed:
                self.logger.debug(
                    f"ウィンドウを復元: 現在={current_width}x{current_height}@{current_x},{current_y} "
                    f"目標={self.target_width}x{self.target_height}@{self.target_x},{self.target_y}"
                )
                # サイズと位置を強制的に復元（メニューバーの高さは既に含まれている）
                self.root.geometry(
                    f"{self.target_width}x{self.target_height}+{self.target_x}+{self.target_y}"
                )
                self.root.update_idletasks()

        # キャプチャ実行中は頻繁にチェック
        self.root.after(50, self._check_and_restore_window_size)

    def on_stop(self) -> None:
        """キャプチャを停止します。"""
        # 現在のウィンドウサイズを取得
        current_width = self.root.winfo_width()
        current_height = self.root.winfo_height()
        self.logger.debug(f"キャプチャ停止時のサイズ: {current_width}x{current_height}")

        # サイズを明示的に固定
        self.root.geometry(f"{current_width}x{current_height}")

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

        # ウィンドウサイズを維持
        self.target_width = current_width
        self.target_height = current_height
        # サイズチェックは継続するが頻度を下げる
        self.root.update_idletasks()

    def _update_preview(self, img: Image.Image) -> None:
        """プレビューキャンバスを更新する関数。

        Args:
            img: 表示する画像
        """
        if img is not None:
            self.preview_canvas.set_image(img)

    def _show_error(self, err: Exception) -> None:
        """エラーダイアログを表示する関数。

        Args:
            err: エラーオブジェクト
        """
        messagebox.showerror("エラー", f"キャプチャ処理に失敗しました: {err}")

    def _stop_capture(self) -> None:
        """キャプチャを停止する関数。"""
        self.on_stop()

    def _update_diff_view(self, img: Image.Image) -> None:
        """差分表示キャンバスを更新する関数。

        Args:
            img: 表示する画像
        """
        if img is not None:
            self.diff_canvas.update_image(img)

    def _show_notification(self, score: float) -> None:
        """通知ダイアログを表示する関数。

        Args:
            score: 差分スコア
        """
        messagebox.showinfo(
            "差分検出",
            f"差分を検出しました。\n差分スコア: {score:.2f}",
        )

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
                    self.original_frame = frame_img.copy()  # 元画像を保持

                    # プレビュー表示を更新（メインスレッドで）
                    orig_frame = self.original_frame  # ローカル変数でキャプチャ
                    if orig_frame is not None:
                        self.root.after(0, lambda: self._update_preview(orig_frame))

                    # ROIの適用
                    roi = self.preview_canvas.get_roi()
                    cropped_frame: Image.Image
                    if roi is not None and self.original_frame is not None:
                        x1, y1, x2, y2 = roi
                        cropped_frame = self.original_frame.crop((x1, y1, x2, y2))
                    else:
                        cropped_frame = (
                            self.original_frame
                            if self.original_frame is not None
                            else Image.new("RGB", (100, 100), "black")
                        )

                    # キューに追加
                    orig = (
                        self.original_frame
                        if self.original_frame is not None
                        else Image.new("RGB", (100, 100), "black")
                    )
                    self.capture_queue.put((cropped_frame, orig))

                    # 待機
                    time.sleep(self.config.capture_interval)

                except Exception as e:
                    self.logger.error(f"キャプチャ処理でエラーが発生しました: {e}")
                    time.sleep(1)  # エラー時は少し待機

        except Exception as e:
            self.logger.error(f"キャプチャループでエラーが発生しました: {e}")
            # UI更新（メインスレッドで）
            err = e  # 変数をキャプチャするためのローカル変数
            self.root.after(0, lambda: self._show_error(err))
            self.root.after(0, self._stop_capture)

        self.logger.debug("キャプチャループを終了します")

    def _diff_detection_loop(self) -> None:
        """差分検出ループを実行します。"""
        self.logger.debug("差分検出ループを開始します")

        try:
            while not self.stop_event.is_set():
                try:
                    # キューから取得（タイムアウト付き）
                    queue_item = self.capture_queue.get(timeout=1.0)

                    if queue_item is not None and self.detector is not None:
                        cropped_frame, original_frame = queue_item

                        # 初回は前回画像として保存して終了
                        if self.prev_image is None:
                            self.prev_image = original_frame
                            self.capture_queue.task_done()
                            continue

                        # ROIの適用
                        roi = self.preview_canvas.get_roi()
                        cropped_prev: Image.Image
                        if roi is not None and self.prev_image is not None:
                            x1, y1, x2, y2 = roi
                            cropped_prev = self.prev_image.crop((x1, y1, x2, y2))
                        else:
                            cropped_prev = (
                                self.prev_image
                                if self.prev_image is not None
                                else Image.new("RGB", cropped_frame.size, "black")
                            )

                        # サイズ調整
                        if cropped_prev.size != cropped_frame.size:
                            cropped_prev = cropped_prev.resize(
                                cropped_frame.size, Image.LANCZOS
                            )

                        # 差分検出
                        diff_result = self.detector.detect(
                            pil_to_cv(cropped_prev), pil_to_cv(cropped_frame)
                        )

                        # 差分画像の表示（メインスレッドで）
                        diff_img = cv_to_pil(diff_result.diff_image)
                        self.diff_preview_img = diff_img

                        # 差分画像のサイズをログに出力（デバッグ用）
                        self.logger.debug(
                            f"差分画像: サイズ={diff_img.width}x{diff_img.height}, "
                            f"モード={diff_img.mode}, "
                            f"差分スコア={diff_result.score:.3f}, "
                            f"差分あり={diff_result.has_difference}"
                        )

                        # ラムダで変数をキャプチャして使用
                        diff_img_copy = diff_img.copy()  # 念のためコピーを作成
                        self.root.after(
                            0, lambda img=diff_img_copy: self._update_diff_view(img)
                        )

                        # 差分スコア表示を更新
                        score = diff_result.score
                        self.root.after(
                            0,
                            lambda s=score, h=diff_result.has_difference: self._update_diff_score(
                                s, h
                            ),
                        )

                        if diff_result.has_difference:
                            # 差分があった場合
                            self.logger.info(
                                f"差分を検出しました: {diff_result.score:.2f} "
                                f"(時刻: {datetime.datetime.now().strftime('%H:%M:%S')})"
                            )

                            # 通知（メインスレッドで）
                            if self.config.notification_sound:
                                notify_sound = play_notification_sound
                                self.root.after(0, notify_sound)

                        # 現在のフレームを保存
                        self.prev_image = original_frame

                    # タスク完了を通知
                    self.capture_queue.task_done()

                except queue.Empty:
                    # タイムアウト時は何もしない
                    pass
                except Exception as e:
                    self.logger.error(f"差分検出処理でエラーが発生しました: {e}")

        except Exception as exception:
            self.logger.error(f"差分検出ループでエラーが発生しました: {exception}")

        self.logger.debug("差分検出ループを終了します")

    def _update_diff_score(self, score: float, has_difference: bool) -> None:
        """差分スコアの表示を更新します。

        Args:
            score: 差分スコア（1.0が完全一致、0.0が完全不一致）
            has_difference: 差分検出フラグ
        """
        # スコアを反転させてパーセンテージに変換（0%が完全一致、100%が完全不一致）
        percentage = (1.0 - score) * 100

        # スコアの表示を更新
        self.diff_score_var.set(f"差分スコア: {percentage:.1f}%")

        # テキストカラーを更新
        self.diff_score_label.configure(foreground="red" if has_difference else "black")

    def _init_default_roi(self) -> None:
        """デフォルトのROIを初期化します。"""
        # デフォルトROIはキャンバスの中央部分に設定
        canvas = self.preview_canvas.canvas
        w = canvas.winfo_width()
        h = canvas.winfo_height()

        if w <= 1 or h <= 1:
            # キャンバスがまだ正しくサイズ設定されていない場合は後で再試行
            self.root.after(500, self._init_default_roi)
            return

        # キャンバスの中央80%の領域をROIに設定
        margin_x = w * 0.1
        margin_y = h * 0.1
        canvas_roi = [margin_x, margin_y, w - margin_x, h - margin_y]

        # キャンバス座標を画像座標に変換（画像がまだない場合はキャンバス座標をそのまま使用）
        if self.preview_canvas.current_img:
            x1, y1 = self.preview_canvas.canvas_to_image(canvas_roi[0], canvas_roi[1])
            x2, y2 = self.preview_canvas.canvas_to_image(canvas_roi[2], canvas_roi[3])
            image_roi = [int(x1), int(y1), int(x2), int(y2)]
            self.preview_canvas.set_roi(image_roi)
        else:
            # 適当なデフォルト値（最初のキャプチャ時に調整される）
            self.preview_canvas.set_roi([100, 100, 500, 400])

    def on_exit(self) -> None:
        """アプリケーションを終了します。"""
        if self.capture_running:
            if not messagebox.askyesno(
                "確認", "キャプチャ実行中ですが、終了しますか？"
            ):
                return
            self.on_stop()

        self.root.quit()

    def run(self) -> None:
        """メインループを実行します。"""
        self.root.mainloop()

    def _refresh_and_capture(self) -> None:
        """ウィンドウリストを更新し、選択されたウィンドウのプレビューを表示します。"""
        self._refresh_window_list()

        # 選択されたウィンドウタイトルを取得
        selected_title = self.window_title_var.get()
        if selected_title:
            # 設定に保存
            self.config.window_title = selected_title
            self.config.save()

            try:
                # ウィンドウキャプチャの初期化
                self.window_capture = WindowCapture(selected_title)

                # キャプチャ実行
                frame = self.window_capture.capture()
                if frame is None:
                    messagebox.showerror(
                        "エラー", "ウィンドウのキャプチャに失敗しました。"
                    )
                    return

                # PIL画像に変換
                frame_img = cv_to_pil(frame)
                self.original_frame = frame_img.copy()  # 元画像を保持

                # プレビューに表示（ROIはプレビューキャンバス内で描画される）
                self.preview_canvas.set_image(self.original_frame)

                # ROIが設定されていなければ初期設定
                if self.preview_canvas.get_roi() is None:
                    self._init_default_roi()

                self.logger.info(f"キャプチャを更新しました: {selected_title}")

            except Exception as e:
                self.logger.error(f"キャプチャの更新に失敗しました: {e}")
                messagebox.showerror("エラー", f"キャプチャの更新に失敗しました: {e}")

    def _init_saved_window_preview(self) -> None:
        """保存されているウィンドウタイトルが利用可能な場合、プレビューを表示します。"""
        saved_title = self.config.window_title
        if saved_title:
            # 利用可能なウィンドウタイトル一覧を取得
            available_titles = self._get_window_titles()
            if saved_title in available_titles:
                self.logger.info(
                    f"保存されているウィンドウを読み込みます: {saved_title}"
                )
                self._refresh_and_capture()


def main() -> None:
    """アプリケーションを起動します。"""
    app = MainWindow()
    app.run()
