"""ArgoCD REST API を使ったツール群。

環境変数:
    ARGOCD_SERVER  - ArgoCD サーバー URL (例: https://argocd.example.com)
    ARGOCD_TOKEN   - ArgoCD API トークン
"""
import json
import urllib.request
import urllib.error
import ssl
from lab_mcp import config


def _request(method: str, path: str, body: dict | None = None) -> dict:
    """ArgoCD API へリクエストを送る。"""
    if not config.ARGOCD_SERVER:
        raise RuntimeError("環境変数 ARGOCD_SERVER が未設定です")
    if not config.ARGOCD_TOKEN:
        raise RuntimeError("環境変数 ARGOCD_TOKEN が未設定です")

    url = f"{config.ARGOCD_SERVER.rstrip('/')}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {
        "Authorization": f"Bearer {config.ARGOCD_TOKEN}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    ctx = ssl.create_default_context()
    if not config.ARGOCD_VERIFY_SSL:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
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


def get_app(name: str) -> dict:
    """指定アプリケーションの詳細（sync/health/resource 一覧）を返す。"""
    data = _request("GET", f"/api/v1/applications/{name}")
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


def sync_app(name: str, revision: str = "", prune: bool = False,
             dry_run: bool = False) -> dict:
    """アプリケーションの sync を実行する。"""
    body: dict = {}
    if revision:
        body["revision"] = revision
    if prune:
        body["prune"] = True
    if dry_run:
        body["dryRun"] = True
    return _request("POST", f"/api/v1/applications/{name}/sync", body)


def refresh_app(name: str, hard: bool = True) -> dict:
    """アプリケーションのキャッシュを更新する (hard refresh)。"""
    refresh_type = "hard" if hard else "normal"
    return _request("GET", f"/api/v1/applications/{name}?refresh={refresh_type}")
