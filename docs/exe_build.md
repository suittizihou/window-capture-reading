# WindowCaptureReading.exe ビルド手順（Windows向け）

このドキュメントでは、PythonアプリケーションをWindows用の単一実行ファイル（exe）に変換する手順を説明します。

---

## 必要なもの
- Python 3.11（推奨）
- pip
- 仮想環境（venv など）
- 必要な依存パッケージ（requirements.txt）
- PyInstaller

---

## 1. 依存パッケージのインストール

PowerShellでプロジェクトルートに移動し、以下を実行してください。

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

---

## 2. exeファイルのビルド

以下のコマンドでビルドします。

```powershell
pyinstaller --noconfirm --onefile --windowed --name WindowCaptureReading --add-data "src;src" src/gui_main.py --distpath dist
```

- `--name WindowCaptureReading` でexe名を指定
- `--add-data "src;src"` でリソースをバンドル
- 出力先は `dist/WindowCaptureReading.exe`

---

## 3. 実行・配布

- `dist/WindowCaptureReading.exe` を実行してください。
- 設定ファイルはexeと同じ階層の `config` フォルダに自動保存されます。
- 配布時は `config` フォルダも同梱してください。

---

## 4. PowerShell用ビルドスクリプト例

`build_exe.ps1` という名前で以下の内容を保存し、PowerShellで実行できます。

```powershell
# venv有効化
if (!(Test-Path ".\venv")) {
    python -m venv venv
}
.\venv\Scripts\Activate.ps1

# 依存パッケージインストール
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# exeビルド
pyinstaller --noconfirm --onefile --windowed --name WindowCaptureReading --add-data "src;src" src/gui_main.py --distpath dist

Write-Host "ビルド完了: dist/WindowCaptureReading.exe"
```

---

## 5. 注意事項
- exe実行時に `config` フォルダが自動生成されます。
- 追加DLLやリソースが必要な場合は `--add-data` オプションを調整してください。
- GitHub Actionsによる自動ビルド・リリースも利用可能です（タグpush時）。 