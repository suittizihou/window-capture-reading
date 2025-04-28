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