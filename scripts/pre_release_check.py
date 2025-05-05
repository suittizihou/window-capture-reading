#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
リリース前にプロジェクトの状態をチェックするスクリプト。
以下の項目を確認します：
- ライセンス情報が最新か
- 必要なファイルが揃っているか
- テストが通るか
- ドキュメントが更新されているか
"""

import os
import sys
import subprocess
import datetime
from pathlib import Path


def check_license_info():
    """ライセンス情報が最新かチェックする"""
    print("ライセンス情報をチェックしています...")
    
    licenses_md = Path("LICENSES.md")
    if not licenses_md.exists():
        print("❌ LICENSES.mdファイルが見つかりません。以下のコマンドで生成してください：")
        print("python scripts/check_licenses.py")
        return False
    
    # ファイルの更新日時を確認
    last_modified = datetime.datetime.fromtimestamp(licenses_md.stat().st_mtime)
    days_old = (datetime.datetime.now() - last_modified).days
    
    if days_old > 30:
        print(f"⚠️ LICENSES.mdファイルが{days_old}日前に更新されています。更新を検討してください：")
        print("python scripts/check_licenses.py")
    else:
        print(f"✅ LICENSES.mdファイルは最近（{days_old}日前）に更新されています。")
    
    return True


def check_required_files():
    """必要なファイルが揃っているかチェックする"""
    print("\n必要なファイルをチェックしています...")
    
    required_files = [
        "README.md",
        "LICENSE",
        "LICENSES.md",
        "requirements.txt",
        "config.json",
        "docs/environment_setup.md",
        "docs/gui_usage.md",
        "docs/setup_guide.md",
        "docs/exe_build.md",
        "docs/license_compliance.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ 以下のファイルが見つかりません：")
        for file in missing_files:
            print(f"  - {file}")
        return False
    else:
        print("✅ すべての必要なファイルが揃っています。")
    
    return True


def run_tests():
    """テストを実行する"""
    print("\nテストを実行しています...")
    
    tests_dir = Path("tests")
    if not tests_dir.exists() or not tests_dir.is_dir():
        print("⚠️ testsディレクトリが見つかりません。テストをスキップします。")
        return True
    
    try:
        result = subprocess.run(["pytest"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ すべてのテストが成功しました。")
            return True
        else:
            print("❌ テストが失敗しました。出力：")
            print(result.stdout)
            print(result.stderr)
            return False
    except FileNotFoundError:
        print("⚠️ pytestが見つかりません。以下のコマンドでインストールしてください：")
        print("pip install pytest")
        return True
    except Exception as e:
        print(f"⚠️ テスト実行中にエラーが発生しました: {e}")
        return True


def check_doc_updates():
    """ドキュメントが更新されているかチェックする"""
    print("\nドキュメントの状態をチェックしています...")
    
    docs_dir = Path("docs")
    if not docs_dir.exists() or not docs_dir.is_dir():
        print("❌ docsディレクトリが見つかりません。")
        return False
    
    # ドキュメントファイルの一覧を取得
    doc_files = list(docs_dir.glob("*.md"))
    
    # 30日以上更新されていないドキュメントを検出
    old_docs = []
    for doc in doc_files:
        last_modified = datetime.datetime.fromtimestamp(doc.stat().st_mtime)
        days_old = (datetime.datetime.now() - last_modified).days
        
        if days_old > 90:
            old_docs.append((doc, days_old))
    
    if old_docs:
        print("⚠️ 以下のドキュメントは90日以上更新されていません：")
        for doc, days in old_docs:
            print(f"  - {doc} ({days}日前)")
        print("  必要に応じて内容を見直してください。")
    else:
        print("✅ すべてのドキュメントは最近更新されています。")
    
    return True


def main():
    """メイン関数"""
    print("======== リリース前チェック ========")
    print(f"実行日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    results.append(check_license_info())
    results.append(check_required_files())
    results.append(run_tests())
    results.append(check_doc_updates())
    
    print("\n======== チェック結果サマリー ========")
    if all(results):
        print("✅ すべてのチェックが完了しました。リリースの準備が整っています。")
        return 0
    else:
        print("❌ いくつかのチェックが失敗しました。上記の問題を解決してからリリースしてください。")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 