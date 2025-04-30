#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
パッケージのライセンス情報を収集し、LICENSES.mdファイルに出力するスクリプト。
このスクリプトは、プロジェクトが使用しているすべてのPythonパッケージの
ライセンス情報を収集して整理し、人間が読みやすい形式でドキュメント化します。
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path


def check_pip_licenses_installed():
    """pip-licensesがインストールされているか確認する"""
    try:
        # pip-licensesコマンドが使用可能かチェック
        subprocess.run(["pip-licenses", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("pip-licensesがインストールされていません。以下のコマンドでインストールしてください：")
        print("pip install pip-licenses")
        return False


def get_licenses_data():
    """pip-licensesを使用してライセンス情報を取得する"""
    cmd = ["pip-licenses", "--format=json", "--with-system", "--with-urls"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"エラー: ライセンス情報の取得に失敗しました: {e}")
        print(f"エラー出力: {e.stderr}")
        sys.exit(1)


def group_licenses_by_type(licenses_data):
    """ライセンスの種類ごとにパッケージをグループ化する"""
    license_groups = {}
    for package in licenses_data:
        license_type = package.get("License", "Unknown")
        
        if license_type not in license_groups:
            license_groups[license_type] = []
            
        license_groups[license_type].append(package)
        
    return license_groups


def generate_markdown(license_groups):
    """ライセンス情報をMarkdown形式で出力する"""
    project_root = Path(__file__).parent.parent
    output_path = project_root / "LICENSES.md"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# サードパーティライセンス\n\n")
        f.write(f"*生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        f.write("このプロジェクトは以下のオープンソースソフトウェアを使用しています。\n\n")
        
        f.write("## 目次\n\n")
        for license_type in sorted(license_groups.keys()):
            slug = license_type.lower().replace(" ", "-").replace(".", "")
            f.write(f"- [{license_type}](#{slug})\n")
        
        f.write("\n## ライセンス詳細\n\n")
        
        for license_type in sorted(license_groups.keys()):
            slug = license_type.lower().replace(" ", "-").replace(".", "")
            f.write(f"### {license_type} {{{f'#{slug}'}}} \n\n")
            
            packages = license_groups[license_type]
            f.write("| パッケージ | バージョン | ホームページ |\n")
            f.write("|------------|------------|-------------|\n")
            
            for package in sorted(packages, key=lambda x: x["Name"]):
                name = package.get("Name", "")
                version = package.get("Version", "")
                url = package.get("URL", "")
                
                if url:
                    f.write(f"| {name} | {version} | [{url}]({url}) |\n")
                else:
                    f.write(f"| {name} | {version} | - |\n")
            
            f.write("\n")
    
    print(f"ライセンス情報を {output_path} に出力しました。")
    return output_path


def main():
    """メイン関数"""
    if not check_pip_licenses_installed():
        sys.exit(1)
    
    print("パッケージのライセンス情報を収集しています...")
    licenses_data = get_licenses_data()
    
    print("ライセンス情報を整理しています...")
    license_groups = group_licenses_by_type(licenses_data)
    
    print("Markdownファイルを生成しています...")
    output_path = generate_markdown(license_groups)
    
    print("完了!")
    print(f"合計 {len(licenses_data)} パッケージのライセンス情報を収集しました。")
    print(f"ライセンスタイプ: {', '.join(sorted(license_groups.keys()))}")


if __name__ == "__main__":
    main() 