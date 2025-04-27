# GUI（Tkinter版）起動方法

このプロジェクトのGUIはTkinterで実装されています。追加のインストールは不要です。

## 起動手順

1. PowerShellなどでプロジェクトのルートディレクトリに移動します。

2. 次のコマンドを実行してください：

```powershell
python src/gui_main.py
```

- デフォルトで「LDPlayer」というウィンドウタイトルが表示されます。
- 終了ボタンを押すとウィンドウが閉じます。

## 注意事項
- Python標準ライブラリのTkinterを使用しているため、追加のパッケージインストールは不要です。
- ウィンドウタイトルを変更したい場合は、`main()` 関数に引数を渡してください。

例：
```python
from src.gui_main import main
main(window_title="任意のタイトル")
``` 
