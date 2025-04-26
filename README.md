# Window Capture Reading

ウィンドウキャプチャとOCRを使用して、指定されたウィンドウのテキストを読み上げるツール。

## 概要

このツールは以下の機能を提供します：

- 指定されたウィンドウのキャプチャ
- OCRによるテキスト認識
- 新規メッセージの検出
- 棒読みちゃんを使用したテキスト読み上げ

## 必要条件

- Windows 10/11
- Python 3.11以上
- 棒読みちゃん（TCP サーバーモード有効）

## インストール

```powershell
# 仮想環境の作成と有効化
python -m venv venv
.\venv\Scripts\Activate

# 依存関係のインストール
pip install -r requirements.txt
```

## 設定

1. `.env.example` を `.env` にコピーして必要な設定を行います
2. 棒読みちゃんをTCPサーバーモードで起動します

## 使用方法

```powershell
python src/main.py
```

## ライセンス

MIT
