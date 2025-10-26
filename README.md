# Window Capture Reading

ウィンドウキャプチャを用いて、指定ウィンドウの画面変化を検出し、通知音を出力するWindows向けツールです。

---

## 特徴
- **高性能なウィンドウキャプチャ**: Windows.Graphics.Capture API（windows-capture ライブラリ）を使用
  - DirectXアプリケーションやゲームウィンドウもキャプチャ可能
  - イベント駆動型のバックグラウンド処理で高効率
- **リアルタイム画面変化検出**: 任意のウィンドウから画面変化を検出
- **充実したGUI機能**:
  - リアルタイムプレビュー表示
  - ROI（関心領域）選択機能
  - 差分可視化キャンバス
  - 設定ダイアログ（閾値調整等）
- **柔軟な設定**: config.jsonファイルによる詳細設定
- **変化率に基づいた通知機能**: SSIM（構造類似性）または絶対差分による検出
- **ログ出力・メモリ監視機能**

---

## 推奨環境
- Windows 10/11
- Python 3.11以上

---

## インストール手順

### ユーザー向け（アプリケーション実行のみ）

```powershell
# 仮想環境の作成と有効化
python -m venv venv
.\venv\Scripts\Activate

# 実行時依存関係のインストール
pip install -r requirements.txt
```

### 開発者向け（テスト・コード品質管理含む）

```powershell
# 仮想環境の作成と有効化
python -m venv venv
.\venv\Scripts\Activate

# 開発依存関係のインストール（実行時依存関係も含む）
pip install -r requirements-dev.txt
```

開発依存関係には以下が含まれます：
- テストフレームワーク（pytest, pytest-cov）
- コードフォーマッター（black, isort）
- リンター（flake8）
- 型チェッカー（mypy）
- ライセンス管理ツール（pip-licenses）

---

## 初期設定
1. プロジェクトルートディレクトリに`config.json`ファイルを作成または編集
   （ファイルが存在しない場合、アプリケーション実行時に自動生成されます）

詳細は [docs/environment_setup.md](docs/environment_setup.md) を参照

---

## 起動方法

### 開発時（Pythonから起動）

```powershell
python -m src.main
```

### EXE版を使用する場合

```powershell
# EXEを起動
.\dist\WindowCaptureReading.exe

# EXEを再ビルド
pyinstaller WindowCaptureReading.spec
```

- ウィンドウタイトルは`config.json`で指定（例：LDPlayer, Chrome など）
- 起動後、指定ウィンドウの画面変化が検出されると通知音が出力されます

---

## 主な使い方

### GUI操作
1. **アプリケーション起動**
   - `python -m src.main`でGUIが起動します
   - 指定したウィンドウのリアルタイムプレビューが表示されます

2. **ROI（関心領域）選択**
   - プレビューキャンバス上でドラッグして検出範囲を指定できます
   - 選択した領域のみが変化検出の対象になります

3. **差分可視化**
   - 画面変化が検出されると、差分キャンバスに変化箇所が表示されます
   - 赤色で変化箇所がハイライトされます

4. **設定調整**
   - 設定ダイアログから検出閾値を調整できます
   - 検出方法（SSIM/絶対差分）の切り替えも可能

### 自動検出
- 検出対象ウィンドウをアクティブにしておく
- 画面の変化率が設定した閾値を超えると通知音が鳴る
- ログは`app.log`に出力
- メモリ監視や詳細設定は`config.json`で制御

---

## トラブルシューティング
- 通知音が鳴らない：音量設定やウィンドウ指定を確認
- 検出がうまくいかない：変化率閾値の調整
- その他詳細は [docs/setup_guide.md](docs/setup_guide.md) を参照

---

## 詳細ガイド
- [docs/setup_guide.md](docs/setup_guide.md) ... セットアップガイド
- [docs/environment_setup.md](docs/environment_setup.md) ... config.json設定例
- [docs/gui_usage.md](docs/gui_usage.md) ... GUI使用方法
- [docs/exe_build.md](docs/exe_build.md) ... 実行ファイル（EXE）ビルド方法
- [docs/license_compliance.md](docs/license_compliance.md) ... ライセンスコンプライアンスガイド

---

## プロジェクト構成
```
src/                      ... アプリ本体
  gui/                    ... GUI関連
    main_window.py        ... メインウィンドウ
    settings_dialog.py    ... 設定ダイアログ
    preview_canvas.py     ... プレビューキャンバス
    diff_canvas.py        ... 差分可視化キャンバス
  services/               ... コアロジック
    window_capture.py     ... ウィンドウキャプチャ（Windows.Graphics.Capture API）
    difference_detector.py ... 画面差分検出（SSIM/絶対差分）
    memory_watcher.py     ... メモリ監視
  utils/                  ... ユーティリティ
    config.py             ... 設定管理
    logging_config.py     ... ログ設定
    resource_path.py      ... リソースパス解決（PyInstaller対応）
  main.py                 ... エントリーポイント
  version.py              ... バージョン情報
resources/                ... 静的リソース（音声、アイコン）
tests/                    ... ユニットテスト
scripts/                  ... ユーティリティスクリプト（ライセンスチェック等）
docs/                     ... ドキュメント
```

---

## 開発者向け情報

### テスト

```powershell
# すべてのテストを実行
pytest

# カバレッジ付きで実行
pytest --cov=src tests/

# 特定のテストファイルを実行
pytest tests/services/test_window_capture.py
```

### コード品質管理

```powershell
# コードフォーマット（Black: 88文字行長）
black src/ tests/

# インポート文の整理
isort src/ tests/

# リンティング
flake8 src/ tests/

# 型チェック
mypy src/
```

### ビルド

```powershell
# PyInstallerをインストール
pip install pyinstaller

# specファイルを使用してビルド（推奨）
pyinstaller WindowCaptureReading.spec

# ビルドされたEXEの場所
.\dist\WindowCaptureReading.exe
```

詳細なビルド手順は [docs/exe_build.md](docs/exe_build.md) を参照してください。

---

## ライセンス
本プロジェクトはMITライセンスで提供されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

### サードパーティライセンス
このプロジェクトは多数のオープンソースライブラリを使用しています。
使用しているライブラリのライセンス情報は[LICENSES.md](LICENSES.md)ファイルにまとめられています。

ライセンス情報の管理：
```powershell
# ライセンス情報を更新
pip install pip-licenses
python scripts/check_licenses.py

# リリース前のライセンスチェック
python scripts/pre_release_check.py
```

GitHub Actionsによる自動チェック：
- `requirements.txt`や`pyproject.toml`が更新されると自動的にライセンス情報がチェックされます
- 変更があった場合は、ワークフロー実行結果からartifactとして最新のLICENSES.mdをダウンロードできます

---

## 貢献
バグ報告・機能要望・PR歓迎です。詳細はCONTRIBUTING.md（今後追加予定）をご参照ください。
