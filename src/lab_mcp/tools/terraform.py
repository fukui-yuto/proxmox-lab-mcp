import subprocess
from pathlib import Path
from lab_mcp import config

# デフォルトのコマンドタイムアウト (秒)
_DEFAULT_TIMEOUT = 300


def _run(args: list[str], cwd: str | None = None, timeout: int = _DEFAULT_TIMEOUT) -> str:
    try:
        result = subprocess.run(
            ["terraform"] + args,
            cwd=cwd or config.TERRAFORM_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0 and not output:
            return f"ERROR: terraform が終了コード {result.returncode} で失敗しました"
        return output
    except subprocess.TimeoutExpired:
        return f"ERROR: terraform コマンドがタイムアウトしました ({timeout}秒)"
    except FileNotFoundError:
        return "ERROR: terraform コマンドが見つかりません。PATH を確認してください。"


def init() -> str:
    """terraform init を実行する（プラグイン取得・バックエンド初期化）。"""
    return _run(["init", "-no-color"], timeout=180)


def plan() -> str:
    """terraform plan を実行して差分を返す。"""
    return _run(["plan", "-no-color"])


def plan_target(target: str) -> str:
    """特定リソースのみの terraform plan を実行する。"""
    return _run(["plan", "-no-color", f"-target={target}"])


def state_list() -> str:
    """terraform state list を実行してリソース一覧を返す。"""
    return _run(["state", "list"], timeout=30)


def state_show(resource: str) -> str:
    """指定リソースの terraform state show を返す。"""
    return _run(["state", "show", "-no-color", resource], timeout=30)


def output() -> str:
    """terraform output を返す。"""
    return _run(["output", "-no-color"], timeout=30)


def output_json() -> str:
    """terraform output を JSON 形式で返す（プログラム処理に便利）。"""
    return _run(["output", "-json", "-no-color"], timeout=30)


def apply() -> str:
    """terraform apply を実行する（confirm 必須）。"""
    return _run(["apply", "-auto-approve", "-no-color"], timeout=600)


def apply_target(target: str) -> str:
    """特定リソースのみの terraform apply を実行する（confirm 必須）。"""
    return _run(["apply", "-auto-approve", "-no-color", f"-target={target}"], timeout=600)


def validate() -> str:
    """terraform validate で構文検証を行う。"""
    return _run(["validate", "-no-color"], timeout=30)


def destroy() -> str:
    """terraform destroy を実行する（confirm 必須）。"""
    return _run(["destroy", "-auto-approve", "-no-color"], timeout=600)


def show() -> str:
    """terraform show で現在の state サマリーを返す。"""
    return _run(["show", "-no-color"], timeout=60)


def providers() -> str:
    """使用中の provider 一覧とバージョンを返す。"""
    return _run(["providers", "-no-color"], timeout=30)


def git_pull() -> str:
    """git pull で TERRAFORM_DIR のリポジトリを最新化する。"""
    repo_dir = str(Path(config.TERRAFORM_DIR).parent)
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return "ERROR: git pull がタイムアウトしました (60秒)"
