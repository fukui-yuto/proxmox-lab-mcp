# MCP サーバー 改善課題

このセッション (2026-04-11) で発見された MCP ツールの問題・改善点をまとめる。

---

## 1. `lab_exec` — SSH ホストキー変更時に接続失敗

**症状:**
```
WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!
Offending ED25519 key in /root/.ssh/known_hosts:25
Host key verification failed. [exit_code] 255
```

**原因:**
VM 再作成後にホストキーが変わると、既存の `known_hosts` エントリと衝突して接続できない。
現在の実装は `StrictHostKeyChecking=accept-new` を使っているが、これは **新規ホストのみ** 自動登録し、既存エントリと異なるキーは拒否する。

**対処案:**
`StrictHostKeyChecking=no` + `UserKnownHostsFile=/dev/null` に変更する（ラボ内ホスト限定のため MITM リスクは許容範囲）。

```python
# lab.py の SSH コマンド部分
"-o", "StrictHostKeyChecking=no",
"-o", "UserKnownHostsFile=/dev/null",
```

または、接続失敗時に `ssh-keygen -R <host>` で古いキーを削除してリトライする仕組みを追加する。

---

## 2. `lab_exec` — デフォルトタイムアウト 30 秒が短すぎる

**症状:**
```
ERROR: コマンドがタイムアウトしました (30秒)。コマンド: sudo kubectl get pods -A ...
```

**原因:**
クラスター全体を対象にした `kubectl` コマンド、Ansible playbook、`journalctl` 等は 30 秒を超えることが多い。

**対処案:**
デフォルトを 60〜120 秒に変更する。または呼び出し側が指定できる `timeout_seconds` パラメータのデフォルト値を増やす。

```python
# lab.py
def exec(host: str, command: str, user: str = "root",
         timeout_seconds: int = 120) -> str:  # 30 → 120
```

---

## 3. `kubectl_rollout_status` — StatefulSet / DaemonSet に非対応

**症状:**
```
Error: 1 validation error for kubectl_rollout_statusArguments
deployment: Field required
```

**原因:**
現実装は `deployment/{name}` に固定:
```python
def rollout_status(deployment: str, namespace: str = "default") -> str:
    return _run(["kubectl", "rollout", "status", f"deployment/{deployment}", ...])
```

**対処案:**
`resource` パラメータにして、任意のリソース種別に対応する。

```python
def rollout_status(resource: str, namespace: str = "default") -> str:
    """
    Args:
        resource: リソース指定 (例: deployment/nginx, statefulset/postgres, daemonset/fluentd)
    """
    return _run(["kubectl", "rollout", "status", resource, "-n", namespace])
```

---

## 4. `kubectl_get_events` — 特定リソースでフィルタリングできない

**症状:**
`kubectl_get_events` に `resource_name` パラメータがなく、Pod 単体のイベントを取得できない。
代わりに `kubectl_describe` を使うか、`field_selector` に `involvedObject.name=xxx` を手動で渡す必要があった。

**対処案:**
`resource_name` と `resource_kind` パラメータを追加する。

```python
def get_events(namespace: str | None = None,
               resource_name: str = "",
               resource_kind: str = "",
               field_selector: str = "") -> str:
    args = ["kubectl", "get", "events", "--sort-by=.lastTimestamp"]
    if namespace:
        args += ["-n", namespace]
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
```

---

## 5. `kubectl_logs` — パラメータ名の不一致

**症状:**
```
Error: 1 validation error for kubectl_logsArguments
pod: Field required [input_value={'pod_name': 'harbor-trivy-0', ...}]
```

**原因:**
ツールの実装は `pod` だが、ツール説明に `pod_name` と記述されている箇所があり混乱する。

**対処案:**
パラメータ名を `pod_name` に統一するか、ドキュメントを `pod` に合わせる。

---

## 6. `kubectl_delete` — Pod 削除が詰まる問題への対応

**症状:**
Longhorn ボリューム付き Pod や、kyverno webhook 障害時に `kubectl delete pod` が詰まって応答しなくなる。

**現状:**
`kubectl_delete` は単純に `kubectl delete <resource> <name>` を実行するだけで、タイムアウト・フォース削除オプションがない。

**対処案:**
`force` オプションと `grace_period` オプションを追加する。

