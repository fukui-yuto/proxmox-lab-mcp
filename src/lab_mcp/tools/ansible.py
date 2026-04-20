import subprocess
from lab_mcp import config

# デフォルトのコマンドタイムアウト (秒)
_DEFAULT_TIMEOUT = 300


def _run(args: list[str], timeout: int = _DEFAULT_TIMEOUT) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=config.ANSIBLE_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0 and not output:
            return f"ERROR: コマンドが終了コード {result.returncode} で失敗しました"
        return output
    except subprocess.TimeoutExpired:
        return f"ERROR: コマンドがタイムアウトしました ({timeout}秒)"
    except FileNotFoundError:
        return f"ERROR: コマンドが見つかりません: {args[0]}"


def ping(hosts: str = "all") -> str:
    """ansible ping で疎通確認する。"""
    return _run(["ansible", "-i", "inventory/hosts.yml", hosts, "-m", "ping"], timeout=60)


def list_inventory() -> str:
    """インベントリのホスト構成を返す。"""
    return _run(["ansible-inventory", "-i", "inventory/hosts.yml", "--list", "--yaml"], timeout=30)


def run_playbook(playbook: str, tags: str = "", limit: str = "") -> str:
    """指定 playbook を実行する（confirm 必須）。

    Args:
        playbook: playbook ファイルパス
        tags: 実行対象タグ（カンマ区切り）
        limit: 対象ホスト制限
    """
    cmd = ["ansible-playbook", "-i", "inventory/hosts.yml", playbook]
    if tags:
        cmd += ["--tags", tags]
    if limit:
        cmd += ["--limit", limit]
    return _run(cmd, timeout=600)


def run_module(hosts: str, module: str, args: str = "") -> str:
    """アドホックモジュールを実行する（例: shell, setup, copy）。"""
    cmd = ["ansible", "-i", "inventory/hosts.yml", hosts, "-m", module]
    if args:
        cmd += ["-a", args]
    if module == "shell":
        cmd += ["-v"]  # stderr も出力に含める
    return _run(cmd)


def get_facts(hosts: str = "all", filter: str = "") -> str:
    """ホストの facts（OS / ハードウェア情報）を収集して返す。

    Args:
        hosts: 対象ホスト/グループ
        filter: facts フィルタ (例: ansible_distribution, ansible_memtotal_mb)
    """
    cmd = ["ansible", "-i", "inventory/hosts.yml", hosts, "-m", "setup"]
    if filter:
        cmd += ["-a", f"filter={filter}"]
    return _run(cmd)


def check_playbook(playbook: str, limit: str = "") -> str:
    """playbook を --check (dry-run) モードで実行し、変更予定を確認する。"""
    cmd = ["ansible-playbook", "-i", "inventory/hosts.yml", playbook, "--check", "--diff"]
    if limit:
        cmd += ["--limit", limit]
    return _run(cmd, timeout=300)
