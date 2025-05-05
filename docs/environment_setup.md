# 設定ファイル（config.json）の使用方法

本プロジェクトでは、`config.json`ファイルを使用して各種設定を管理します。

## 設定ファイルの場所

設定ファイル（config.json）はプロジェクトのルートディレクトリに配置されています。
実行ファイル（EXE）版では、実行ファイルと同じディレクトリの`config`フォルダ内に保存されます。

## 設定オプション

### キャプチャ関連設定

#### window_title
- 説明: キャプチャするウィンドウのタイトル
- デフォルト値: `"Chrome"`
- 設定例:
  ```json
  {
    "window_title": "Chrome"
  }
  ```

#### diff_threshold
- 説明: 通知音を鳴らす変化率の閾値（0.0～1.0）
- デフォルト値: `0.05`
- 設定例:
  ```json
  {
    "diff_threshold": 0.05
  }
  ```

#### capture_interval
- 説明: キャプチャ間隔（秒）
- デフォルト値: `1.0`
- 設定例:
  ```json
  {
    "capture_interval": 1.0
  }
  ```

### 通知関連設定

#### notification_sound
- 説明: 通知音を有効にするかどうか
- デフォルト値: `true`
- 設定例:
  ```json
  {
    "notification_sound": true
  }
  ```

### 差分検出関連設定

#### diff_method
- 説明: 差分検出に使用するアルゴリズム（"ssim"または"absdiff"）
- デフォルト値: `"ssim"`
- 設定例:
  ```json
  {
    "diff_method": "ssim"
  }
  ```

## config.jsonの例

完全な設定ファイルの例:

```json
{
  "window_title": "LDPlayer",
  "capture_interval": 1.0,
  "diff_threshold": 0.09,
  "diff_method": "ssim",
  "notification_sound": true
}
```

## 設定ファイルの編集方法

1. テキストエディタで`config.json`ファイルを開く
2. 必要な設定値を編集
3. 保存して、アプリケーションを再起動

## 注意事項

- 設定変更後はアプリケーションの再起動が必要です
- 設定ファイルが存在しない場合は、アプリケーション起動時にデフォルト設定で自動的に作成されます
- 無効な設定値の場合は、該当する設定のみデフォルト値に戻されます
- JSONファイルの形式に従って編集してください。カンマやブラケットの漏れがあると読み込みエラーになります