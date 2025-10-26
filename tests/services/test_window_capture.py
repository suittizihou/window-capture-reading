"""ウィンドウキャプチャ機能のテストモジュール。"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch, Mock
from typing import Optional, cast

from src.services.window_capture import WindowCapture


@patch("src.services.window_capture.WindowsCapture")
def test_window_capture_init(mock_windows_capture: MagicMock) -> None:
    """ウィンドウキャプチャクラスの初期化をテストします（遅延初期化）。"""
    window_title = "Test Window"
    mock_instance = MagicMock()
    mock_windows_capture.return_value = mock_instance

    capture = WindowCapture(window_title)

    assert capture.window_title == window_title
    assert capture.latest_frame is None
    # 遅延初期化なので、初期化時点では開始されていない
    assert capture.capture_started is False
    assert capture.win_capture is None
    # 初期化時点ではstart_free_threadedは呼ばれない
    mock_instance.start_free_threaded.assert_not_called()


@patch("src.services.window_capture.WindowsCapture")
def test_capture_no_frame_yet(mock_windows_capture: MagicMock) -> None:
    """まだフレームが到着していない場合のテスト。"""
    mock_instance = MagicMock()
    mock_windows_capture.return_value = mock_instance

    # eventデコレータのモック
    def mock_event(func):
        return func

    mock_instance.event = mock_event

    capture = WindowCapture("Test Window")
    result = capture.capture()

    # 初回capture()呼び出しで初期化される
    mock_instance.start_free_threaded.assert_called_once()
    assert result is None


@patch("src.services.window_capture.WindowsCapture")
def test_capture_with_frame(mock_windows_capture: MagicMock) -> None:
    """フレームが到着している場合のテスト。"""
    mock_instance = MagicMock()
    mock_windows_capture.return_value = mock_instance

    # eventデコレータのモック
    def mock_event(func):
        return func

    mock_instance.event = mock_event

    capture = WindowCapture("Test Window")

    # ダミーフレームを設定
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    capture.latest_frame = dummy_frame
    capture.capture_started = True  # 初期化済みと見なす

    result = capture.capture()

    assert result is not None
    assert result.shape == (100, 100, 3)
    # コピーが返されることを確認
    assert not np.shares_memory(result, dummy_frame)


@patch("src.services.window_capture.WindowsCapture")
def test_capture_failed(mock_windows_capture: MagicMock) -> None:
    """キャプチャが失敗した場合のテスト。"""
    mock_instance = MagicMock()
    mock_windows_capture.return_value = mock_instance

    capture = WindowCapture("Test Window")
    capture.capture_failed = True
    capture.capture_started = True  # 初期化済みと見なす

    result = capture.capture()

    assert result is None


@patch("src.services.window_capture.WindowsCapture")
def test_find_window(mock_windows_capture: MagicMock) -> None:
    """find_windowメソッドのテスト。"""
    mock_instance = MagicMock()
    mock_windows_capture.return_value = mock_instance

    capture = WindowCapture("Test Window")
    capture.capture_started = True  # 初期化済みと見なす

    # キャプチャが開始されている場合
    result = capture.find_window()
    assert result == 1

    # キャプチャが失敗している場合
    capture.capture_failed = True
    result = capture.find_window()
    assert result is None


@patch("src.services.window_capture.WindowsCapture")
def test_stop(mock_windows_capture: MagicMock) -> None:
    """stopメソッドのテスト。"""
    mock_instance = MagicMock()
    mock_windows_capture.return_value = mock_instance

    # eventデコレータのモック
    def mock_event(func):
        return func

    mock_instance.event = mock_event

    # capture_controlのモック（start_free_threaded()の戻り値）
    mock_capture_control = MagicMock()
    mock_instance.start_free_threaded.return_value = mock_capture_control

    capture = WindowCapture("Test Window")
    # 初期化を実行
    capture._initialize_capture()
    capture.stop()

    mock_capture_control.stop.assert_called_once()
    assert capture.capture_started is False


@patch("src.services.window_capture.WindowsCapture")
def test_event_handler_integration(mock_windows_capture: MagicMock) -> None:
    """イベントハンドラーの統合テスト。"""
    mock_instance = MagicMock()
    mock_windows_capture.return_value = mock_instance

    # eventデコレータのモック
    event_handlers = {}

    def mock_event(func):
        event_handlers[func.__name__] = func
        return func

    mock_instance.event = mock_event

    capture = WindowCapture("Test Window")
    # 遅延初期化を実行
    capture._initialize_capture()

    # on_frame_arrivedハンドラーが登録されていることを確認
    assert "on_frame_arrived" in event_handlers
    assert "on_closed" in event_handlers

    # on_closedハンドラーをテスト
    on_closed = event_handlers["on_closed"]
    on_closed()
    assert capture.capture_started is False


@patch("src.services.window_capture.WindowsCapture")
def test_initialization_failure(mock_windows_capture: MagicMock) -> None:
    """初期化が失敗した場合のテスト。"""
    mock_windows_capture.side_effect = Exception("Initialization failed")

    capture = WindowCapture("Test Window")
    # 初期化を試みる（失敗する）
    result = capture._initialize_capture()

    assert result is False
    assert capture.capture_failed is True
    assert capture.capture_started is False


@patch("src.services.window_capture.WindowsCapture")
def test_destructor(mock_windows_capture: MagicMock) -> None:
    """デストラクタのテスト。"""
    mock_instance = MagicMock()
    mock_windows_capture.return_value = mock_instance

    # eventデコレータのモック
    def mock_event(func):
        return func

    mock_instance.event = mock_event

    # capture_controlのモック（start_free_threaded()の戻り値）
    mock_capture_control = MagicMock()
    mock_instance.start_free_threaded.return_value = mock_capture_control

    capture = WindowCapture("Test Window")
    # 初期化を実行
    capture._initialize_capture()
    capture.__del__()

    mock_capture_control.stop.assert_called()


@patch("src.services.window_capture.WindowsCapture")
def test_lazy_initialization_on_capture(mock_windows_capture: MagicMock) -> None:
    """capture()呼び出し時の遅延初期化をテスト。"""
    mock_instance = MagicMock()
    mock_windows_capture.return_value = mock_instance

    # eventデコレータのモック
    def mock_event(func):
        return func

    mock_instance.event = mock_event

    capture = WindowCapture("Test Window")

    # 初期化前は未開始
    assert capture.capture_started is False

    # capture()呼び出しで初期化される
    capture.capture()

    # 初期化が実行された
    mock_windows_capture.assert_called_once_with(
        window_name="Test Window", cursor_capture=False, draw_border=False
    )
    mock_instance.start_free_threaded.assert_called_once()
    assert capture.capture_started is True
