# Window Capture Reading セットアップガイド

## 1. 基本インストール

### 環境準備
1. Python 3.11以上をインストール
   - [Python公式サイト](https://www.python.org/downloads/)からダウンロード
   - インストール時に「Add Python to PATH」にチェックを入れる

### リポジトリのクローン
```powershell
git clone https://github.com/suittizihou/window-capture-reading.git
cd window-capture-reading
```

### 仮想環境のセットアップ
```powershell
python -m venv venv
.\venv\Scripts\Activate
```

### 依存関係のインストール
```powershell
pip install -r requirements.txt
```

## 2. アプリケーション設定

### 設定ファイルの準備
1. プロジェクトルートに`config.json`ファイルを作成（ない場合は自動生成されます）
2. `config.json`ファイルを編集して必要な設定を行う：

```json
{
  "window_title": "Chrome",
  "capture_interval": 1.0,
  "diff_threshold": 0.05,
  "diff_method": "ssim",
  "notification_sound": true
}
```

### 通知設定
1. `config.json`ファイルの通知関連設定を必要に応じて変更
   - `notification_sound`: 通知音の有効/無効

## 3. アプリケーションの実行

### GUI起動
```powershell
python -m src.gui_main
```

## 4. トラブルシューティング

### 変化検出の問題
1. 変化率閾値（`diff_threshold`）を調整
   - 閾値を下げると検出感度が上がる（0.01-0.1の範囲で調整推奨）
   - 閾値を上げると誤検出が減少

### キャプチャの問題
1. ウィンドウタイトルが正確に設定されているか確認
2. ウィンドウが最小化されていないことを確認
3. 前景ウィンドウとして表示されていることを確認

### 通知音の問題
1. `notification_sound`設定が`true`になっているか確認
2. システムの音量設定を確認

## 5. 補足情報

### 推奨設定
- 変化率閾値：0.05（標準的な変化検出）
- キャプチャ間隔：1.0秒（パフォーマンスと検出精度のバランス）
- 差分検出方式：ssim（構造的類似性による高精度な差分検出）

### 注意事項
- ウィンドウのタイトルは部分一致で検索されます
- キャプチャ間隔を短くするとCPU使用率が上昇します
- 画面のチラつきが多い場合は閾値を上げてください