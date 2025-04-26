# 棒読みちゃんのセットアップガイド

このドキュメントでは、Window Capture Readingアプリケーションで読み上げ機能を使用するために必要な棒読みちゃんのインストールと設定方法を説明します。

## 棒読みちゃんとは

棒読みちゃんは、テキストを音声で読み上げるためのフリーソフトウェアです。TCP/IP通信を使用して外部アプリケーションから読み上げ指示を送信することができます。

## インストール手順

1. [棒読みちゃん公式サイト](https://chi.usamimi.info/Program/Application/BouyomiChan/)からダウンロード
   - 最新版の「棒読みちゃん」の「インストーラ版」をダウンロードします。

2. インストーラを実行し、指示に従ってインストールします。
   - 標準のインストール先は `C:\Program Files (x86)\BouyomiChan\` です。
   - すべてのコンポーネントをインストールすることをお勧めします。

## TCP/IP設定

Window Capture Readingと連携するためには、棒読みちゃんをTCP/IPサーバーモードで起動する必要があります。

1. 棒読みちゃんを起動します。

2. メニューから「設定」→「システム設定」を選択します。

3. 「Socket通信」タブを選択します。

4. 以下の設定を行います：
   - 「Socket通信機能を使う」にチェックを入れる
   - 「Listen IPアドレス」: `127.0.0.1`（ローカルホスト）
   - 「Listen Port」: `50001`（デフォルト）
   - 「接続待機をする」にチェックを入れる

5. 「OK」をクリックして設定を保存します。

## 音声設定

必要に応じて、以下の音声設定をカスタマイズできます：

1. メニューから「設定」→「音声設定」を選択します。

2. 好みの音声エンジンを選択します。
   - 「AquesTalk（女性１）」がデフォルトです。
   - 他のエンジンを使用する場合は、それぞれの設定を調整できます。

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

## トラブルシューティング

### 棒読みちゃんへの接続エラー

アプリケーションで以下のエラーが表示される場合：
```
棒読みちゃんに接続できませんでした: 127.0.0.1:50001
```

1. 棒読みちゃんが起動しているか確認する
2. Socket通信の設定が正しいか確認する
3. ファイアウォールが通信をブロックしていないか確認する

### 読み上げが機能しない

1. `.env`ファイルで`BOUYOMI_ENABLED=true`になっているか確認する
2. 棒読みちゃんの音声設定で適切な音声エンジンが選択されているか確認する
3. システムの音量設定を確認する
4. 他のアプリが棒読みちゃんのポートを使用していないか確認する

## 参考リンク

- [棒読みちゃん公式サイト](https://chi.usamimi.info/Program/Application/BouyomiChan/)
- [棒読みちゃんTCP/IP連携プロトコル](https://hgotoh.jp/wiki/doku.php/documents/voiceroid/public/bouyomichan_api)
- [AquesTalk公式サイト](https://www.a-quest.com/) 