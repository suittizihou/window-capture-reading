"""棒読みちゃんと通信するモジュール。

TCP通信で棒読みちゃんにテキストを送信します。
"""

import logging
import socket
import struct
import time
from typing import Dict, Optional, Tuple

class BouyomiClient:
    """棒読みちゃんクライアントクラス。
    
    TCP通信で棒読みちゃんにテキストを送信する機能を提供します。
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """棒読みちゃんクライアントクラスを初期化します。
        
        Args:
            config: 環境設定の辞書
        """
        self.logger = logging.getLogger(__name__)
        
        # 棒読みちゃんの接続設定
        self.host = config.get("BOUYOMI_HOST", "127.0.0.1")
        self.port = int(config.get("BOUYOMI_PORT", "50001"))
        
        # 音声設定
        self.voice_type = int(config.get("BOUYOMI_VOICE_TYPE", "0"))  # 0: 通常
        self.voice_speed = int(config.get("BOUYOMI_VOICE_SPEED", "-1"))  # -1: 標準
        self.voice_tone = int(config.get("BOUYOMI_VOICE_TONE", "-1"))  # -1: 標準
        self.voice_volume = int(config.get("BOUYOMI_VOICE_VOLUME", "-1"))  # -1: 標準
        self.voice_type_specific = int(config.get("BOUYOMI_VOICE_TYPE_SPECIFIC", "0"))  # 0: 標準
        
        # 接続状態
        self._connected = False
        self._last_connect_attempt = 0
        self._connect_retry_interval = int(config.get("BOUYOMI_RETRY_INTERVAL", "5"))  # 秒
        
        # 接続タイムアウト設定
        self._timeout = float(config.get("BOUYOMI_COMMAND_TIMEOUT", "3.0"))  # 秒
        
        # 永続的なソケット接続（常にNoneから開始）
        self._socket = None
    
    def __del__(self) -> None:
        """デストラクタ - オブジェクトが破棄される際にリソースを解放します。"""
        self.close()
    
    def close(self) -> None:
        """接続をクローズし、リソースを解放します。"""
        try:
            if self._socket:
                self._socket.close()
                self._socket = None
            self._connected = False
            self.logger.debug("棒読みちゃんとの接続を閉じました")
        except Exception as e:
            self.logger.error(f"棒読みちゃんとの接続クローズ中にエラーが発生しました: {e}", exc_info=True)
    
    def speak(self, text: str) -> bool:
        """テキストを棒読みちゃんに送信して読み上げさせます。
        
        Args:
            text: 読み上げるテキスト
            
        Returns:
            bool: 送信が成功したかどうか
        """
        if not text:
            return False
        
        try:
            # コマンドデータの作成
            command = self._create_command(text)
            
            # 送信
            return self._send_command(command)
            
        except Exception as e:
            self.logger.error(f"棒読みちゃんへの送信中にエラーが発生しました: {e}", exc_info=True)
            return False
    
    def talk(self, text: str) -> bool:
        """
        棒読みちゃん本体のバイナリTCPプロトコルでコマンド送信する（.NETサンプル準拠）。
        """
        if not text:
            return False
        try:
            # パラメータ（デフォルト値は.NETサンプルに準拠）
            iCommand = 0x0001  # メッセージ読み上げ
            iSpeed   = -1      # 速度（-1:デフォルト）
            iTone    = -1      # 音程（-1:デフォルト）
            iVolume  = -1      # 音量（-1:デフォルト）
            iVoice   = 1       # 声質（1:女性1）
            bCode    = 0       # 文字コード(0:UTF-8)
            bMessage = text.encode('utf-8')
            iLength  = len(bMessage)

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self._timeout)
                sock.connect((self.host, self.port))
                # バイナリで送信
                packet = struct.pack('<hhhhhb', iCommand, iSpeed, iTone, iVolume, iVoice, bCode)
                packet += struct.pack('<I', iLength)
                packet += bMessage
                self.logger.debug(f"送信バイト列: {packet}")
                sock.sendall(packet)
            self.logger.info(f"棒読みちゃん本体にバイナリコマンド送信: {text}")
            return True
        except Exception as e:
            self.logger.error(f"棒読みちゃんバイナリ送信エラー: {e}", exc_info=True)
            return False
    
    def _create_command(self, text: str) -> bytes:
        """棒読みちゃんコマンドデータを作成します。
        
        Args:
            text: 読み上げるテキスト
            
        Returns:
            bytes: コマンドデータ
        """
        # テキストをUTF-8でバイト列に変換
        text_bytes = text.encode('utf-8')
        
        # コマンド形式：
        # [コマンド(1)][速度(2)][音程(2)][音量(2)][声質(1)][エンコード(1)][追加声質(4)][テキスト長(4)][テキスト(可変)]
        # 注意: 数値の型とバイト数が厳密に指定されている
        command = struct.pack(
            '<bhhhbbi',
            0x01,                    # コマンド（0x01：読み上げ）[1バイト]
            self.voice_speed,        # 速度 [2バイト、符号付き]
            self.voice_tone,         # 音程 [2バイト、符号付き]
            self.voice_volume,       # 音量 [2バイト、符号付き]
            self.voice_type,         # 声質 [1バイト、符号なし]
            0x00,                    # エンコード（0：UTF-8, 1：Unicode, 2：Shift-JIS）[1バイト]
            self.voice_type_specific # 追加声質 [4バイト、符号付き]
        )
        
        # テキスト長を追加 [4バイト]
        command += struct.pack('<i', len(text_bytes))
        
        # テキストデータを追加
        command += text_bytes
        
        return command
    
    def _send_command(self, command: bytes) -> bool:
        """コマンドデータを棒読みちゃんに送信します。
        
        Args:
            command: 送信するコマンドデータ
            
        Returns:
            bool: 送信が成功したかどうか
        """
        # 接続または再接続
        if not self._try_connect():
            return False
        
        sock = None
        try:
            # ソケット作成
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # タイムアウト設定
            sock.settimeout(self._timeout)
            
            # 接続
            sock.connect((self.host, self.port))
            
            # コマンド送信
            sock.sendall(command)
            
            # 接続成功を記録
            self._connected = True
            self.logger.debug(f"棒読みちゃんにテキストを送信しました: {len(command)} バイト")
            return True
            
        except ConnectionRefusedError:
            self.logger.warning(f"棒読みちゃんに接続できませんでした: {self.host}:{self.port}")
            self._connected = False
            return False
            
        except socket.timeout:
            self.logger.warning("棒読みちゃんへの接続がタイムアウトしました")
            self._connected = False
            return False
            
        except (ConnectionError, OSError) as e:
            self.logger.error(f"棒読みちゃんへの送信中にエラーが発生しました: {e}", exc_info=True)
            self._connected = False
            return False
            
        except Exception as e:
            self.logger.error(f"棒読みちゃんへの接続中にエラーが発生しました: {e}", exc_info=True)
            self._connected = False
            return False
            
        finally:
            if sock:
                try:
                    sock.close()
                except Exception as e:
                    self.logger.debug(f"ソケットのクローズ中にエラーが発生しました: {e}")
    
    def _try_connect(self) -> bool:
        """棒読みちゃんへの接続を試みます。
        
        接続失敗後一定時間が経過していない場合は、retry_interval秒間は再試行しません。
        
        Returns:
            bool: 接続が可能な状態かどうか
        """
        current_time = time.time()
        
        # すでに接続されているか、前回の接続失敗から一定時間経過している場合のみ接続を試みる
        if self._connected or (current_time - self._last_connect_attempt) >= self._connect_retry_interval:
            self._last_connect_attempt = current_time
            return True
        else:
            # 前回の接続失敗からまだ十分な時間が経過していない
            remain_time = self._connect_retry_interval - (current_time - self._last_connect_attempt)
            self.logger.debug(f"棒読みちゃんへの再接続待機中... あと {remain_time:.1f} 秒")
            return False
    
    def test_connection(self) -> bool:
        """棒読みちゃんとの接続をテストします。
        
        Returns:
            bool: 接続が成功したかどうか
        """
        sock = None
        try:
            # テスト用ソケット作成
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # タイムアウト設定
            sock.settimeout(self._timeout)
            
            # 接続
            sock.connect((self.host, self.port))
            
            self.logger.info(f"棒読みちゃんとの接続テストに成功しました: {self.host}:{self.port}")
            self._connected = True
            return True
            
        except ConnectionRefusedError:
            self.logger.warning(f"棒読みちゃんに接続できませんでした: {self.host}:{self.port}")
            self._connected = False
            return False
            
        except socket.timeout:
            self.logger.warning("棒読みちゃんへの接続がタイムアウトしました")
            self._connected = False
            return False
            
        except Exception as e:
            self.logger.error(f"棒読みちゃんへの接続テスト中にエラーが発生しました: {e}", exc_info=True)
            self._connected = False
            return False
            
        finally:
            if sock:
                try:
                    sock.close()
                except Exception as e:
                    self.logger.debug(f"ソケットのクローズ中にエラーが発生しました: {e}") 