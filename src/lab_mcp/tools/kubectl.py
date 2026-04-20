import subprocess
import shlex
import json
import time
import os
import tempfile
from lab_mcp import config

# デフォルトのコマンドタイムアウト (秒)
_DEFAULT_TIMEOUT = 120


def _run(args: list[str], timeout: int = _DEFAULT_TIMEOUT) -> str:
    env = {**os.environ, "KUBECONFIG": config.KUBECONFIG}
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0 and not output:
            return f"ERROR: コマンドが終了コード {result.returncode} で失敗しました"
        return output
    except subprocess.TimeoutExpired:
        return f"ERROR: コマンドがタイムアウトしました ({timeout}秒): {' '.join(args[:4])}..."
    except FileNotFoundError:
        return f"ERROR: コマンドが見つかりません: {args[0]}"


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
        try:
            jq_proc = subprocess.run(
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


def helm_history(release: str, namespace: str = "default") -> str:
    """helm history でリリースの履歴（リビジョン一覧）を返す。"""
    return _run(["helm", "history", release, "-n", namespace])


def helm_rollback(release: str, revision: int, namespace: str = "default") -> str:
    """helm rollback でリリースを指定リビジョンに戻す。"""
    return _run(["helm", "rollback", release, str(revision), "-n", namespace])


def apply(manifest: str = "", manifest_content: str = "") -> str:
    """kubectl apply を実行する。ファイルパスまたはインライン YAML を受け付ける。"""
    if manifest_content:
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
    """kubectl annotate でアノテーションを追加・更新する。"""
    args = ["kubectl", "annotate", resource, name] + annotations.split()
    if overwrite:
        args += ["--overwrite"]
    if namespace:
        args += ["-n", namespace]
    return _run(args)


def wait(resource: str, condition: str, namespace: str | None = None,
         timeout_seconds: int = 60) -> str:
    """kubectl wait でリソースが指定条件になるまで待機する。"""
    args = ["kubectl", "wait", resource, f"--for={condition}", f"--timeout={timeout_seconds}s"]
    if namespace:
        args += ["-n", namespace]
    else:
        args += ["--all-namespaces"]
    return _run(args, timeout=timeout_seconds + 10)


def rollout_restart(resource: str, namespace: str = "default") -> str:
    """Deployment / StatefulSet / DaemonSet をローリングリスタートする。"""
    return _run(["kubectl", "rollout", "restart", resource, "-n", namespace])


def rollout_status(resource: str, namespace: str = "default") -> str:
    """Deployment / StatefulSet / DaemonSet のロールアウト状態を返す。"""
    return _run(["kubectl", "rollout", "status", resource, "-n", namespace, "--timeout=30s"], timeout=40)


def delete(resource: str, name: str, namespace: str | None = None,
           force: bool = False, grace_period: int = -1) -> str:
    """kubectl delete <resource> <name> を実行する。"""
    args = ["kubectl", "delete", resource, name]
    if namespace:
        args += ["-n", namespace]
    if force:
        args += ["--force"]
    if grace_period >= 0:
        args += [f"--grace-period={grace_period}"]
    return _run(args)


def scale(resource: str, replicas: int, namespace: str = "default") -> str:
    """kubectl scale でレプリカ数を変更する。"""
    return _run(["kubectl", "scale", resource, f"--replicas={replicas}", "-n", namespace])


def cordon(node: str) -> str:
    """kubectl cordon でノードをスケジュール不可にする。"""
    return _run(["kubectl", "cordon", node])


def uncordon(node: str) -> str:
    """kubectl uncordon でノードのスケジュールを再開する。"""
    return _run(["kubectl", "uncordon", node])


def get_pvc(namespace: str | None = None, label_selector: str = "") -> str:
    """PersistentVolumeClaim の一覧と状態を返す。"""
    args = ["kubectl", "get", "pvc", "-o", "wide"]
    if namespace:
        args += ["-n", namespace]
    else:
        args += ["--all-namespaces"]
    if label_selector:
        args += ["-l", label_selector]
    return _run(args)


def get_pv() -> str:
    """PersistentVolume の一覧と状態を返す。"""
    return _run(["kubectl", "get", "pv", "-o", "wide"])


def get_ingress(namespace: str | None = None) -> str:
    """Ingress リソースの一覧を返す。"""
    args = ["kubectl", "get", "ingress", "-o", "wide"]
    if namespace:
        args += ["-n", namespace]
    else:
        args += ["--all-namespaces"]
    return _run(args)


def get_endpoints(name: str = "", namespace: str | None = None) -> str:
    """Endpoints の一覧を返す（Service→Pod の接続確認に有用）。"""
    args = ["kubectl", "get", "endpoints"]
    if name:
        args += [name]
    if namespace:
        args += ["-n", namespace]
    else:
        args += ["--all-namespaces"]
    args += ["-o", "wide"]
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
    args = ["kubectl", "exec", pod, "-n", namespace]
    if container:
        args += ["-c", container]
    args += ["--"] + shlex.split(command)
    return _run(args)


def get_events(namespace: str | None = None, resource_name: str = "",
               resource_kind: str = "", field_selector: str = "") -> str:
    """Namespace / Pod のイベント一覧を返す。"""
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


def get_secret(name: str, namespace: str = "default", decode: bool = False) -> str:
    """Secret の内容を返す。decode=False ではマスク、True ではデコード済み値を表示。"""
    result = _run(["kubectl", "get", "secret", name, "-n", namespace, "-o", "json"])
    try:
        data = json.loads(result)
        if "data" in data:
            if decode:
                import base64
                data["data"] = {
                    k: base64.b64decode(v).decode(errors="replace")
                    for k, v in data["data"].items()
                }
            else:
                data["data"] = {k: "***" for k in data["data"]}
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return result


def get_configmap(name: str, namespace: str = "default") -> str:
    """ConfigMap の内容を返す。"""
    return _run(["kubectl", "get", "configmap", name, "-n", namespace, "-o", "yaml"])


def run_pod(image: str, command: str, namespace: str = "default") -> str:
    """一時 Pod でコマンドを実行し、出力を返す（Pod は自動削除）。"""
    pod_name = f"debug-{int(time.time())}"
    args = ["kubectl", "run", pod_name, f"--image={image}", "-n", namespace,
            "--restart=Never", "--rm", "--attach",
            "--"] + shlex.split(command)
    return _run(args, timeout=180)


def port_forward(resource: str, ports: str, namespace: str = "default") -> str:
    """kubectl port-forward をバックグラウンドで開始する。"""
    env = {**os.environ, "KUBECONFIG": config.KUBECONFIG}
    proc = subprocess.Popen(
        ["kubectl", "port-forward", resource, ports, "-n", namespace],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    return f"ポートフォワードを開始しました。PID: {proc.pid}, リソース: {resource}, ポート: {ports}\n終了するには kill {proc.pid} を実行してください。"


def drain(node: str, ignore_daemonsets: bool = True, delete_emptydir_data: bool = True,
          force: bool = False, timeout_seconds: int = 300) -> str:
    """kubectl drain でノードからワークロードを退避する。"""
    args = ["kubectl", "drain", node]
    if ignore_daemonsets:
        args += ["--ignore-daemonsets"]
    if delete_emptydir_data:
        args += ["--delete-emptydir-data"]
    if force:
        args += ["--force"]
    args += [f"--timeout={timeout_seconds}s"]
    return _run(args, timeout=timeout_seconds + 30)


def get_longhorn_volumes(namespace: str = "longhorn-system") -> str:
    """Longhorn ボリューム一覧と状態を返す。"""
    return _run(["kubectl", "get", "volumes.longhorn.io", "-n", namespace, "-o", "wide"])


def get_velero_backups() -> str:
    """Velero バックアップ一覧を返す。"""
    return _run(["kubectl", "get", "backups.velero.io", "-n", "velero", "-o", "wide"])


def get_velero_restores() -> str:
    """Velero リストア一覧を返す。"""
    return _run(["kubectl", "get", "restores.velero.io", "-n", "velero", "-o", "wide"])


def get_velero_schedules() -> str:
    """Velero スケジュール一覧を返す。"""
    return _run(["kubectl", "get", "schedules.velero.io", "-n", "velero", "-o", "wide"])


def create_velero_backup(name: str, namespaces: str = "", selector: str = "") -> str:
    """Velero バックアップを作成する。"""
    manifest = {
        "apiVersion": "velero.io/v1",
        "kind": "Backup",
        "metadata": {"name": name, "namespace": "velero"},
        "spec": {},
    }
    if namespaces:
        manifest["spec"]["includedNamespaces"] = [ns.strip() for ns in namespaces.split(",")]
    if selector:
        manifest["spec"]["labelSelector"] = {"matchLabels": dict(
            item.split("=") for item in selector.split(",")
        )}
    content = json.dumps(manifest)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        return _run(["kubectl", "apply", "-f", tmp_path])
    finally:
        os.unlink(tmp_path)


def create_velero_restore(name: str, backup_name: str, namespaces: str = "") -> str:
    """Velero リストアを作成する。"""
    manifest = {
        "apiVersion": "velero.io/v1",
        "kind": "Restore",
        "metadata": {"name": name, "namespace": "velero"},
        "spec": {"backupName": backup_name},
    }
    if namespaces:
        manifest["spec"]["includedNamespaces"] = [ns.strip() for ns in namespaces.split(",")]
    content = json.dumps(manifest)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        return _run(["kubectl", "apply", "-f", tmp_path])
    finally:
        os.unlink(tmp_path)


def get_cilium_status() -> str:
    """Cilium の状態を返す (cilium status via DaemonSet Pod)。"""
    # cilium CLI がインストールされていない環境向けに Pod 経由で実行
    result = _run(["kubectl", "get", "pods", "-n", "kube-system", "-l", "k8s-app=cilium",
                   "-o", "jsonpath={.items[0].metadata.name}"])
    if result.startswith("ERROR"):
        return result
    pod_name = result.strip()
    if not pod_name:
        return "ERROR: Cilium Pod が見つかりません"
    return _run(["kubectl", "exec", "-n", "kube-system", pod_name, "-c", "cilium-agent",
                 "--", "cilium", "status", "--brief"], timeout=30)


def get_vault_status() -> str:
    """Vault の状態 (sealed/unsealed) を返す。"""
    result = _run(["kubectl", "get", "pods", "-n", "vault", "-l", "app.kubernetes.io/name=vault",
                   "-o", "jsonpath={.items[0].metadata.name}"])
    if result.startswith("ERROR"):
        return result
    pod_name = result.strip()
    if not pod_name:
        return "ERROR: Vault Pod が見つかりません"
    return _run(["kubectl", "exec", "-n", "vault", pod_name, "--",
                 "vault", "status", "-format=json"], timeout=15)
