"""
PySimpleGUIによるWindow Capture Reading Toolの初期GUI/UX設計（完成版）。

- ウィンドウタイトル表示
- Start/Stopボタン
- ステータスバー（日本語・色分け）
- OCRライブプレビュー（自動スクロール・選択不可）
- エラーハンドリング強化

PEP8/PEP257/型アノテーション/ロギング/エラーハンドリング準拠。
"""

import PySimpleGUI as sg
import threading
import logging
from typing import Optional
from src.services.window_capture import WindowCapture
from src.services.ocr_service import OCRService
from src.services.bouyomi_client import BouyomiClient
from src.utils.config import Config
from src.utils.logging_config import setup_logging


def main(window_title: Optional[str] = None) -> None:
    """
    Window Capture Reading ToolのPySimpleGUI版メインエントリ。
    Args:
        window_title: ターゲットウィンドウ名（省略可）
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    config = Config()
    sg.theme('SystemDefault')

    # GUIレイアウト
    layout = [
        [sg.Text(f'ターゲットウィンドウ: {window_title or config.get("TARGET_WINDOW_TITLE", "LDPlayer")}', key='-TITLE-', font=('Meiryo', 14), size=(50, 1))],
        [sg.Multiline('まだテキストは検出されていません', key='-OCR-', font=('Meiryo', 12), size=(60, 4), disabled=True, autoscroll=True, no_scrollbar=True, background_color='#f8f8f8')],
        [sg.Button('開始', key='-START-', size=(10, 1)), sg.Button('停止', key='-STOP-', size=(10, 1), disabled=True)],
        [sg.Text('停止中', key='-STATUS-', font=('Meiryo', 10), background_color='#f0f0f0', size=(60, 1))],
    ]

    window = sg.Window('Window Capture Reading (PySimpleGUI)', layout, finalize=True, resizable=False)

    running: threading.Event = threading.Event()
    running.clear()
    ocr_thread: Optional[threading.Thread] = None

    def set_status(state: str) -> None:
        """
        ステータスバーの状態を日本語で更新し、色分けする。
        Args:
            state: 'Running', 'Stopped', 'Error' など
        """
        if state == 'Running':
            window['-STATUS-'].update('稼働中', background_color='#d0ffd0')
        elif state == 'Error':
            window['-STATUS-'].update('エラー', background_color='#ffd0d0')
        else:
            window['-STATUS-'].update('停止中', background_color='#f0f0f0')

    def show_error_dialog(message: str) -> None:
        """
        エラー発生時にユーザーへダイアログ表示。
        Args:
            message: エラーメッセージ
        """
        sg.popup_error('エラーが発生しました', message, title='エラー', keep_on_top=True)

    def ocr_loop() -> None:
        """
        OCR・読み上げメインループ（スレッド用）。
        例外時はGUIに通知。
        """
        window_capture = WindowCapture(config.get("TARGET_WINDOW_TITLE", "LDPlayer"))
        ocr_service = OCRService(config)
        bouyomi_enabled = str(config.get("BOUYOMI_ENABLED", "true")).lower() == "true"
        bouyomi_client = BouyomiClient(config) if bouyomi_enabled else None
        last_text: str = ''
        try:
            while running.is_set():
                frame = window_capture.capture()
                if frame is not None:
                    text = ocr_service.extract_text(frame)
                    if text and text != last_text:
                        window.write_event_value('-OCR-UPDATE-', text)
                        last_text = text
                import time
                time.sleep(float(config.get("CAPTURE_INTERVAL", "1.0")))
        except Exception as e:
            logger.error(f"OCRループでエラー: {e}", exc_info=True)
            window.write_event_value('-ERROR-', str(e))
        finally:
            if bouyomi_client:
                bouyomi_client.close()

    # イベントループ
    while True:
        event, values = window.read(timeout=100)
        if event == sg.WIN_CLOSED:
            running.clear()
            break
        elif event == '-START-':
            if not running.is_set():
                running.set()
                set_status('Running')
                window['-START-'].update(disabled=True)
                window['-STOP-'].update(disabled=False)
                ocr_thread = threading.Thread(target=ocr_loop, daemon=True)
                ocr_thread.start()
        elif event == '-STOP-':
            running.clear()
            set_status('Stopped')
            window['-START-'].update(disabled=False)
            window['-STOP-'].update(disabled=True)
        elif event == '-OCR-UPDATE-':
            text = values.get('-OCR-UPDATE-', '')
            window['-OCR-'].update(text)
        elif event == '-ERROR-':
            set_status('Error')
            show_error_dialog(values.get('-ERROR-', '不明なエラー'))

    window.close()


if __name__ == '__main__':
    main() 