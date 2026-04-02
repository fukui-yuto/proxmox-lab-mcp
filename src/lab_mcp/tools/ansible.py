import subprocess
from lab_mcp import config


def _run(args: list[str]) -> str:
    result = subprocess.run(
        args,
        cwd=config.ANSIBLE_DIR,
        capture_output=True,
        text=True,
    )
    return (result.stdout + result.stderr).strip()


def ping(hosts: str = "all") -> str:
    """ansible ping で疎通確認する。"""
    return _run(["ansible", "-i", "inventory/hosts.yml", hosts, "-m", "ping"])


def list_inventory() -> str:
    """インベントリのホスト構成を返す。"""
    return _run(["ansible-inventory", "-i", "inventory/hosts.yml", "--list", "--yaml"])


def run_playbook(playbook: str) -> str:
    """指定 playbook を実行する（confirm 必須）。"""
    return _run(["ansible-playbook", "-i", "inventory/hosts.yml", playbook])
