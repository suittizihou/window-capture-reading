# Window Capture Reading

ウィンドウキャプチャを用いて、指定ウィンドウの画面変化を検出し、通知音を出力するWindows向けツールです。

---

## 特徴
- 任意のウィンドウからリアルタイムで画面変化を検出
- 変化率に基づいた通知機能
- 柔軟な設定（config.jsonファイル）
- ログ出力・メモリ監視機能

---

## 推奨環境
- Windows 10/11
- Python 3.11以上

---

## インストール手順

```powershell
# 仮想環境の作成と有効化
python -m venv venv
.\venv\Scripts\Activate

# 依存関係のインストール
pip install -r requirements.txt
```

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
src/        ... アプリ本体
  services/ ... 各種サービス（画面変化検出、通知音等）
  utils/    ... ユーティリティ
config/     ... 設定ファイル
resources/  ... 静的リソース
tests/      ... ユニットテスト
scripts/    ... ユーティリティスクリプト
```

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
