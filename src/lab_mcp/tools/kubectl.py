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


def get(resource: str, namespace: str | None = None, label_selector: str = "",
        output: str = "wide", jq_filter: str = "") -> str:
    """kubectl get <resource> を実行する。"""
    _output = output
    if jq_filter and output not in ("json", "yaml"):
        _output = "json"
    args = ["kubectl", "get", resource, "-o", _output]
    if namespace:
        args += ["-n", namespace]
    else:
        args += ["--all-namespaces"]
    if label_selector:
        args += ["-l", label_selector]
    result = _run(args)
    if jq_filter:
        import subprocess as _sp, json as _json
        try:
            jq_proc = _sp.run(
                ["jq", "-r", jq_filter],
                input=result, capture_output=True, text=True, timeout=10
            )
            return (jq_proc.stdout + jq_proc.stderr).strip()
        except Exception as e:
            return f"jq フィルタ適用エラー: {e}\n\n{result}"
    return result


def describe(resource: str, name: str, namespace: str | None = None) -> str:
    """kubectl describe <resource> <name> を実行する。"""
    args = ["kubectl", "describe", resource, name]
    if namespace:
        args += ["-n", namespace]
    return _run(args)


def logs(pod_name: str, namespace: str = "default", tail: int = 100,
         previous: bool = False, container: str = "", since: str = "") -> str:
    """kubectl logs で Pod のログを取得する。"""
    args = ["kubectl", "logs", pod_name, "-n", namespace, f"--tail={tail}"]
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


def helm_show_values(chart: str, version: str = "") -> str:
    """helm show values でチャートのデフォルト values を返す。"""
    args = ["helm", "show", "values", chart]
    if version:
        args += ["--version", version]
    return _run(args)


def apply(manifest: str = "", manifest_content: str = "") -> str:
    """kubectl apply を実行する。ファイルパスまたはインライン YAML を受け付ける。"""
    if manifest_content:
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(manifest_content)
            tmp_path = f.name
        try:
            return _run(["kubectl", "apply", "-f", tmp_path])
        finally:
            os.unlink(tmp_path)
    if not manifest:
        return "ERROR: manifest または manifest_content のどちらかを指定してください。"
    return _run(["kubectl", "apply", "-f", manifest])


def patch(resource: str, name: str, patch_json: str,
          namespace: str | None = None, patch_type: str = "merge") -> str:
    """kubectl patch でリソースを部分更新する。"""
    args = ["kubectl", "patch", resource, name, f"--type={patch_type}", f"--patch={patch_json}"]
    if namespace:
        args += ["-n", namespace]
    return _run(args)


def annotate(resource: str, name: str, annotations: str,
             namespace: str | None = None, overwrite: bool = True) -> str:
    """kubectl annotate でアノテーションを追加・更新する。

    Args:
        annotations: スペース区切りの key=value (例: "argocd.argoproj.io/refresh=hard")
    """
    args = ["kubectl", "annotate", resource, name] + annotations.split()
    if overwrite:
        args += ["--overwrite"]
    if namespace:
        args += ["-n", namespace]
    return _run(args)


def wait(resource: str, condition: str, namespace: str | None = None,
         timeout_seconds: int = 60) -> str:
    """kubectl wait でリソースが指定条件になるまで待機する。

    Args:
        resource: リソース指定 (例: pod/my-pod, deployment/nginx, pods --all)
        condition: 待機条件 (例: condition=Ready, condition=Available, delete)
        timeout_seconds: 最大待機秒数 (デフォルト: 60)
    """
    args = ["kubectl", "wait", resource, f"--for={condition}", f"--timeout={timeout_seconds}s"]
    if namespace:
        args += ["-n", namespace]
    else:
        args += ["--all-namespaces"]
    return _run(args)


def rollout_restart(resource: str, namespace: str = "default") -> str:
    """Deployment / StatefulSet / DaemonSet をローリングリスタートする。

    Args:
        resource: リソース指定 (例: deployment/nginx, statefulset/postgres)
    """
    return _run(["kubectl", "rollout", "restart", resource, "-n", namespace])


def rollout_status(resource: str, namespace: str = "default") -> str:
    """Deployment / StatefulSet / DaemonSet のロールアウト状態を返す。

    Args:
        resource: リソース指定 (例: deployment/nginx, statefulset/postgres, daemonset/fluentd)
    """
    return _run(["kubectl", "rollout", "status", resource, "-n", namespace])


def delete(resource: str, name: str, namespace: str | None = None,
           force: bool = False, grace_period: int = -1) -> str:
    """kubectl delete <resource> <name> を実行する。

    Args:
        force: 強制削除 (詰まった Pod の解放に有効)
        grace_period: グレースピリオド秒数 (0 で即時削除。-1 はデフォルト動作)
    """
    args = ["kubectl", "delete", resource, name]
    if namespace:
        args += ["-n", namespace]
    if force:
        args += ["--force"]
    if grace_period >= 0:
        args += [f"--grace-period={grace_period}"]
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


def get_events(namespace: str | None = None, resource_name: str = "",
               resource_kind: str = "", field_selector: str = "") -> str:
    """Namespace / Pod のイベント一覧を返す。

    Args:
        resource_name: 特定リソース名でフィルタ (例: my-pod)
        resource_kind: リソース種別でフィルタ (例: Pod, Deployment)
        field_selector: 追加フィールドセレクタ
    """
    args = ["kubectl", "get", "events", "--sort-by=.lastTimestamp"]
    if namespace:
        args += ["-n", namespace]
    else:
        args += ["--all-namespaces"]
    selectors = []
    if resource_name:
        selectors.append(f"involvedObject.name={resource_name}")
    if resource_kind:
        selectors.append(f"involvedObject.kind={resource_kind}")
    if field_selector:
        selectors.append(field_selector)
    if selectors:
        args += ["--field-selector", ",".join(selectors)]
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
