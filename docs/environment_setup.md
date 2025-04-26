# 環境変数の設定方法

本プロジェクトでは、以下の環境変数を使用して各種設定を管理します。

## OCR関連の設定

### TESSERACT_PATH
- 説明: Tesseract OCRの実行ファイルのパス
- デフォルト値: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- 設定例:
  ```powershell
  $env:TESSERACT_PATH = "C:\Program Files\Tesseract-OCR\tesseract.exe"
  ```

### OCR_LANGUAGE
- 説明: OCRで認識する言語
- デフォルト値: `jpn`
- 設定例:
  ```powershell
  $env:OCR_LANGUAGE = "jpn"
  ```

### OCR_CONFIG
- 説明: Tesseractの設定オプション
- デフォルト値: `--psm 6`
- 設定例:
  ```powershell
  $env:OCR_CONFIG = "--psm 6"
  ```

### OCR_PREPROCESSING_ENABLED
- 説明: 画像の前処理を有効にするかどうか
- デフォルト値: `True`
- 設定例:
  ```powershell
  $env:OCR_PREPROCESSING_ENABLED = "True"
  ```

## 環境変数の永続化

Windows PowerShellで環境変数を永続化するには、以下の方法があります：

1. システム環境変数として設定:
   - Windowsの設定 > システム > 詳細情報 > システムの詳細設定 > 環境変数
   - 必要な変数を追加または編集

2. PowerShellプロファイルに追加:
   ```powershell
   # プロファイルファイルを開く
   notepad $PROFILE

   # 以下の内容を追加
   $env:TESSERACT_PATH = "C:\Program Files\Tesseract-OCR\tesseract.exe"
   $env:OCR_LANGUAGE = "jpn"
   $env:OCR_CONFIG = "--psm 6"
   $env:OCR_PREPROCESSING_ENABLED = "True"
   ```

## 設定値の確認方法

現在の設定値を確認するには、以下のコマンドを使用します：

```powershell
Get-ChildItem Env: | Where-Object { $_.Name -like "OCR_*" -or $_.Name -eq "TESSERACT_PATH" }
```