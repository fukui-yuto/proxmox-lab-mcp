import subprocess
import os
import socket
from lab_mcp import config


def ping(host: str, count: int = 4) -> str:
    """指定ホストへの疎通確認を行う。"""
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), host],
            capture_output=True,
            text=True,
            timeout=count * 5 + 10,
        )
        return (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return f"ERROR: ping がタイムアウトしました ({host})"
    except FileNotFoundError:
        return "ERROR: ping コマンドが見つかりません"


def wakeup(mac: str, broadcast: str = "192.168.210.255") -> str:
    """Wake-on-LAN でホストを起動する。"""
    mac_clean = mac.replace(":", "").replace("-", "")
    if len(mac_clean) != 12:
        return f"ERROR: 無効な MAC アドレスです: {mac}"
    try:
        mac_bytes = bytes.fromhex(mac_clean)
    except ValueError:
        return f"ERROR: 無効な MAC アドレスです: {mac}"
    magic = b"\xff" * 6 + mac_bytes * 16

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic, (broadcast, 9))

    return f"Wake-on-LAN パケットを {mac} ({broadcast}) に送信しました。"


def exec(host: str, command: str, user: str = "", ssh_key: str = "",
         timeout_seconds: int = 120) -> str:
    """SSH 経由でホスト上のコマンドを実行する。"""
    _user = user or config.SSH_USER
    _key = ssh_key or config.SSH_KEY

    target = f"{_user}@{host}" if _user else host
    args = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
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
            # SSH の警告メッセージを除外
            filtered = "\n".join(
                line for line in stderr.splitlines()
                if not line.startswith("Warning: Permanently added")
            ).strip()
            if filtered:
                parts.append(f"[stderr]\n{filtered}")
        if exit_code != 0:
            parts.append(f"[exit_code] {exit_code}")
        return "\n".join(parts) if parts else "(出力なし)"
    except subprocess.TimeoutExpired:
        return f"ERROR: コマンドがタイムアウトしました ({timeout_seconds}秒)。コマンド: {command}"


def dns_lookup(host: str, server: str = "", record_type: str = "") -> str:
    """DNS 名前解決を行う（dig / nslookup）。

    Args:
        host: 解決するホスト名または IP
        server: 問い合わせ先 DNS サーバー
        record_type: レコードタイプ (例: A, AAAA, CNAME, MX, TXT, PTR)
    """
    args = ["dig", "+short", host]
    if record_type:
        args += [record_type]
    if server:
        args += [f"@{server}"]
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=10)
        output = (result.stdout + result.stderr).strip()
        return output if output else f"{host} の解決結果が空です（未解決または NXDOMAIN）"
    except subprocess.TimeoutExpired:
        return f"ERROR: DNS lookup がタイムアウトしました ({host})"
    except FileNotFoundError:
        return "ERROR: dig コマンドが見つかりません"


def check_port(host: str, port: int, timeout: float = 3.0) -> str:
    """指定ホスト・ポートの疎通確認を行う。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return f"{host}:{port} は開いています (OPEN)"
    except (ConnectionRefusedError, socket.timeout):
        return f"{host}:{port} は閉じているかタイムアウトしました (CLOSED/TIMEOUT)"
    except OSError as e:
        return f"{host}:{port} の確認中にエラーが発生しました: {e}"


def check_ports(host: str, ports: str, timeout: float = 2.0) -> str:
    """複数ポートの疎通を一括確認する。

    Args:
        host: ホスト名または IP
        ports: カンマ区切りのポート番号 (例: "22,80,443,6443")
        timeout: 各ポートのタイムアウト秒数
    """
    results = []
    for p in ports.split(","):
        p = p.strip()
        if not p.isdigit():
            results.append(f"  {p}: 無効なポート番号")
            continue
        port = int(p)
        try:
            with socket.create_connection((host, port), timeout=timeout):
                results.append(f"  {port}: OPEN")
        except (ConnectionRefusedError, socket.timeout, OSError):
            results.append(f"  {port}: CLOSED")
    return f"{host} ポートスキャン結果:\n" + "\n".join(results)


def traceroute(host: str, max_hops: int = 15) -> str:
    """traceroute でネットワーク経路を確認する。"""
    try:
        result = subprocess.run(
            ["traceroute", "-m", str(max_hops), host],
            capture_output=True,
            text=True,
            timeout=max_hops * 5 + 10,
        )
        return (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return f"ERROR: traceroute がタイムアウトしました ({host})"
    except FileNotFoundError:
        return "ERROR: traceroute コマンドが見つかりません"


def curl(url: str, method: str = "GET", headers: str = "", data: str = "",
         timeout_seconds: int = 30, insecure: bool = False) -> str:
    """curl で HTTP リクエストを実行する（ラボ内サービスの接続テストに有用）。

    Args:
        url: リクエスト先 URL
        method: HTTP メソッド (GET, POST, PUT, DELETE 等)
        headers: ヘッダー（改行区切り, 例: "Content-Type: application/json")
        data: リクエストボディ
        timeout_seconds: タイムアウト秒数
        insecure: SSL 証明書検証をスキップする
    """
    args = ["curl", "-s", "-w", "\n---\nHTTP_CODE: %{http_code}\nTIME_TOTAL: %{time_total}s",
            "-X", method, "--max-time", str(timeout_seconds)]
    if insecure:
        args += ["-k"]
    if headers:
        for h in headers.split("\n"):
            h = h.strip()
            if h:
                args += ["-H", h]
    if data:
        args += ["-d", data]
    args += [url]
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout_seconds + 10)
        return (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return f"ERROR: curl がタイムアウトしました ({url})"
    except FileNotFoundError:
        return "ERROR: curl コマンドが見つかりません"