```python
def delete(resource: str, name: str, namespace: str | None = None,
           force: bool = False, grace_period: int = -1) -> str:
    args = ["kubectl", "delete", resource, name]
    if namespace:
        args += ["-n", namespace]
    if force:
        args += ["--force"]
    if grace_period >= 0:
        args += [f"--grace-period={grace_period}"]
    return _run(args)
```

また、タイムアウトを設定して詰まりを防ぐ:
```python
# _run() にタイムアウトを追加 (例: 30s)
result = subprocess.run(args, capture_output=True, text=True, timeout=30)
```

---

## 7. ArgoCD — セッション切れ後に自動再認証しない

**症状:**
```
ERROR: ArgoCD API エラー 401: {"error":"invalid session: account password has changed since token issued"}
```

**原因:**
ArgoCD のパスワード変更や長時間経過後にトークンが無効化されると、MCP サーバーが再ログインせずエラーを返し続ける。

**対処案:**
401 エラー時に `argocd login` を再実行してトークンを更新し、リトライする。

```python
# argocd.py
def _argocd(args: list[str]) -> str:
    result = _run(args)
    if "invalid session" in result or "401" in result:
        _login()  # 再認証
        result = _run(args)  # リトライ
    return result
```

---

## 8. `kubectl_get` — jq フィルタのパースエラー

**症状:**
```
jq: parse error: Invalid numeric literal at line 9, column 6
```

**原因:**
Claude が渡す jq フィルタ式（特に `select()` や数値比較を含む複雑な式）が、Python 側のエスケープ処理やシェル経由の引数渡しで破損することがある。

**対処案:**
jq をシェル経由ではなく、`subprocess` で直接 stdin にフィルタを渡す。

```python
# jq フィルタをファイルまたは stdin で渡す
result = subprocess.run(
    ["jq", "-r", jq_filter],
    input=json_output,
    capture_output=True, text=True
)
```

または、`--arg` や `--argjson` を使って jq に安全に値を渡す。

---

## 9. `argocd_get_app` — パラメータ名の不一致

**症状:**
```
Error: 1 validation error for argocd_get_appArguments
name: Field required [input_value={'app_name': 'harbor'}, ...]
```

**原因:**
`argocd_get_app` のパラメータ名が `name` だが、ツール説明文に `app_name` と記述されている。

**対処案:**
パラメータ名を `app_name` に統一する（他の ArgoCD ツールとも一貫させる）。

---

## 10. `kubectl_delete` の二重確認問題

**現状:**
Claude Code の UI でユーザーがツール呼び出しを承認 → さらに `confirm=true` が必要という二重確認になっている。

`kubectl_delete (volumeattachment, csi-xxx...)` → ユーザーが承認を拒否 → Claude が `confirm=true` を付けて再試行 → 再度ユーザーが承認 という流れになり、ユーザー体験が悪い。

**対処案:**
Claude Code の UI がすでに確認ステップになっているため、`confirm` パラメータは削除するか、デフォルト `true` にする。
あるいは、`kubectl_delete` を完全に廃止して `kubectl_patch` でのファイナライザ削除 + スケール操作で代替する方法を検討する。

---

## 優先度まとめ

| # | 課題 | 影響度 | 対応コスト | 状態 |
|---|------|--------|-----------|------|
| 1 | `lab_exec` SSH ホストキー問題 | 高 (接続不可) | 低 | ✅ 対応済 |
| 2 | `lab_exec` タイムアウト | 高 (頻発) | 低 | ✅ 対応済 |
| 3 | `kubectl_rollout_status` 汎用化 | 中 | 低 | ✅ 対応済 |
| 4 | `kubectl_get_events` フィルタ | 中 | 低 | ✅ 対応済 |
| 6 | `kubectl_delete` 詰まり対策 | 高 | 中 | ✅ 対応済 |
| 7 | ArgoCD 自動再認証 | 中 | 中 | ✅ 対応済 |
| 8 | jq パースエラー | 中 | 中 | ✅ 対応済 |
| 5 | `kubectl_logs` パラメータ名 | 低 | 低 | ✅ 対応済 |
| 9 | `argocd_get_app` パラメータ名 | 低 | 低 | ✅ 対応済 |
| 10 | `kubectl_delete` 二重確認 | 低 | 中 | ✅ 対応済 |
