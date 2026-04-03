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


def get(resource: str, namespace: str | None = None, label_selector: str = "", output: str = "wide") -> str:
    """kubectl get <resource> を実行する。"""
    args = ["kubectl", "get", resource, "-o", output]
    if namespace:
        args += ["-n", namespace]
    else:
        args += ["--all-namespaces"]
    if label_selector:
        args += ["-l", label_selector]
    return _run(args)


def describe(resource: str, name: str, namespace: str | None = None) -> str:
    """kubectl describe <resource> <name> を実行する。"""
    args = ["kubectl", "describe", resource, name]
    if namespace:
        args += ["-n", namespace]
    return _run(args)


def logs(pod: str, namespace: str = "default", tail: int = 100,
         previous: bool = False, container: str = "", since: str = "") -> str:
    """kubectl logs で Pod のログを取得する。"""
    args = ["kubectl", "logs", pod, "-n", namespace, f"--tail={tail}"]
    if previous:
        args += ["--previous"]
    if container:
        args += ["-c", container]
    if since:
        args += [f"--since={since}"]
    return _run(args)


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


def delete(resource: str, name: str, namespace: str | None = None) -> str:
    """kubectl delete <resource> <name> を実行する。"""
    args = ["kubectl", "delete", resource, name]
    if namespace:
        args += ["-n", namespace]
    return _run(args)


def helm_upgrade(release: str, chart: str, namespace: str = "default", values_file: str = "") -> str:
    """helm upgrade --install でリリースをアップグレード／インストールする。"""
    args = ["helm", "upgrade", "--install", release, chart, "-n", namespace]
    if values_file:
        args += ["-f", values_file]
    return _run(args)


def helm_uninstall(release: str, namespace: str = "default") -> str:
    """helm uninstall でリリースを削除する。"""
    return _run(["helm", "uninstall", release, "-n", namespace])


def top(resource: str = "nodes", namespace: str | None = None) -> str:
    """kubectl top nodes / pods でリソース使用量を返す。"""
    args = ["kubectl", "top", resource]
    if namespace and resource == "pods":
        args += ["-n", namespace]
    elif resource == "pods":
        args += ["--all-namespaces"]
    return _run(args)


def exec(pod: str, command: str, namespace: str = "default", container: str = "") -> str:
    """kubectl exec で Pod 内コマンドを実行する。"""
    import shlex
    args = ["kubectl", "exec", pod, "-n", namespace]
    if container:
        args += ["-c", container]
    args += ["--"] + shlex.split(command)
    return _run(args)


def get_events(namespace: str | None = None, field_selector: str = "") -> str:
    """Namespace / Pod のイベント一覧を返す。"""
    args = ["kubectl", "get", "events", "--sort-by=.lastTimestamp"]
    if namespace:
        args += ["-n", namespace]
    else:
        args += ["--all-namespaces"]
    if field_selector:
        args += [f"--field-selector={field_selector}"]
    return _run(args)


def get_secret(name: str, namespace: str = "default") -> str:
    """Secret の内容をマスク付きで返す。"""
    import json
    result = _run(["kubectl", "get", "secret", name, "-n", namespace, "-o", "json"])
    try:
        data = json.loads(result)
        if "data" in data:
            data["data"] = {k: "***" for k in data["data"]}
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return result


def get_configmap(name: str, namespace: str = "default") -> str:
    """ConfigMap の内容を返す。"""
    return _run(["kubectl", "get", "configmap", name, "-n", namespace, "-o", "yaml"])


def run_pod(image: str, command: str, namespace: str = "default") -> str:
    """一時 Pod でコマンドを実行し、出力を返す（Pod は自動削除）。"""
    import shlex, time
    pod_name = f"debug-{int(time.time())}"
    args = ["kubectl", "run", pod_name, f"--image={image}", "-n", namespace,
            "--restart=Never", "--rm", "--attach",
            "--"] + shlex.split(command)
    return _run(args)


def port_forward(resource: str, ports: str, namespace: str = "default") -> str:
    """kubectl port-forward をバックグラウンドで開始する。"""
    import os
    env = {**os.environ, "KUBECONFIG": config.KUBECONFIG}
    proc = subprocess.Popen(
        ["kubectl", "port-forward", resource, ports, "-n", namespace],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    return f"ポートフォワードを開始しました。PID: {proc.pid}, リソース: {resource}, ポート: {ports}\n終了するには kill {proc.pid} を実行してください。"
