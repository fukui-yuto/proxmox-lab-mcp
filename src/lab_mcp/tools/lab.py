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


def exec(host: str, command: str, user: str = "", ssh_key: str = "",
         timeout_seconds: int = 30) -> str:
    """SSH 経由でホスト上のコマンドを実行する。

    Args:
        host: 接続先ホスト名または IP
        command: 実行するコマンド
        user: SSH ユーザー名（省略時は SSH_USER 環境変数またはシステムデフォルト）
        ssh_key: SSH 秘密鍵パス（省略時は SSH_KEY 環境変数またはシステムデフォルト）
        timeout_seconds: タイムアウト秒数（デフォルト: 30）
    """
    _user = user or config.SSH_USER
    _key = ssh_key or config.SSH_KEY

    target = f"{_user}@{host}" if _user else host
    args = [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
    ]
    if _key:
        args += ["-i", _key]
    args += [target, command]

    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout_seconds
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        exit_code = result.returncode

        parts = []
        if stdout:
            parts.append(f"[stdout]\n{stdout}")
        if stderr:
            parts.append(f"[stderr]\n{stderr}")
        if exit_code != 0:
            parts.append(f"[exit_code] {exit_code}")
        return "\n".join(parts) if parts else "(出力なし)"
    except subprocess.TimeoutExpired:
        return f"ERROR: コマンドがタイムアウトしました ({timeout_seconds}秒)。コマンド: {command}"


def dns_lookup(host: str, server: str = "") -> str:
    """DNS 名前解決を行う（dig / nslookup）。

    Args:
        host: 解決するホスト名または IP
        server: 問い合わせ先 DNS サーバー（省略時はシステムデフォルト）
    """
    args = ["dig", "+short", host]
    if server:
        args += [f"@{server}"]
    result = subprocess.run(args, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    return output if output else f"{host} の解決結果が空です（未解決または NXDOMAIN）"


def check_port(host: str, port: int, timeout: float = 3.0) -> str:
    """指定ホスト・ポートの疎通確認を行う。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return f"{host}:{port} は開いています (OPEN)"
    except (ConnectionRefusedError, socket.timeout):
        return f"{host}:{port} は閉じているかタイムアウトしました (CLOSED/TIMEOUT)"
    except OSError as e:
        return f"{host}:{port} の確認中にエラーが発生しました: {e}"
