"""設定ダイアログモジュール。

アプリケーションの設定ダイアログを提供します。
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List, Optional, Tuple, Callable, cast, Sequence, TypeVar, Generic, Union, Mapping, MutableMapping, TypedDict, Iterator

from src.utils.config import Config

T = TypeVar('T')

class SettingItem(TypedDict, total=False):
    """設定項目の型定義。"""
    key: str
    label: str
    type: str
    default: Any
    min: float
    max: float
    values: List[str]

class SettingsDialog:
    """設定ダイアログクラス。"""

    def __init__(
        self, 
        parent: tk.Tk, 
        config: Config,
        on_save: Optional[Callable[[Config], None]] = None
    ) -> None:
        """設定ダイアログを初期化します。

        Args:
            parent: 親ウィンドウ
            config: 設定オブジェクト
            on_save: 設定保存時のコールバック
        """
        self.parent = parent
        self.config = config
        self.on_save_callback = on_save
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("設定")
        self.dialog.grab_set()
        self.dialog.focus_set()
        self.dialog.resizable(False, False)
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        # ダイアログを親の中央に配置
        self.center_dialog()
        
        # 値の入力ウィジェットをキーとして保持
        self.bool_vars: Dict[str, tk.BooleanVar] = {}
        self.string_vars: Dict[str, tk.StringVar] = {}
        self.double_vars: Dict[str, tk.DoubleVar] = {}
        self.int_vars: Dict[str, tk.IntVar] = {}
        
        # タブコントロールの作成
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 基本設定タブ
        basic_tab = ttk.Frame(self.notebook)
        self.notebook.add(basic_tab, text="基本設定")
        
        # OCR設定タブ
        ocr_tab = ttk.Frame(self.notebook)
        self.notebook.add(ocr_tab, text="OCR設定")
        
        # 通知設定タブ
        notification_tab = ttk.Frame(self.notebook)
        self.notebook.add(notification_tab, text="通知設定")
        
        # 各タブに設定項目を追加
        basic_settings: List[SettingItem] = [
            {"key": "capture_interval", "label": "キャプチャ間隔(秒)", "type": "float", "min": 0.1, "max": 60.0, "default": 1.0},
            {"key": "window_title", "label": "ウィンドウタイトル", "type": "str", "default": ""},
            {"key": "diff_threshold", "label": "差分検出閾値", "type": "float", "min": 0.0, "max": 1.0, "default": 0.1},
        ]
        
        ocr_settings: List[SettingItem] = [
            {"key": "ocr_enabled", "label": "OCR有効", "type": "bool", "default": True},
            {"key": "ocr_language", "label": "OCR言語", "type": "str", "default": "jpn", "values": ["jpn", "eng", "jpn+eng"]},
            {"key": "ocr_threshold", "label": "OCR検出閾値", "type": "float", "min": 0.0, "max": 1.0, "default": 0.7},
        ]
        
        notification_settings: List[SettingItem] = [
            {"key": "notification_sound", "label": "音声通知", "type": "bool", "default": True},
            {"key": "notification_popup", "label": "ポップアップ通知", "type": "bool", "default": True},
            {"key": "notification_flash", "label": "フラッシュ通知", "type": "bool", "default": False},
        ]
        
        self.create_settings_ui(basic_tab, basic_settings)
        self.create_settings_ui(ocr_tab, ocr_settings)
        self.create_settings_ui(notification_tab, notification_settings)
        
        # ボタンフレーム
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # 保存ボタン
        save_button = ttk.Button(button_frame, text="保存", command=self.on_save)
        save_button.pack(side="right", padx=5)
        
        # キャンセルボタン
        cancel_button = ttk.Button(button_frame, text="キャンセル", command=self.on_cancel)
        cancel_button.pack(side="right", padx=5)

    def center_dialog(self) -> None:
        """ダイアログを親ウィンドウの中央に配置します。"""
        self.dialog.update_idletasks()
        
        # 親ウィンドウの位置とサイズを取得
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # ダイアログのサイズを取得
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        # 中央位置を計算
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # ダイアログを中央に配置
        self.dialog.geometry(f"+{x}+{y}")
        self.dialog.transient(self.parent)

    def create_settings_ui(self, tab: ttk.Frame, settings_list: List[SettingItem]) -> None:
        """設定項目のUIを作成します。

        Args:
            tab: 設定項目を配置するタブ
            settings_list: 設定項目のリスト
        """
        for i, setting in enumerate(settings_list):
            # フレームの作成
            frame = ttk.Frame(tab)
            frame.pack(fill="x", padx=10, pady=5)
            
            # ラベルの作成
            label = ttk.Label(frame, text=setting["label"])
            label.grid(row=0, column=0, sticky="w")
            
            key = setting["key"]
            current_value = getattr(self.config, key, setting.get("default", ""))
            
            # 型に応じた入力ウィジェットの作成
            if setting["type"] == "bool":
                bool_var = tk.BooleanVar(value=bool(current_value))
                ttk.Checkbutton(frame, variable=bool_var).grid(row=0, column=1, sticky="e")
                self.bool_vars[key] = bool_var
                
            elif setting["type"] == "str":
                str_var = tk.StringVar(value=str(current_value))
                if "values" in setting:
                    values = setting.get("values", [])
                    combobox = ttk.Combobox(frame, textvariable=str_var, values=values)
                    combobox.grid(row=0, column=1, sticky="e")
                    combobox.state(["readonly"])
                else:
                    ttk.Entry(frame, textvariable=str_var).grid(row=0, column=1, sticky="e")
                self.string_vars[key] = str_var
                    
            elif setting["type"] == "float":
                dbl_var = tk.DoubleVar(value=float(current_value))
                if "min" in setting and "max" in setting:
                    # スライダーの作成
                    min_val = float(setting["min"])
                    max_val = float(setting["max"])
                    
                    # 値表示ラベル
                    value_label = ttk.Label(frame, text=str(current_value))
                    value_label.grid(row=0, column=2, padx=5)
                    
                    scale = ttk.Scale(
                        frame, 
                        from_=min_val, 
                        to=max_val, 
                        variable=dbl_var, 
                        orient="horizontal"
                    )
                    scale.grid(row=0, column=1, sticky="e")
                    
                    # スライダー変更時のコールバック（ラベル更新用）
                    def on_float_slider_change(event: tk.Event, lbl: ttk.Label, var: tk.DoubleVar) -> None:
                        value = var.get()
                        lbl.config(text=str(value))
                    
                    # lambda型を明示するために関数定義で包む
                    def make_float_slider_callback(lbl: ttk.Label, var: tk.DoubleVar) -> Callable[[tk.Event], None]:
                        return lambda e: on_float_slider_change(e, lbl, var)
                    
                    scale.bind("<Motion>", make_float_slider_callback(value_label, dbl_var))
                else:
                    # 通常の数値入力
                    ttk.Entry(frame, textvariable=dbl_var).grid(row=0, column=1, sticky="e")
                
                self.double_vars[key] = dbl_var
                
            elif setting["type"] == "int":
                int_var = tk.IntVar(value=int(current_value))
                if "min" in setting and "max" in setting:
                    # スライダーの作成
                    min_val = float(setting["min"])
                    max_val = float(setting["max"])
                    
                    # 値表示ラベル
                    value_label = ttk.Label(frame, text=str(current_value))
                    value_label.grid(row=0, column=2, padx=5)
                    
                    # IntVarを使用してスケールウィジェットを作成
                    scale = ttk.Scale(
                        frame, 
                        from_=min_val, 
                        to=max_val, 
                        variable=int_var, 
                        orient="horizontal"
                    )
                    scale.grid(row=0, column=1, sticky="e")
                    
                    # スライダー変更時のコールバック（ラベル更新用）
                    def on_int_slider_change(event: tk.Event, lbl: ttk.Label, var: tk.IntVar) -> None:
                        value = var.get()
                        value_int = int(value)
                        var.set(value_int)
                        lbl.config(text=str(value_int))
                    
                    # lambda型を明示するために関数定義で包む
                    def make_int_slider_callback(lbl: ttk.Label, var: tk.IntVar) -> Callable[[tk.Event], None]:
                        return lambda e: on_int_slider_change(e, lbl, var)
                    
                    scale.bind("<Motion>", make_int_slider_callback(value_label, int_var))
                else:
                    # 通常の数値入力
                    ttk.Entry(frame, textvariable=int_var).grid(row=0, column=1, sticky="e")
                
                self.int_vars[key] = int_var

    def on_save(self) -> None:
        """設定を保存します。"""
        # BooleanVar経由の設定を保存
        for key in self.bool_vars:
            bool_var = self.bool_vars[key]
            setattr(self.config, key, bool_var.get())
        
        # StringVar経由の設定を保存
        for key in self.string_vars:
            str_var = self.string_vars[key]
            setattr(self.config, key, str_var.get())
        
        # DoubleVar経由の設定を保存
        for key in self.double_vars:
            dbl_var = self.double_vars[key]
            setattr(self.config, key, dbl_var.get())
        
        # IntVar経由の設定を保存
        for key in self.int_vars:
            int_var = self.int_vars[key]
            setattr(self.config, key, int_var.get())
        
        # コールバックがあれば呼び出す
        if self.on_save_callback:
            self.on_save_callback(self.config)
        
        # ダイアログを閉じる
        self.dialog.destroy()

    def on_cancel(self) -> None:
        """キャンセル処理を行います。"""
        self.dialog.destroy()

def show_settings_dialog(
    parent: tk.Tk, 
    config: Config, 
    on_save: Optional[Callable[[Config], None]] = None
) -> None:
    """設定ダイアログを表示します。

    Args:
        parent: 親ウィンドウ
        config: 設定オブジェクト
        on_save: 設定保存時のコールバック
    """
    SettingsDialog(parent, config, on_save) 