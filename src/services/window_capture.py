"""ウィンドウキャプチャ機能を提供するモジュール。

Windows.Graphics.Capture APIを使用して、指定されたウィンドウのキャプチャを行います。
"""

import logging
import threading
from typing import Optional, cast, Any
import numpy as np
from numpy.typing import NDArray

try:
    from windows_capture import WindowsCapture, Frame, InternalCaptureControl  # type: ignore
except ImportError as e:
    raise ImportError(
        "windows-captureライブラリがインストールされていません。"
        "pip install windows-capture を実行してください。"
    ) from e

# 画像処理関連の型定義
ImageArray = NDArray[np.uint8]


class WindowCapture:
    """ウィンドウキャプチャ機能を提供するクラス。

    Windows.Graphics.Capture APIを使用して、指定されたウィンドウタイトルの
    ウィンドウをキャプチャします。イベント駆動型でバックグラウンドで
    キャプチャを実行し、最新のフレームを保持します。
    """

    def __init__(self, window_title: str, draw_border: bool = False, cursor_capture: bool = False) -> None:
        """ウィンドウキャプチャクラスを初期化します。

        Args:
            window_title: キャプチャ対象のウィンドウタイトル
            draw_border: キャプチャ時に枠を表示するか（デフォルト: False）
            cursor_capture: マウスカーソルをキャプチャするか（デフォルト: False）
        """
        self.window_title = window_title
        self.draw_border = draw_border
        self.cursor_capture = cursor_capture
        self.logger = logging.getLogger(__name__)

        # 最新フレームを保存するための変数
        self.latest_frame: Optional[ImageArray] = None
        self.frame_lock = threading.Lock()
        self.capture_started = False
        self.capture_failed = False
        self.win_capture: Optional[WindowsCapture] = None
        self.capture_control: Optional[Any] = None  # CaptureControlを保存
        self.initialization_attempted = False

    def _initialize_capture(self) -> bool:
        """WindowsCaptureを初期化します（遅延初期化）。

        Returns:
            初期化が成功した場合はTrue、失敗した場合はFalse
        """
        if self.capture_started:
            return True

        if self.initialization_attempted and self.capture_failed:
            # 以前に初期化を試みて失敗している場合はスキップ
            return False

        self.initialization_attempted = True

        try:
            self.win_capture = WindowsCapture(
                window_name=self.window_title,
                cursor_capture=self.cursor_capture,
                draw_border=self.draw_border,
            )

            # イベントハンドラーの設定
            @self.win_capture.event
            def on_frame_arrived(
                frame: Frame, capture_control: InternalCaptureControl
            ) -> None:
                """フレームが到着したときに呼び出されるイベントハンドラー。

                Args:
                    frame: キャプチャされたフレーム
                    capture_control: キャプチャ制御オブジェクト
                """
                try:
                    # BGRに変換してフレームを取得
                    # convert_to_bgr()はBGRA (H, W, 4) から BGR (H, W, 3) に変換
                    bgr_frame = frame.convert_to_bgr()
                    frame_data = bgr_frame.frame_buffer

                    if frame_data is not None and len(frame_data.shape) == 3:
                        with self.frame_lock:
                            self.latest_frame = cast(ImageArray, frame_data.copy())
                            self.capture_failed = False
                except Exception as e:
                    self.logger.error(f"フレーム処理中にエラー: {e}", exc_info=True)
                    with self.frame_lock:
                        self.capture_failed = True

            @self.win_capture.event
            def on_closed() -> None:
                """キャプチャセッションが閉じられたときに呼び出されるイベントハンドラー。"""
                self.logger.info("キャプチャセッションが閉じられました")
                with self.frame_lock:
                    self.capture_started = False

            # キャプチャを開始し、CaptureControlを保存
            self.capture_control = self.win_capture.start_free_threaded()
            self.capture_started = True
            self.capture_failed = False
            self.logger.info(f"ウィンドウ '{self.window_title}' のキャプチャを開始しました")
            return True

        except Exception as e:
            self.logger.warning(
                f"ウィンドウ '{self.window_title}' が見つかりません。"
                f"ウィンドウが開いているか確認してください。"
            )
            self.logger.debug(f"詳細なエラー情報: {e}", exc_info=True)
            self.capture_failed = True
            return False

    def find_window(self) -> Optional[int]:
        """指定されたタイトルのウィンドウハンドルを取得します。

        注: この メソッドは互換性のために残されていますが、
        windows-captureライブラリが内部でウィンドウ検索を行うため、
        直接使用する必要はありません。

        Returns:
            ウィンドウが見つかった場合は1、それ以外は None。
        """
        if self.capture_started and not self.capture_failed:
            return 1
        return None

    def capture(self) -> Optional[ImageArray]:
        """最新のキャプチャフレームを取得します。

        初回呼び出し時にキャプチャを初期化します（遅延初期化）。

        Returns:
            キャプチャした画像（BGR形式のnumpy配列）。失敗時はNone。
        """
        # 初期化がまだの場合は初期化を試みる
        if not self.capture_started:
            if not self._initialize_capture():
                return None

        with self.frame_lock:
            if self.capture_failed:
                return None

            if self.latest_frame is None:
                # まだフレームが到着していない
                return None

            # コピーを返す（スレッドセーフのため）
            return self.latest_frame.copy()

    def stop(self) -> None:
        """キャプチャを停止します。"""
        if self.capture_started and self.capture_control is not None:
            try:
                self.capture_control.stop()
                self.capture_started = False
                self.logger.info(
                    f"ウィンドウ '{self.window_title}' のキャプチャを停止しました"
                )
            except Exception as e:
                self.logger.error(f"キャプチャの停止中にエラー: {e}", exc_info=True)

    def __del__(self) -> None:
        """デストラクタ。クリーンアップ処理を実行します。"""
        self.stop()
