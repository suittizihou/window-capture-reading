"""
設定を管理するモジュール。

.iniファイル形式で設定を管理し、ユーザーが容易に設定を変更できるようにします。
"""

import os
import sys
import logging
import configparser
from pathlib import Path
from typing import Dict, Any, Optional

class Config:
    """
    設定を.iniファイル形式で管理するクラス。
    
    設定はセクションごとに整理され、ユーザーが容易に編集できます。
    """
    
    def __init__(self) -> None:
        """Configクラスを初期化し、設定ファイルを読み込みます。"""
        self.logger = logging.getLogger(__name__)
        self.config_parser = configparser.ConfigParser()
        
        # 設定ファイルのパスを取得
        self.config_path = self._get_config_path()
        
        # デフォルト設定を読み込む
        self._set_default_config()
        
        # 設定ファイルが存在する場合は読み込む
        if self.config_path.exists():
            try:
                self.config_parser.read(self.config_path, encoding='utf-8')
                self.logger.info(f"設定ファイルを読み込みました: {self.config_path}")
            except Exception as e:
                self.logger.error(f"設定ファイルの読み込みに失敗しました: {e}")
        else:
            # 設定ファイルが存在しない場合は作成する
            self._create_default_config()
            self.logger.info(f"デフォルト設定ファイルを作成しました: {self.config_path}")
    
    def _get_config_path(self) -> Path:
        """
        実行環境に応じて設定ファイルのパスを返します。
        
        Returns:
            Path: 設定ファイルのパス
        """
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # PyInstallerでexe化されている場合
            exe_dir = Path(sys.executable).parent
            return exe_dir / "config.ini"
        else:
            # 通常のスクリプト実行
            return Path(__file__).parent.parent.parent / "config.ini"
    
    def _set_default_config(self) -> None:
        """デフォルト設定を設定します。"""
        # Windowセクション
        self.config_parser.add_section('Window')
        self.config_parser.set('Window', 'TARGET_WINDOW_TITLE', 'LDPlayer')
        self.config_parser.set('Window', 'CAPTURE_INTERVAL', '1.0')
        
        # OCRセクション
        self.config_parser.add_section('OCR')
        self.config_parser.set('OCR', 'TESSERACT_PATH', r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe')
        self.config_parser.set('OCR', 'TESSERACT_LANG', 'jpn')
        self.config_parser.set('OCR', 'TESSERACT_CONFIG', '--psm 6')
        self.config_parser.set('OCR', 'OCR_USE_GRAYSCALE', 'true')
        self.config_parser.set('OCR', 'OCR_USE_BLUR', 'true')
        self.config_parser.set('OCR', 'OCR_USE_THRESHOLD', 'true')
        self.config_parser.set('OCR', 'OCR_BLUR_KERNEL', '5')
        self.config_parser.set('OCR', 'OCR_THRESHOLD_METHOD', 'adaptive')
        self.config_parser.set('OCR', 'OCR_CONTRAST_ALPHA', '1.0')
        self.config_parser.set('OCR', 'OCR_CONTRAST_BETA', '0')
        self.config_parser.set('OCR', 'OCR_USE_CACHE', 'true')
        self.config_parser.set('OCR', 'OCR_CACHE_TTL', '5.0')
        
        # Differenceセクション
        self.config_parser.add_section('Difference')
        self.config_parser.set('Difference', 'DIFF_THRESHOLD', '0.05')
        self.config_parser.set('Difference', 'DIFF_BLUR_SIZE', '5')
        self.config_parser.set('Difference', 'DIFF_COOLDOWN', '1.0')
        self.config_parser.set('Difference', 'DIFF_MIN_AREA', '100')
        self.config_parser.set('Difference', 'DIFF_METHOD', 'ssim')
        self.config_parser.set('Difference', 'DIFF_MAX_HISTORY', '10')
        self.config_parser.set('Difference', 'DIFF_DEBUG_MODE', 'false')
        
        # Notificationセクション
        self.config_parser.add_section('Notification')
        self.config_parser.set('Notification', 'NOTIFICATION_TITLE', '画面の変化を検知しました')
        self.config_parser.set('Notification', 'NOTIFICATION_SOUND', 'true')
        self.config_parser.set('Notification', 'NOTIFICATION_BEEP_FREQUENCY', '1000')
        self.config_parser.set('Notification', 'NOTIFICATION_BEEP_DURATION', '200')
        
        # 後方互換性のために追加
        self.config_parser.add_section('Compatibility')
        self.config_parser.set('Compatibility', 'BOUYOMI_PORT', '50001')
        self.config_parser.set('Compatibility', 'BOUYOMI_VOICE_TYPE', '0')
    
    def _create_default_config(self) -> None:
        """デフォルト設定ファイルを作成します。"""
        try:
            # 必要なディレクトリを作成
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 設定ファイルを書き込む
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config_parser.write(f)
        except Exception as e:
            self.logger.error(f"デフォルト設定ファイルの作成に失敗しました: {e}")
    
    def get(self, key: str, default: Optional[str] = None) -> str:
        """
        指定されたキーの設定値を取得します。
        
        Args:
            key: 設定キー（例: "TESSERACT_PATH"）
            default: キーが存在しない場合のデフォルト値
            
        Returns:
            設定値
        """
        # セクション名を特定
        section = self._get_section_for_key(key)
        
        if section and key in self.config_parser[section]:
            return self.config_parser[section][key]
        return default
    
    def set(self, key: str, value: str) -> None:
        """
        指定されたキーに設定値を設定します。
        
        Args:
            key: 設定キー（例: "TESSERACT_PATH"）
            value: 設定値
        """
        # セクション名を特定
        section = self._get_section_for_key(key)
        
        if section:
            self.config_parser[section][key] = value
        else:
            # セクションが特定できない場合はCompatibilityセクションに保存
            self.config_parser['Compatibility'][key] = value
    
    def _get_section_for_key(self, key: str) -> Optional[str]:
        """
        指定されたキーが属するセクション名を取得します。
        
        Args:
            key: 設定キー
            
        Returns:
            セクション名、または特定できない場合はNone
        """
        for section in self.config_parser.sections():
            if key in self.config_parser[section]:
                return section
        
        # キーの接頭辞からセクションを推測
        key_prefixes = {
            'TARGET_WINDOW': 'Window',
            'CAPTURE_': 'Window',
            'TESSERACT_': 'OCR',
            'OCR_': 'OCR',
            'DIFF_': 'Difference',
            'NOTIFICATION_': 'Notification',
            'BOUYOMI_': 'Compatibility'
        }
        
        for prefix, section in key_prefixes.items():
            if key.startswith(prefix):
                return section
        
        return None
    
    def save(self) -> None:
        """現在の設定を設定ファイルに保存します。"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config_parser.write(f)
            self.logger.info(f"設定を保存しました: {self.config_path}")
        except Exception as e:
            self.logger.error(f"設定の保存に失敗しました: {e}")
    
    def get_all(self) -> Dict[str, Dict[str, str]]:
        """
        すべての設定をセクションごとに辞書として取得します。
        
        Returns:
            すべての設定
        """
        result = {}
        for section in self.config_parser.sections():
            result[section] = dict(self.config_parser[section])
        return result