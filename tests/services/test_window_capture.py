"""ウィンドウキャプチャ機能のテストモジュール。
"""

import pytest
from PIL import Image
from unittest.mock import MagicMock, patch

from src.services.window_capture import WindowCapture

def test_window_capture_init():
    """ウィンドウキャプチャクラスの初期化をテストします。"""
    window_title = "Test Window"
    capture = WindowCapture(window_title)
    
    assert capture.window_title == window_title
    assert capture.user32 is not None
    assert capture.gdi32 is not None

@patch('src.services.window_capture.WindowCapture.find_window')
def test_capture_window_not_found(mock_find_window):
    """ウィンドウが見つからない場合のテスト。"""
    mock_find_window.return_value = None
    
    capture = WindowCapture("Non-existent Window")
    result = capture.capture()
    
    assert result is None
    mock_find_window.assert_called_once()

@patch('src.services.window_capture.WindowCapture.get_window_rect')
@patch('src.services.window_capture.WindowCapture.find_window')
def test_capture_get_rect_failed(mock_find_window, mock_get_window_rect):
    """ウィンドウの矩形情報取得に失敗した場合のテスト。"""
    mock_find_window.return_value = 12345  # ダミーのウィンドウハンドル
    mock_get_window_rect.return_value = None
    
    capture = WindowCapture("Test Window")
    result = capture.capture()
    
    assert result is None
    mock_find_window.assert_called_once()
    mock_get_window_rect.assert_called_once_with(12345)
