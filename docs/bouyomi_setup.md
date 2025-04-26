# 棒読みちゃんセットアップガイド

このガイドでは、Window Capture Readingアプリケーションで読み上げ機能を使用するために必要な棒読みちゃんのインストールと設定方法を説明します。

## 棒読みちゃんとは

棒読みちゃんは、テキストを音声で読み上げるためのフリーソフトウェアです。TCP/IP通信を使用して外部アプリケーションから読み上げ指示を送信することができます。

## インストール手順

### 1. 棒読みちゃんのダウンロード

1. [棒読みちゃん公式サイト](https://chi.usamimi.info/Program/Application/BouyomiChan/)から最新版をダウンロードします。
   - 「インストーラ版」をダウンロードすることをお勧めします。

2. インストーラを実行し、指示に従ってインストールします。
   - 標準のインストール先は `C:\Program Files (x86)\BouyomiChan\` です。
   - すべてのコンポーネントをインストールすることをお勧めします。

### 2. 初期設定

1. インストールした `BouyomiChan.exe` を実行します。

2. 初回起動時に以下の設定を確認してください：
   - 基本設定
     - 「起動時に読み上げ開始」にチェック
     - 「最小化して起動」にチェック（任意）
   - 音声設定
     - お好みの音声エンジンを選択
     - 声質、速度、音程、音量を調整

### 3. TCP/IP設定

1. メニューから「設定」→「システム設定」を選択します。

2. 「Socket通信」タブで以下の設定を行います：
   - 「Socket通信機能を使う」にチェックを入れる
   - 「Listen IPアドレス」: `127.0.0.1`（ローカルホスト）
   - 「Listen Port」: `50001`（デフォルト）
   - 「接続待機をする」にチェックを入れる

3. 「OK」をクリックして設定を保存します。

## アプリケーションとの連携

Window Capture Readingで棒読みちゃんと連携するには、`.env`ファイルで以下の設定を確認/更新します：

```
# 棒読みちゃん設定
BOUYOMI_ENABLED=true
BOUYOMI_HOST=127.0.0.1
BOUYOMI_PORT=50001

# 棒読みちゃん拡張設定
BOUYOMI_RETRY_INTERVAL=5
BOUYOMI_VOICE_TYPE=0
BOUYOMI_VOICE_SPEED=-1
BOUYOMI_VOICE_TONE=-1
BOUYOMI_VOICE_VOLUME=-1
```

- `BOUYOMI_ENABLED`: 読み上げ機能の有効/無効を切り替えます（`true`または`false`）
- `BOUYOMI_HOST`: 棒読みちゃんのIPアドレス
- `BOUYOMI_PORT`: 棒読みちゃんのポート番号
- `BOUYOMI_RETRY_INTERVAL`: 接続失敗時の再試行間隔（秒）
- `BOUYOMI_VOICE_TYPE`: 音声の種類（0: 標準）
- `BOUYOMI_VOICE_SPEED`: 読み上げ速度（-1: デフォルト）
- `BOUYOMI_VOICE_TONE`: 音程（-1: デフォルト）
- `BOUYOMI_VOICE_VOLUME`: 音量（-1: デフォルト）

## 動作確認

1. 棒読みちゃんが起動していることを確認します。

2. 以下のPythonスクリプトで動作確認ができます：

```python
from src.services.bouyomi_client import BouyomiClient

client = BouyomiClient()
client.speak("テスト")  # このテキストが読み上げられるはずです
```

## トラブルシューティング

### 接続エラーが発生する場合

アプリケーションで以下のエラーが表示される場合：
```
棒読みちゃんに接続できませんでした: 127.0.0.1:50001
```

1. 棒読みちゃんが起動しているか確認する
2. Socket通信の設定が正しいか確認する
3. ファイアウォールが通信をブロックしていないか確認する
4. ポート番号が正しく設定されているか確認する

### 読み上げが機能しない場合

1. `.env`ファイルで`BOUYOMI_ENABLED=true`になっているか確認する
2. 音声エンジンが正しくインストールされているか確認する
3. 音声の設定（音量など）を確認する
4. 他のアプリケーションが音声出力を占有していないか確認する
5. システムの音量設定を確認する

### 文字化けが発生する場合

1. 文字コードがUTF-8に設定されているか確認する
2. テキストエンコーディングが正しく処理されているか確認する

## 参考リンク

- [棒読みちゃん公式サイト](https://chi.usamimi.info/Program/Application/BouyomiChan/)
- [棒読みちゃんTCP/IP連携プロトコル](https://hgotoh.jp/wiki/doku.php/documents/voiceroid/public/bouyomichan_api)
- [AquesTalk公式サイト](https://www.a-quest.com/)
