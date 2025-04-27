# Window Capture Reading

ウィンドウキャプチャとOCRを用いて、指定ウィンドウのテキストを自動抽出・棒読みちゃんで読み上げるWindows向けツールです。

---

## 特徴
- 任意のウィンドウからリアルタイムでテキストを抽出
- OCR（Tesseract）による高精度な文字認識
- 新規メッセージ検出・重複読み上げ防止
- 棒読みちゃん（TCPサーバーモード）連携による音声出力
- 柔軟な設定（.envファイル）
- ログ出力・メモリ監視機能

---

## 推奨環境
- Windows 10/11
- Python 3.11以上
- 棒読みちゃん（TCPサーバーモード有効）
- Tesseract OCR（日本語対応）

---

## インストール手順

```powershell
# 仮想環境の作成と有効化
python -m venv venv
.\venv\Scripts\Activate

# 依存関係のインストール
pip install -r requirements.txt
```

Tesseract・棒読みちゃんのセットアップは [docs/tesseract_setup.md](docs/tesseract_setup.md)・[docs/bouyomi_setup.md](docs/bouyomi_setup.md) を参照してください。

---

## 初期設定
1. `.env.example` を `.env` にコピーし、必要なパラメータ（ウィンドウタイトル、Tesseractパス、棒読みちゃんホスト/ポート等）を編集
2. 棒読みちゃんをTCPサーバーモードで起動
3. Tesseractのパス・言語設定を確認

詳細は [docs/environment_setup.md](docs/environment_setup.md) を参照

---

## 起動方法

```powershell
python -m src.main
```

- ウィンドウタイトルは`.env`で指定（例：LDPlayer, Chrome など）
- 起動後、指定ウィンドウのテキストが自動で抽出・音声出力されます

---

## 主な使い方
- OCR対象ウィンドウをアクティブにしておく
- 新しいテキストが検出されると自動で読み上げ
- ログは`app.log`に出力
- メモリ監視や詳細設定は`.env`で制御

---

## トラブルシューティング
- 棒読みちゃんが反応しない：TCPサーバーモード・ポート設定・ファイアウォールを確認
- 文字化け：Tesseractの言語設定・エンコーディングを確認
- OCR精度が低い：ウィンドウの解像度や前処理設定を調整
- その他詳細は [docs/setup_guide.md](docs/setup_guide.md) を参照

---

## 詳細ガイド
- [docs/setup_guide.md](docs/setup_guide.md) ... 棒読みちゃんセットアップ・連携
- [docs/tesseract_setup.md](docs/tesseract_setup.md) ... Tesseract OCRセットアップ
- [docs/bouyomi_setup.md](docs/bouyomi_setup.md) ... 棒読みちゃん詳細設定
- [docs/environment_setup.md](docs/environment_setup.md) ... .env/環境設定例

---

## プロジェクト構成
```
src/        ... アプリ本体
  services/ ... 各種サービス（OCR, TTS, キャプチャ等）
  utils/    ... ユーティリティ
config/     ... 設定ファイル
resources/  ... 静的リソース
tests/      ... ユニットテスト
```

---

## ライセンス
MIT

---

## 貢献
バグ報告・機能要望・PR歓迎です。詳細はCONTRIBUTING.md（今後追加予定）をご参照ください。
