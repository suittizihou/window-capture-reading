# Tesseract OCRのセットアップガイド

このドキュメントでは、Window Capture ReadingアプリケーションでOCR機能を使用するために必要なTesseract OCRのインストールと設定方法を説明します。

## 前提条件
- Windows 10以降のOS
- Python 3.8以降がインストールされていること

## インストール手順

### 1. Tesseractのインストール

1. [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)から最新のインストーラーをダウンロードします。
   - 64ビット版を推奨: `tesseract-ocr-w64-setup-vX.X.X.exe`
   - 32ビットシステムの場合: `tesseract-ocr-w32-setup-vX.X.X.exe`

2. インストーラーを実行し、以下のオプションを選択します：
   - 言語データパックで「Japanese」を必ず選択
   - インストール先は標準の `C:\Program Files\Tesseract-OCR` を推奨
   - 「PATHにTesseract実行ファイルへのパスを追加する」にチェックを入れることをおすすめします

3. 手動で環境変数を設定する場合：
   - Windowsの検索で「環境変数」と入力し、「システム環境変数の編集」を開く
   - 「環境変数」ボタンをクリック
   - 「システム環境変数」の「Path」を選択し、「編集」をクリック
   - 「新規」をクリックし、Tesseractのインストールパスを追加（例: `C:\Program Files\Tesseract-OCR`）
   - すべてのダイアログで「OK」をクリック

### 2. インストール確認

PowerShellで以下のコマンドを実行して、Tesseractが正しくインストールされていることを確認します：

```powershell
tesseract --version
```

正しくインストールされていれば、バージョン情報が表示されます。

### 3. Pythonパッケージのインストール

必要なPythonパッケージをインストールします：

```powershell
pip install pytesseract pillow numpy opencv-python
```

## アプリケーションの設定

1. `.env` ファイルにTesseractのパスを設定します：

```
TESSERACT_PATH=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
OCR_LANGUAGE=jpn
OCR_CONFIG=--psm 6
```

2. パスに特殊文字やスペースが含まれる場合は、バックスラッシュを二重にして正しくエスケープしてください。

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

以下のエラーが表示された場合：
```
TesseractNotFoundError: tesseract is not installed or it's not in your PATH.
```

1. Tesseractが正しくインストールされていることを確認
2. `.env` ファイルで `TESSERACT_PATH` が正しく設定されていることを確認
3. システム環境変数のPATHが正しく設定されているか確認
4. システムを再起動して環境変数の変更を反映
5. Pythonコード内でTesseractのパスを明示的に指定：
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### 言語データが見つからない場合

以下のエラーが表示された場合：
```
Error opening data file: Error:Failed loading language 'jpn'
```

1. インストーラーを再実行し、日本語言語パックを選択
2. `C:\Program Files\Tesseract-OCR\tessdata` フォルダに `jpn.traineddata` ファイルが存在することを確認

### 日本語が認識されない場合

1. 言語データが正しくインストールされているか確認
2. `lang='jpn'`パラメータが指定されているか確認
3. 必要に応じて画像の前処理（リサイズ、コントラスト調整など）を実施

## 参考リンク

- [Tesseract GitHub](https://github.com/tesseract-ocr/tesseract)
- [pytesseract PyPI](https://pypi.org/project/pytesseract/)
- [Tesseract Documentation](https://tesseract-ocr.github.io/)
- [UB-Mannheim Tesseractインストールガイド](https://github.com/UB-Mannheim/tesseract/wiki)
