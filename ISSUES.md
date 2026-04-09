# MCP サーバー 問題点・改善要望まとめ

---

## 既知の不具合

### 1. lab_exec が SSH 接続できない (Pi への root 接続)

**症状**
- `host: 192.168.210.55` (Raspberry Pi) への接続が `Permission denied (publickey,password)` で失敗

**影響**
- ラボ管理端末 (Pi) で kubectl / ansible / terraform を実行できない
- k3s-master (192.168.210.21) に ubuntu ユーザーで接続することで一部回避できるが毎回 host key 警告が出る

**要望**
- 接続ユーザーを設定ファイルや環境変数で指定できるようにする
- ホストごとにユーザー・鍵ファイルを設定できるようにする

---

### 2. lab_exec がハング → MCP サーバー全体がフリーズ 【最優先】

**症状**
- `lab_exec` が出力なしで無応答になることがある
- 以降の全 MCP ツール呼び出しも無応答になり、Claude Code 再起動が必要

**再現ケース**
- `sleep 30 && kubectl get ...` のような長時間コマンド実行時
- 複数回 lab_exec を連続実行した後

**要望**
- コマンドタイムアウトを設定可能にする（デフォルト 30 秒など）
- タイムアウト時は明示的なエラーメッセージを返す
- 1 コマンドのハングで MCP サーバー全体が止まらないよう非同期処理を改善する

---

### 3. kubectl_apply がインライン YAML を受け付けない

**症状**
- `manifest` パラメータにファイルパスしか渡せず、YAML 文字列を渡すと「the path ... does not exist」エラー

**影響**
- git push → ラボ側でパスを指定、という回り道が必要
- 未 push のマニフェストをその場で apply できない

**要望**
- YAML 文字列をインラインで渡せるようにする（ファイルパスか文字列かを自動判定、または別パラメータ `manifest_content` を追加）

---

### 4. SSH host key mismatch 警告がノイズになる

**症状**
- k3s-master への接続時に毎回 `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!` が出力に混入する

**要望**
- `StrictHostKeyChecking=accept-new` を使用する、または known_hosts を自動更新する
- 少なくとも SSH 警告を stderr として分離し、ツール出力に混入しないようにする

---

### 5. kubectl_apply のパス解決がラボ側基準

**症状**
- パスがラボ側 (Raspberry Pi) のファイルシステム基準のため、Windows 側のパスは使えない

**要望**
- インライン YAML 対応 (#3 と共通) で解消される

---

## 機能追加の要望

### 6. 不足している kubectl 操作ツール

今回の作業で `lab_exec` に逃げざるを得なかった操作：

| 必要だった操作 | 提案するツール |
|---------------|---------------|
| `kubectl patch` | `kubectl_patch` |
| `kubectl delete` | `kubectl_delete` |
| `kubectl annotate` | `kubectl_annotate` (または patch で代用) |
| `kubectl rollout status` | `kubectl_rollout_status` |
| `kubectl wait --for=condition=...` | `kubectl_wait` |
| `kubectl top nodes/pods` | `kubectl_top` |

---

### 7. kubectl_get の大量出力問題

**症状**
- `kubectl get pods -A -o yaml` などで出力が巨大になり、ファイルに保存されるが読み取りが面倒

**要望**
- `jq` フィルタを指定できるパラメータを追加する（例: `jq: '.items[].metadata.name'`）
- デフォルトで出力を N 行に制限し、超えた場合はファイル保存する現在の動作をオプション化する
- `kubectl_get` に `output: "wide"` を指定したとき、テーブル形式で返すようにする（現在は `-o wide` 扱いにならないケースがある）

---

### 8. ArgoCD 専用ツール

今回 ArgoCD の操作で `lab_exec` + `kubectl patch` で代替したが、専用ツールがあると便利：

| 提案ツール | 相当する操作 |
|-----------|-------------|
| `argocd_sync` | `argocd app sync <app>` |
| `argocd_refresh` | hard refresh のトリガー |
| `argocd_get_app` | アプリの sync/health 状態取得 |
| `argocd_list_apps` | 全アプリの一覧と状態 |

---

### 9. Helm 操作ツール

ArgoCD 管理のリリースは `helm list` に出ないが、直接 Helm で管理している場合に有用：

| 提案ツール | 相当する操作 |
|-----------|-------------|
| `helm_list` | `helm list -A` |
| `helm_get_values` | `helm get values <release> -n <ns>` |
| `helm_show_values` | `helm show values <chart> --version <ver>` |

`helm_show_values` は今回 chart のデフォルト値確認で何度も必要になった。

---

### 10. lab_exec の出力改善

**現状の問題**
- stdout と stderr が混在して返ってくる
- SSH 警告、kubectl の warning、実際の出力が区別できない

**要望**
- `stdout` / `stderr` / `exit_code` を分けて返す
- `exit_code != 0` のときは明示的にエラーとして扱う

---

### 11. kubectl_describe ツールの引数仕様が不明確

**症状**
- `resource` と `name` を別パラメータで渡す必要があるが、`kubectl describe pod mypod` のように `resource` に `pod mypod` を渡せない

**要望**
- `kubectl describe <resource> <name>` の形式をそのまま受け付けられるようにする
- または使い方をドキュメント・ツール説明文に明記する

---

### 12. ツールのタイムアウトをパラメータで指定できるようにする

**要望**
- `lab_exec` や `kubectl_*` ツールに `timeout_seconds` パラメータを追加する
- 長時間かかる操作（ArgoCD sync 待機など）に対応できるようにする
- デフォルト: 30 秒、最大: 300 秒など

---

## 優先度まとめ

| # | 内容 | 優先度 | 難易度 |
|---|------|--------|--------|
| 2 | lab_exec ハング → MCP 全体フリーズ | **高** | 中 |
| 3 | kubectl_apply インライン YAML 非対応 | **高** | 低 |
| 6 | 不足 kubectl ツール (patch/delete/wait 等) | **高** | 低〜中 |
| 8 | ArgoCD 専用ツール | 中 | 中 |
| 10 | lab_exec の stdout/stderr 分離 | 中 | 低 |
| 7 | kubectl_get 大量出力・jq フィルタ | 中 | 低 |
| 12 | ツールのタイムアウトパラメータ | 中 | 低 |
| 1 | lab_exec SSH ユーザー設定 | 中 | 低 |
| 9 | Helm 操作ツール | 低 | 低 |
| 4 | SSH host key 警告ノイズ | 低 | 低 |
| 11 | kubectl_describe 引数仕様 | 低 | 低 |
| 5 | kubectl_apply パス解決 (#3 で解消) | - | - |
