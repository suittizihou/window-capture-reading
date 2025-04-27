import PySimpleGUI as sg
import threading
import queue
import time
from typing import Optional
from src.main import run_main_loop


def main(window_title: Optional[str] = None) -> None:
    """
    PySimpleGUIで実装したOCRテキストライブプレビュー付きGUI。
    - 最新のOCR認識テキストをリアルタイムで表示
    - Start/Stopボタンでメイン処理を制御
    - ステータスバーでシステム状態を表示

    Args:
        window_title: 現在ターゲットとなっているウィンドウ名
    """
    # OCRテキスト受信用キュー
    ocr_text_queue = queue.Queue()
    running = threading.Event()
    running.clear()

    # GUIレイアウト
    layout = [
        [sg.Text(f'ターゲットウィンドウ: {window_title or "(未設定)"}', key='-TITLE-', font=("Meiryo", 14), size=(40, 1))],
        [sg.Multiline('まだテキストは検出されていません', key='-OCR-', size=(60, 5), font=("Meiryo", 12), disabled=True, autoscroll=True)],
        [sg.Button('Start', key='-START-', size=(10, 1)), sg.Button('Stop', key='-STOP-', size=(10, 1), disabled=True), sg.Button('終了', key='-EXIT-', size=(10, 1))],
        [sg.Text('Stopped', key='-STATUS-', font=("Meiryo", 10), size=(40, 1), background_color='#f0f0f0')]
    ]

    window = sg.Window('Window Capture Reading', layout, finalize=True, resizable=False)

    def set_status(state: str) -> None:
        """ステータスバーの状態を更新する。"""
        color = {'Running': '#d0ffd0', 'Error': '#ffd0d0'}.get(state, '#f0f0f0')
        window['-STATUS-'].update(state, background_color=color)

    def ocr_loop():
        """OCR・読み上げメインループを別スレッドで実行し、テキストをキューに送る。"""
        from src.services.window_capture import WindowCapture
        from src.services.ocr_service import OCRService
        from src.utils.config import Config
        import logging
        config = Config()
        window_capture = WindowCapture(config.get("TARGET_WINDOW_TITLE", "LDPlayer"))
        ocr_service = OCRService(config)
        last_text = ''
        while running.is_set():
            frame = window_capture.capture()
            if frame is not None:
                text = ocr_service.extract_text(frame)
                if text and text != last_text:
                    ocr_text_queue.put(text)
                    last_text = text
            time.sleep(float(config.get("CAPTURE_INTERVAL", "1.0")))

    ocr_thread = None

    while True:
        event, values = window.read(timeout=200)
        if event in (sg.WIN_CLOSED, '-EXIT-'):
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
        # OCRテキストのライブ更新
        try:
            while True:
                text = ocr_text_queue.get_nowait()
                window['-OCR-'].update(text)
        except queue.Empty:
            pass

    window.close()


if __name__ == '__main__':
    main(window_title="LDPlayer")
