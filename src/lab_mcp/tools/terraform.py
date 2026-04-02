import subprocess
from lab_mcp import config


def _run(args: list[str], cwd: str | None = None) -> str:
    result = subprocess.run(
        ["terraform"] + args,
        cwd=cwd or config.TERRAFORM_DIR,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    return output.strip()


def plan() -> str:
    """terraform plan を実行して差分を返す。"""
    return _run(["plan", "-no-color"])


def state_list() -> str:
    """terraform state list を実行してリソース一覧を返す。"""
    return _run(["state", "list"])


def state_show(resource: str) -> str:
    """指定リソースの terraform state show を返す。"""
    return _run(["state", "show", "-no-color", resource])


def output() -> str:
    """terraform output を返す。"""
    return _run(["output", "-no-color"])


def apply() -> str:
    """terraform apply を実行する（confirm 必須）。"""
    return _run(["apply", "-auto-approve", "-no-color"])


def validate() -> str:
    """terraform validate で構文検証を行う。"""
    return _run(["validate", "-no-color"])


def destroy() -> str:
    """terraform destroy を実行する（confirm 必須）。"""
    return _run(["destroy", "-auto-approve", "-no-color"])
