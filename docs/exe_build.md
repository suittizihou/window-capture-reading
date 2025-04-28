# 実行ファイル（EXE）ビルド方法

## 概要

このドキュメントでは、Window Capture Readingをスタンドアロンの実行ファイル（EXE）としてビルドする手順を説明します。ビルドされたEXEファイルはTesseract OCRを含むため、ユーザーは追加でOCRエンジンをインストールする必要がありません。

## 前提条件

- Python 3.9以上
- 必要なパッケージ（requirements.txtに記載されているもの）
- PyInstaller 5.1以上

## 手動ビルド手順

### 1. 必要なパッケージのインストール

```powershell
pip install -r requirements.txt
pip install pyinstaller
```

### 2. PyInstallerを使用したビルド

```powershell
pyinstaller --add-data "resources;resources" --add-data "C:\Program Files\Tesseract-OCR;tesseract" --windowed --name window-capture-reading --icon "resources/icon.ico" src/gui_main.py
```

上記コマンドの説明:
- `--add-data "resources;resources"`: リソースディレクトリをバンドル
- `--add-data "C:\Program Files\Tesseract-OCR;tesseract"`: Tesseract OCRをバンドル（インストールパスが異なる場合は調整が必要）
- `--windowed`: コンソールウィンドウを表示しない
- `--name window-capture-reading`: 出力ファイル名
- `--icon "resources/icon.ico"`: アプリケーションアイコン設定

### 3. ビルド結果の確認

ビルドが成功すると、`dist/window-capture-reading`ディレクトリに実行ファイルと必要なリソースが生成されます。

## GitHub Actionsを使用した自動ビルド

このプロジェクトはGitHub Actionsを使用して、バージョンタグ（v*）をプッシュすると自動的にEXEをビルドしてGitHubリリースにアップロードする機能をサポートしています。

自動ビルドを行うには:

1. リポジトリにコードをコミットしてプッシュ
2. 新しいバージョンタグを作成してプッシュ

```powershell
git tag v1.0.3
git push origin v1.0.3
```

これにより、GitHub Actionsワークフローが起動し、以下のステップが実行されます:
1. コードのチェックアウト
2. Pythonと依存関係のセットアップ
3. PyInstallerを使用したEXEのビルド
4. GitHubリリースの作成／更新
5. ビルドされたEXEをリリースアセットとしてアップロード

詳しいワークフロー設定は `.github/workflows/release-exe.yml` を参照してください。

## 注意事項

- ビルドされた実行ファイルは、実行時に `config` ディレクトリを作成して設定を保存します
- アプリケーションを初めて起動する際は、デフォルト設定が適用されます
- ファイアウォールがアラートを表示する場合は、アクセスを許可してください

## 実行ファイルの使用方法

### 初回起動時の注意点

1. 実行ファイルをダウンロードし、任意のフォルダに配置します
2. 初回起動時は、`config` フォルダが自動的に作成されます
3. Windowsのセキュリティ警告が表示される場合がありますが、信頼できる場合は「実行」を選択してください

### 設定の保存場所

実行ファイル版では、設定は以下の場所に保存されます：
- 実行ファイルと同じディレクトリ内の `config` フォルダ
- 具体的には: `[実行ファイルのパス]/config/settings.json`

### 実行ファイル版の特徴

- インストール不要で実行可能
- Python環境が不要
- 設定はEXEファイルと同じディレクトリの `config` フォルダに保存
- Tesseract OCRのパスは設定ダイアログから変更可能

## トラブルシューティング

### 実行ファイルが起動しない場合

1. **アンチウイルスソフトの干渉**: 一部のアンチウイルスソフトウェアが実行ファイルをブロックすることがあります。一時的にウイルス対策ソフトを無効にするか、例外として登録してみてください。

2. **Visual C++ ランタイムの不足**: 実行に必要なVCランタイムがインストールされていない可能性があります。以下からダウンロードしてインストールしてみてください：
   - [Microsoft Visual C++ Redistributable](https://support.microsoft.com/ja-jp/help/2977003/the-latest-supported-visual-c-downloads)

3. **Tesseract OCRの設定**: 実行ファイル版でも、Tesseract OCRは別途インストールが必要です。設定ダイアログからTesseractのパスを正しく設定してください。 