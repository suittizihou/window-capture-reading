# Tesseract OCRのセットアップガイド

このドキュメントでは、Window Capture ReadingアプリケーションでOCR機能を使用するために必要なTesseract OCRのインストールと設定方法を説明します。

## Windowsへのインストール

1. [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)から最新のインストーラーをダウンロードします。
   - 64ビット版を推奨: `tesseract-ocr-w64-setup-vX.X.X.exe`

2. インストーラーを実行し、以下のオプションを選択します：
   - 言語データパックで「Japanese」を必ず選択
   - インストール先は標準の `C:\Program Files\Tesseract-OCR` を推奨

3. 環境変数のセットアップ:
   - インストール時に「PATHにTesseract実行ファイルへのパスを追加する」にチェックを入れることをおすすめします
   - 手動で追加する場合は、システム環境変数の `Path` に `C:\Program Files\Tesseract-OCR` を追加します

## インストール確認

PowerShellで以下のコマンドを実行して、Tesseractが正しくインストールされていることを確認します：

```powershell
tesseract --version
```

正しくインストールされていれば、バージョン情報が表示されます。

## アプリケーションの設定

1. `.env` ファイルにTesseractのパスを設定します：

```
TESSERACT_PATH=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
OCR_LANGUAGE=jpn
OCR_CONFIG=--psm 6
```

2. パスに特殊文字やスペースが含まれる場合は、バックスラッシュを二重にして正しくエスケープしてください。

## トラブルシューティング

### Tesseractが見つからない場合

以下のエラーが表示された場合：
```
TesseractNotFoundError: tesseract is not installed or it's not in your PATH.
```

1. Tesseractが正しくインストールされていることを確認
2. `.env` ファイルで `TESSERACT_PATH` が正しく設定されていることを確認
3. システムを再起動して環境変数の変更を反映

### 言語データが見つからない場合

以下のエラーが表示された場合：
```
Error opening data file: Error:Failed loading language 'jpn'
```

1. インストーラーを再実行し、日本語言語パックを選択
2. `C:\Program Files\Tesseract-OCR\tessdata` フォルダに `jpn.traineddata` ファイルが存在することを確認

## 参考リンク

- [Tesseract OCR公式ドキュメント](https://tesseract-ocr.github.io/)
- [pytesseractドキュメント](https://pypi.org/project/pytesseract/)
- [UB-Mannheim Tesseractインストールガイド](https://github.com/UB-Mannheim/tesseract/wiki) 