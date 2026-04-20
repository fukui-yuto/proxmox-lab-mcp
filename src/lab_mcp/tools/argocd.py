"""ArgoCD REST API を使ったツール群。

環境変数:
    ARGOCD_SERVER  - ArgoCD サーバー URL (例: https://argocd.example.com)
    ARGOCD_TOKEN   - ArgoCD API トークン
"""
import json
import time
import urllib.request
import urllib.error
import ssl
from lab_mcp import config


_token_cache: str = ""


def _get_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not config.ARGOCD_VERIFY_SSL:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _login() -> str:
    """ユーザー名/パスワードで再認証し、新しいトークンを返す。"""
    global _token_cache
    if not config.ARGOCD_USERNAME or not config.ARGOCD_PASSWORD:
        raise RuntimeError("再認証に失敗しました。ARGOCD_USERNAME / ARGOCD_PASSWORD が未設定です")
    url = f"{config.ARGOCD_SERVER.rstrip('/')}/api/v1/session"
    body = json.dumps({"username": config.ARGOCD_USERNAME, "password": config.ARGOCD_PASSWORD}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, context=_get_ctx(), timeout=30) as resp:
        data = json.loads(resp.read().decode())
    _token_cache = data["token"]
    return _token_cache


def _request(method: str, path: str, body: dict | None = None) -> dict:
    """ArgoCD API へリクエストを送る。401 時はトークンを再取得してリトライする。"""
    global _token_cache
    if not config.ARGOCD_SERVER:
        raise RuntimeError("環境変数 ARGOCD_SERVER が未設定です")

    token = _token_cache or config.ARGOCD_TOKEN
    if not token:
        raise RuntimeError("環境変数 ARGOCD_TOKEN が未設定です")

    def _do_request(tok: str) -> dict:
        url = f"{config.ARGOCD_SERVER.rstrip('/')}{path}"
        data = json.dumps(body).encode() if body else None
        headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, context=_get_ctx(), timeout=30) as resp:
            return json.loads(resp.read().decode())

    try:
        return _do_request(token)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        if e.code == 401 and (config.ARGOCD_USERNAME and config.ARGOCD_PASSWORD):
            new_token = _login()
            try:
                return _do_request(new_token)
            except urllib.error.HTTPError as e2:
                body2 = e2.read().decode(errors="replace")
                raise RuntimeError(f"ArgoCD API エラー {e2.code}: {body2}") from e2
        raise RuntimeError(f"ArgoCD API エラー {e.code}: {body_text}") from e


def list_apps(project: str = "") -> list:
    """全アプリケーションの一覧と sync/health 状態を返す。"""
    path = "/api/v1/applications"
    if project:
        path += f"?projects={project}"
    data = _request("GET", path)
    apps = data.get("items") or []
    return [
        {
            "name": a.get("metadata", {}).get("name"),
            "project": a.get("spec", {}).get("project"),
            "namespace": a.get("spec", {}).get("destination", {}).get("namespace"),
            "sync_status": a.get("status", {}).get("sync", {}).get("status"),
            "health_status": a.get("status", {}).get("health", {}).get("status"),
            "repo": a.get("spec", {}).get("source", {}).get("repoURL"),
            "path": a.get("spec", {}).get("source", {}).get("path"),
            "target_revision": a.get("spec", {}).get("source", {}).get("targetRevision"),
        }
        for a in apps
    ]


def get_app(app_name: str) -> dict:
    """指定アプリケーションの詳細（sync/health/resource 一覧）を返す。"""
    data = _request("GET", f"/api/v1/applications/{app_name}")
    status = data.get("status", {})
    return {
        "name": data.get("metadata", {}).get("name"),
        "project": data.get("spec", {}).get("project"),
        "sync_status": status.get("sync", {}).get("status"),
        "sync_revision": status.get("sync", {}).get("revision"),
        "health_status": status.get("health", {}).get("status"),
        "conditions": status.get("conditions") or [],
        "resources": [
            {
                "kind": r.get("kind"),
                "name": r.get("name"),
                "namespace": r.get("namespace"),
                "status": r.get("status"),
                "health": r.get("health", {}).get("status") if r.get("health") else None,
            }
            for r in (status.get("resources") or [])
        ],
    }


def terminate_operation(name: str) -> None:
    """実行中のオペレーションを終了させる。"""
    _request("DELETE", f"/api/v1/applications/{name}/operation")


def sync_app(name: str, revision: str = "", prune: bool = False,
             dry_run: bool = False) -> dict:
    """アプリケーションの sync を実行する。

    既に操作が進行中の場合は終了させてからリトライする。
    """
    body: dict = {}
    if revision:
        body["revision"] = revision
    if prune:
        body["prune"] = True
    if dry_run:
        body["dryRun"] = True
    try:
        return _request("POST", f"/api/v1/applications/{name}/sync", body)
    except RuntimeError as e:
        if "another operation is already in progress" in str(e):
            terminate_operation(name)
            time.sleep(2)
            return _request("POST", f"/api/v1/applications/{name}/sync", body)
        raise


def refresh_app(name: str, hard: bool = True) -> dict:
    """アプリケーションのキャッシュを更新する (hard refresh)。

    既に操作が進行中の場合は終了させてからリトライする。
    """
    refresh_type = "hard" if hard else "normal"
    try:
        return _request("GET", f"/api/v1/applications/{name}?refresh={refresh_type}")
    except RuntimeError as e:
        if "another operation is already in progress" in str(e):
            terminate_operation(name)
            time.sleep(2)
            return _request("GET", f"/api/v1/applications/{name}?refresh={refresh_type}")
        raise


def app_history(name: str) -> list:
    """アプリケーションの sync 履歴を返す。"""
    data = _request("GET", f"/api/v1/applications/{name}")
    history = data.get("status", {}).get("history") or []
    return [
        {
            "id": h.get("id"),
            "revision": h.get("revision", "")[:12],
            "deployed_at": h.get("deployedAt"),
            "source": h.get("source", {}).get("path") or h.get("source", {}).get("chart"),
        }
        for h in history
    ]


def app_managed_resources(name: str) -> list:
    """アプリケーションの管理リソース詳細（live vs desired 差分の有無）を返す。"""
    data = _request("GET", f"/api/v1/applications/{name}/managed-resources")
    items = data.get("items") or []
    return [
        {
            "kind": r.get("kind"),
            "name": r.get("name"),
            "namespace": r.get("namespace"),
            "group": r.get("group", ""),
            "status": r.get("status"),
            "health": r.get("health", {}).get("status") if r.get("health") else None,
            "requires_pruning": r.get("requiresPruning", False),
        }
        for r in items
    ]


def app_resource_diff(name: str) -> list:
    """アプリケーションのリソース差分（live vs desired）を返す。"""
    import urllib.parse
    data = _request("GET", f"/api/v1/applications/{name}/managed-resources")
    items = data.get("items") or []
    diffs = []
    for r in items:
        diff_info = r.get("diff", {})
        if diff_info:
            diffs.append({
                "kind": r.get("kind"),
                "name": r.get("name"),
                "namespace": r.get("namespace"),
                "diff": diff_info,
            })
    return diffs


def list_out_of_sync() -> list:
    """OutOfSync 状態のアプリケーション一覧を返す。"""
    apps = list_apps()
    return [a for a in apps if a.get("sync_status") == "OutOfSync"]


def list_unhealthy() -> list:
    """Healthy 以外の状態のアプリケーション一覧を返す。"""
    apps = list_apps()
    return [a for a in apps if a.get("health_status") != "Healthy"]
