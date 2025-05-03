"""GUIユーティリティ関数モジュール。

GUI関連のユーティリティ関数を提供します。
"""

import os
import logging
import numpy as np
from PIL import Image
import cv2
from typing import Tuple, cast
from numpy.typing import NDArray
from src.utils.resource_path import get_sound_file_path

# 画像処理関連の型定義
ImageArray = NDArray[np.uint8]

# 表示関連定数
MAX_TITLE_DISPLAY_LENGTH = 24  # 表示上限（全角換算で調整可）


def pil_to_cv(pil_image: Image.Image) -> ImageArray:
    """PIL画像をOpenCV形式に変換します。

    Args:
        pil_image: PIL画像

    Returns:
        OpenCV形式の画像（BGR）
    """
    # PIL画像をRGBに変換
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")

    # PIL -> NumPy配列（RGB）
    np_image = np.array(pil_image)

    # RGB -> BGR（OpenCVの形式）
    cv_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)

    return cast(ImageArray, cv_image)


def cv_to_pil(cv_image: ImageArray) -> Image.Image:
    """OpenCV形式の画像をPIL形式に変換します。

    Args:
        cv_image: OpenCV形式の画像（BGR）

    Returns:
        PIL形式の画像
    """
    # BGR -> RGB（PILの形式）
    rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)

    # NumPy配列 -> PIL
    pil_image = Image.fromarray(rgb_image)

    return pil_image


def play_notification_sound() -> bool:
    """通知音を再生する。

    Returns:
        bool: 再生に成功した場合はTrue、失敗した場合はFalse
    """
    try:
        import winsound

        sound_path = str(get_sound_file_path())
        if not os.path.exists(sound_path):
            logging.warning(f"通知音ファイルが見つかりません: {sound_path}")
            return False

        winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        return True
    except Exception as e:
        logging.error(f"通知音の再生に失敗しました: {e}")
        return False


def ellipsize(text: str, max_length: int = MAX_TITLE_DISPLAY_LENGTH) -> str:
    """長すぎるテキストを...で省略して返す。

    Args:
        text: 元のテキスト
        max_length: 最大表示文字数

    Returns:
        省略後のテキスト
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
