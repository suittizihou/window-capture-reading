"""共通の型定義モジュール。

アプリケーション全体で使用される型定義を提供します。
"""

from typing import Union, Any
import numpy as np
from numpy.typing import NDArray

# 画像処理関連の型定義
# OpenCVの画像型として、複数の型が許容されるようUnion型で定義
ImageArray = Union[NDArray[np.uint8], NDArray[Any]]
