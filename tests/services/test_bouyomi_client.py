"""BouyomiClientクラスのテストモジュール。"""

import unittest
from unittest.mock import patch, MagicMock
from src.services.bouyomi_client import BouyomiClient

class TestBouyomiClient(unittest.TestCase):
    """BouyomiClientクラスのテストケース。"""
    
    def setUp(self):
        """各テストケース実行前の準備。"""
        self.config = {
            "BOUYOMI_HOST": "localhost",
            "BOUYOMI_PORT": "50001",
            "BOUYOMI_VOICE": "1",
            "BOUYOMI_VOLUME": "100",
            "BOUYOMI_SPEED": "100",
            "BOUYOMI_TONE": "100",
            "BOUYOMI_COMMAND_TIMEOUT": "1.0"
        }
        self.client = BouyomiClient(self.config)
    
    @patch('socket.socket')
    def test_speak_success(self, mock_socket):
        """正常なテキスト送信のテスト。"""
        # ソケット通信のモック設定
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        
        # テキスト送信
        text = "テストメッセージ"
        result = self.client.speak(text)
        
        # 結果の確認
        self.assertTrue(result)
        mock_socket_instance.connect.assert_called_once_with(('localhost', 50001))
        mock_socket_instance.sendall.assert_called_once()  # sendallが呼ばれることを確認
    
    @patch('socket.socket')
    def test_speak_connection_error(self, mock_socket):
        """接続エラー時のテスト。"""
        # 接続エラーを発生させる
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect.side_effect = ConnectionRefusedError()
        mock_socket.return_value = mock_socket_instance
        
        # テキスト送信
        result = self.client.speak("テストメッセージ")
        
        # 結果の確認
        self.assertFalse(result)
    
    @patch('socket.socket')
    def test_speak_send_error(self, mock_socket):
        """送信エラー時のテスト。"""
        # 送信エラーを発生させる
        mock_socket_instance = MagicMock()
        mock_socket_instance.sendall.side_effect = ConnectionError()  # sendallでエラーを発生
        mock_socket.return_value = mock_socket_instance
        
        # テキスト送信
        result = self.client.speak("テストメッセージ")
        
        # 結果の確認
        self.assertFalse(result)
    
    def test_create_command(self):
        """コマンドデータ作成のテスト。"""
        text = "テスト"
        command = self.client._create_command(text)
        
        # コマンドデータの形式を確認
        self.assertIsInstance(command, bytes)
        self.assertTrue(len(command) > len(text.encode('utf-8')))
    
    @patch('socket.socket')
    def test_test_connection(self, mock_socket):
        """接続テスト機能のテスト。"""
        # 正常な接続をモック
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        
        # 接続テスト実行
        result = self.client.test_connection()
        
        # 結果の確認
        self.assertTrue(result)
        mock_socket_instance.connect.assert_called_once_with(('localhost', 50001))
        mock_socket_instance.close.assert_called_once()

if __name__ == '__main__':
    unittest.main() 