"""設定ダイアログモジュール。

アプリケーションの設定ダイアログを提供します。
"""

import tkinter as tk
from tkinter import ttk
from typing import (
    Dict,
    Any,
    List,
    Optional,
    Tuple,
    Callable,
    cast,
    Sequence,
    TypeVar,
    Generic,
    Union,
    Mapping,
    MutableMapping,
    TypedDict,
    Iterator,
)

from src.utils.config import Config

T = TypeVar("T")


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
        on_save: Optional[Callable[[Config], None]] = None,
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
        self.bool_vars: Dict[str, tk.Variable] = {}  # BooleanVarを含む汎用型
        self.string_vars: Dict[str, tk.Variable] = {}  # StringVarを含む汎用型
        self.double_vars: Dict[str, tk.Variable] = {}  # DoubleVarを含む汎用型
        self.int_vars: Dict[str, tk.Variable] = {}  # IntVarを含む汎用型

        # タブコントロールの作成
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # 基本設定タブ
        basic_tab = ttk.Frame(self.notebook)
        self.notebook.add(basic_tab, text="基本設定")

        # 通知設定タブ
        notification_tab = ttk.Frame(self.notebook)
        self.notebook.add(notification_tab, text="通知設定")

        # 各タブに設定項目を追加
        basic_settings: List[SettingItem] = [
            {
                "key": "capture_interval",
                "label": "キャプチャ間隔(秒)",
                "type": "float_entry",
                "min": 0.1,
                "max": 60.0,
                "default": 1.0,
            },
            {
                "key": "draw_border",
                "label": "キャプチャ時に枠を表示",
                "type": "bool",
                "default": False,
            },
            {
                "key": "cursor_capture",
                "label": "マウスカーソルをキャプチャ",
                "type": "bool",
                "default": False,
            },
            {
                "key": "diff_threshold",
                "label": "差分検出閾値(%)",
                "type": "float",
                "min": 0.0,
                "max": 100.0,
                "default": 10.0,
            },
            {
                "key": "diff_method",
                "label": "差分検出方法",
                "type": "str",
                "values": ["ssim", "absdiff"],
                "default": "ssim",
            },
        ]

        notification_settings: List[SettingItem] = [
            {
                "key": "notification_sound",
                "label": "音声通知",
                "type": "bool",
                "default": True,
            },
        ]

        self.create_settings_ui(basic_tab, basic_settings)
        self.create_settings_ui(notification_tab, notification_settings)

        # ボタンフレーム
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))

        # 保存ボタン
        save_button = ttk.Button(button_frame, text="保存", command=self.on_save)
        save_button.pack(side="right", padx=5)

        # キャンセルボタン
        cancel_button = ttk.Button(
            button_frame, text="キャンセル", command=self.on_cancel
        )
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

    def create_settings_ui(
        self, tab: ttk.Frame, settings_list: List[SettingItem]
    ) -> None:
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

            # 差分検出閾値の場合は、内部値（0-1）をパーセント（0-100）に変換
            if key == "diff_threshold":
                current_value = float(current_value) * 100

            # 型に応じた入力ウィジェットの作成
            if setting["type"] == "bool":
                bool_var = tk.BooleanVar(value=bool(current_value))
                ttk.Checkbutton(frame, variable=bool_var, takefocus=False).grid(
                    row=0, column=1
                )
                self.bool_vars[key] = bool_var

            elif setting["type"] == "str":
                str_var = tk.StringVar(value=str(current_value))
                if "values" in setting:
                    values = setting.get("values", [])
                    combobox = ttk.Combobox(frame, textvariable=str_var, values=values)
                    combobox.grid(row=0, column=1, sticky="e")
                    combobox.state(["readonly"])
                else:
                    ttk.Entry(frame, textvariable=str_var).grid(
                        row=0, column=1, sticky="e"
                    )
                self.string_vars[key] = str_var

            elif setting["type"] == "float_entry":
                dbl_var = tk.DoubleVar(value=float(current_value))
                entry = ttk.Entry(frame, width=10, textvariable=dbl_var)
                entry.grid(row=0, column=1, sticky="e")

                def validate_float(action: str, value: str) -> bool:
                    if action == "1":  # 挿入時
                        try:
                            if value == "":
                                return True
                            float_val = float(value)
                            min_val = float(setting.get("min", 0.0))
                            max_val = float(setting.get("max", float("inf")))
                            return min_val <= float_val <= max_val
                        except ValueError:
                            return False
                    return True

                vcmd = (frame.register(validate_float), "%d", "%P")
                entry.configure(validate="key", validatecommand=vcmd)
                self.double_vars[key] = dbl_var

            elif setting["type"] == "float":
                dbl_var = tk.DoubleVar(value=float(current_value))
                if "min" in setting and "max" in setting:
                    min_val = float(setting["min"])
                    max_val = float(setting["max"])

                    # 値表示ラベル
                    value_label = ttk.Label(frame, text=f"{current_value:.1f}%")
                    value_label.grid(row=0, column=3, padx=5)

                    # スライダー
                    scale = ttk.Scale(
                        frame,
                        from_=min_val,
                        to=max_val,
                        variable=dbl_var,
                        orient="horizontal",
                    )
                    scale.grid(row=0, column=1, sticky="e")

                    # Entry（数値入力）
                    entry = ttk.Entry(frame, width=7)
                    entry.grid(row=0, column=2, sticky="e")

                    # Entryのバリデーション
                    def validate_float_entry(action: str, value: str) -> bool:
                        if action == "1":  # 挿入時
                            try:
                                if value == "":
                                    return True
                                float_val = float(value)
                                return min_val <= float_val <= max_val
                            except ValueError:
                                return False
                        return True

                    vcmd = (frame.register(validate_float_entry), "%d", "%P")
                    entry.configure(validate="key", validatecommand=vcmd)

                    # EntryとDoubleVarの同期
                    def on_var_changed(*args: object) -> None:
                        value = dbl_var.get()
                        entry.delete(0, tk.END)
                        entry.insert(0, f"{value:.1f}")
                        value_label.config(text="%")

                    def on_entry_changed(event: tk.Event) -> None:
                        try:
                            value = float(entry.get())
                            if min_val <= value <= max_val:
                                dbl_var.set(value)
                        except ValueError:
                            pass  # 無効な値は無視

                    # DoubleVarが変わったときにEntryとラベルを更新
                    dbl_var.trace_add("write", lambda *args: on_var_changed())
                    # EntryでEnter押下またはフォーカスアウト時にDoubleVarを更新
                    entry.bind("<Return>", on_entry_changed)
                    entry.bind("<FocusOut>", on_entry_changed)

                    # 初期値反映
                    entry.delete(0, tk.END)
                    entry.insert(0, f"{dbl_var.get():.1f}")
                    value_label.config(text="%")

                    # スライダーの動きでラベル・Entryも更新（traceで十分なのでbindは不要）
                else:
                    ttk.Entry(frame, textvariable=dbl_var).grid(
                        row=0, column=1, sticky="e"
                    )
                self.double_vars[key] = dbl_var

    def on_save(self) -> None:
        """設定を保存します。"""
        # 各設定値を取得して保存
        # BooleanVarのみ
        for key, var in self.bool_vars.items():
            setattr(self.config, key, bool(var.get()))

        # StringVarのみ
        for key, var in self.string_vars.items():
            setattr(self.config, key, str(var.get()))

        # DoubleVarのみ
        for key, var in self.double_vars.items():
            value = float(var.get())
            # 差分検出閾値の場合は、パーセント（0-100）から内部値（0-1）に変換
            if key == "diff_threshold":
                value = value / 100.0
            setattr(self.config, key, value)

        # IntVarのみ
        for key, var in self.int_vars.items():
            setattr(self.config, key, int(var.get()))

        # 設定をファイルに保存
        self.config.save()

        # 保存コールバックを呼び出し
        if self.on_save_callback:
            self.on_save_callback(self.config)

        self.dialog.destroy()

    def on_cancel(self) -> None:
        """キャンセル処理を行います。"""
        self.dialog.destroy()


def show_settings_dialog(
    parent: tk.Tk, config: Config, on_save: Optional[Callable[[Config], None]] = None
) -> None:
    """設定ダイアログを表示します。

    Args:
        parent: 親ウィンドウ
        config: 設定オブジェクト
        on_save: 設定保存時のコールバック
    """
    SettingsDialog(parent, config, on_save)
