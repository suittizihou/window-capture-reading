# Tesseractセットアップガイド

このガイドでは、OCRエンジンであるTesseractのセットアップ方法について説明します。

## 前提条件
- Windows 10以降のOS
- Python 3.8以降がインストールされていること

## インストール手順

### 1. Tesseractのインストール

1. [Tesseract公式ダウンロードページ](https://github.com/UB-Mannheim/tesseract/wiki)から、最新のインストーラーをダウンロードします。
   - 64ビットシステムの場合: `tesseract-ocr-w64-setup-vX.XX.XX.exe`
   - 32ビットシステムの場合: `tesseract-ocr-w32-setup-vX.XX.XX.exe`

2. ダウンロードしたインストーラーを実行します。

3. インストール時に以下のオプションを選択してください：
   - 「Additional language data」で「Japanese」を選択
   - 「Additional script data」で必要なスクリプトを選択
   - インストール先を記録しておいてください（デフォルト: `C:\Program Files\Tesseract-OCR`）

4. インストールが完了したら、システム環境変数のPATHにTesseractのインストールディレクトリを追加します：
   - Windowsの検索で「環境変数」と入力し、「システム環境変数の編集」を開く
   - 「環境変数」ボタンをクリック
   - 「システム環境変数」の「Path」を選択し、「編集」をクリック
   - 「新規」をクリックし、Tesseractのインストールパスを追加（例: `C:\Program Files\Tesseract-OCR`）
   - すべてのダイアログで「OK」をクリック

### 2. Pythonパッケージのインストール

1. 必要なPythonパッケージをインストールします：

```powershell
pip install pytesseract pillow numpy opencv-python
```

## 動作確認

1. 以下のPythonスクリプトで動作確認ができます：

```python
import pytesseract
from PIL import Image

# Tesseractのパスを設定（必要な場合）
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# テスト用の画像を読み込んで文字認識を実行
image = Image.open('test_image.png')
text = pytesseract.image_to_string(image, lang='jpn')
print(text)
```

## トラブルシューティング

### Tesseractが見つからない場合

エラーメッセージ: `pytesseract.pytesseract.TesseractNotFoundError`

解決方法:
1. Tesseractが正しくインストールされているか確認
2. システム環境変数のPATHが正しく設定されているか確認
3. Pythonコード内でTesseractのパスを明示的に指定：
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### 日本語が認識されない場合

1. 言語データが正しくインストールされているか確認
2. `lang='jpn'`パラメータが指定されているか確認
3. 必要に応じて画像の前処理（リサイズ、コントラスト調整など）を実施

## 参考リンク

- [Tesseract GitHub](https://github.com/tesseract-ocr/tesseract)
- [pytesseract PyPI](https://pypi.org/project/pytesseract/)
- [Tesseract Documentation](https://tesseract-ocr.github.io/)