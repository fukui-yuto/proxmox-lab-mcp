import subprocess
import os
import socket
from lab_mcp import config


def ping(host: str, count: int = 4) -> str:
    """指定ホストへの疎通確認を行う。"""
    result = subprocess.run(
        ["ping", "-c", str(count), host],
        capture_output=True,
        text=True,
    )
    return (result.stdout + result.stderr).strip()


def wakeup(mac: str, broadcast: str = "192.168.210.255") -> str:
    """Wake-on-LAN でホストを起動する。

    Args:
        mac: MAC アドレス (例: AA:BB:CC:DD:EE:FF)
        broadcast: ブロードキャストアドレス
    """
    # Magic Packet: 6バイトの0xFF + MACアドレスを16回繰り返す
    mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    magic = b"\xff" * 6 + mac_bytes * 16

    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic, (broadcast, 9))

    return f"Wake-on-LAN パケットを {mac} ({broadcast}) に送信しました。"


def exec(host: str, command: str, user: str = "", ssh_key: str = "") -> str:
    """SSH 経由でホスト上のコマンドを実行する。

    Args:
        host: 接続先ホスト名または IP
        command: 実行するコマンド
        user: SSH ユーザー名（省略時は SSH_USER 環境変数またはシステムデフォルト）
        ssh_key: SSH 秘密鍵パス（省略時は SSH_KEY 環境変数またはシステムデフォルト）
    """
    _user = user or config.SSH_USER
    _key = ssh_key or config.SSH_KEY

    target = f"{_user}@{host}" if _user else host
    args = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes"]
    if _key:
        args += ["-i", _key]
    args += [target, command]

    result = subprocess.run(args, capture_output=True, text=True)
    return (result.stdout + result.stderr).strip()


def check_port(host: str, port: int, timeout: float = 3.0) -> str:
    """指定ホスト・ポートの疎通確認を行う。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return f"{host}:{port} は開いています (OPEN)"
    except (ConnectionRefusedError, socket.timeout):
        return f"{host}:{port} は閉じているかタイムアウトしました (CLOSED/TIMEOUT)"
    except OSError as e:
        return f"{host}:{port} の確認中にエラーが発生しました: {e}"
