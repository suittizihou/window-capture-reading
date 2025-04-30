# 設定ファイル（config.ini）の使用方法

本プロジェクトでは、`config.ini`ファイルを使用して各種設定を管理します。

## 設定ファイルの場所

設定ファイル（config.ini）はプロジェクトのルートディレクトリに配置されています。
実行ファイル（EXE）版では、実行ファイルと同じディレクトリの`config`フォルダ内に保存されます。

## 設定オプション

### [Capture]セクション

#### window_title
- 説明: キャプチャするウィンドウのタイトル
- デフォルト値: `Chrome`
- 設定例:
  ```ini
  [Capture]
  window_title = Chrome
  ```

#### change_threshold
- 説明: 通知音を鳴らす変化率の閾値（0.0～1.0）
- デフォルト値: `0.05`
- 設定例:
  ```ini
  [Capture]
  change_threshold = 0.05
  ```

#### capture_interval
- 説明: キャプチャ間隔（秒）
- デフォルト値: `1.0`
- 設定例:
  ```ini
  [Capture]
  capture_interval = 1.0
  ```

### [Notification]セクション

#### sound_file
- 説明: 通知音ファイルのパス
- デフォルト値: `resources/sounds/notification.wav`
- 設定例:
  ```ini
  [Notification]
  sound_file = resources/sounds/notification.wav
  ```

### [Processing]セクション

#### preprocessing_enabled
- 説明: 画像の前処理を有効にするかどうか
- デフォルト値: `True`
- 設定例:
  ```ini
  [Processing]
  preprocessing_enabled = True
  ```

## config.iniの例

完全な設定ファイルの例:

```ini
[Capture]
window_title = Chrome
change_threshold = 0.05
capture_interval = 1.0

[Notification]
sound_file = resources/sounds/notification.wav

[Processing]
preprocessing_enabled = True
```

## 設定ファイルの編集方法

1. テキストエディタで`config.ini`ファイルを開く
2. 必要な設定値を編集
3. 保存して、アプリケーションを再起動

## 注意事項

- 設定変更後はアプリケーションの再起動が必要です
- 設定ファイルが存在しない場合は、アプリケーション起動時にデフォルト設定で自動的に作成されます
- 無効な設定値の場合は、該当する設定のみデフォルト値に戻されます