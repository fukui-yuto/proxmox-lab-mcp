import subprocess
from lab_mcp import config


def _run(args: list[str]) -> str:
    env = {"KUBECONFIG": config.KUBECONFIG}
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, **env},
    )
    return (result.stdout + result.stderr).strip()


def get(resource: str, namespace: str | None = None) -> str:
    """kubectl get <resource> を実行する。"""
    args = ["kubectl", "get", resource, "-o", "wide"]
    if namespace:
        args += ["-n", namespace]
    else:
        args += ["--all-namespaces"]
    return _run(args)


def describe(resource: str, name: str, namespace: str | None = None) -> str:
    """kubectl describe <resource> <name> を実行する。"""
    args = ["kubectl", "describe", resource, name]
    if namespace:
        args += ["-n", namespace]
    return _run(args)


def logs(pod: str, namespace: str = "default", tail: int = 100) -> str:
    """kubectl logs で Pod のログを取得する。"""
    return _run(["kubectl", "logs", pod, "-n", namespace, f"--tail={tail}"])


def helm_list(namespace: str | None = None) -> str:
    """helm list で Helm リリース一覧を返す。"""
    args = ["helm", "list"]
    if namespace:
        args += ["-n", namespace]
    else:
        args += ["--all-namespaces"]
    return _run(args)


def helm_get_values(release: str, namespace: str = "default") -> str:
    """helm get values で指定リリースの values を返す。"""
    return _run(["helm", "get", "values", release, "-n", namespace])


def apply(manifest: str) -> str:
    """kubectl apply -f <manifest> を実行する。"""
    return _run(["kubectl", "apply", "-f", manifest])


def rollout_status(deployment: str, namespace: str = "default") -> str:
    """Deployment のロールアウト状態を返す。"""
    return _run(["kubectl", "rollout", "status", f"deployment/{deployment}", "-n", namespace])


def top(resource: str = "nodes", namespace: str | None = None) -> str:
    """kubectl top nodes / pods でリソース使用量を返す。"""
    args = ["kubectl", "top", resource]
    if namespace and resource == "pods":
        args += ["-n", namespace]
    elif resource == "pods":
        args += ["--all-namespaces"]
    return _run(args)
