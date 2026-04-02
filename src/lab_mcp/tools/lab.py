import subprocess
import os


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
