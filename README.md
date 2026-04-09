# proxmox-lab-mcp

Proxmox ホームラボ管理用 MCP サーバー。Raspberry Pi 5 (Ubuntu 24) 上で稼働し、Claude Code から HTTP/SSE で接続する。

## 構成

```
Claude Code (Windows)
    │  HTTP/SSE  http://192.168.210.55:8000/sse
    ▼
Raspberry Pi 5 (Ubuntu 24) ← MCP Server
    ├── proxmoxer  → Proxmox API (LAN)
    ├── terraform CLI (ネイティブ実行)
    ├── ansible CLI (ネイティブ実行)
    ├── kubectl (kubeconfig)
    └── ArgoCD REST API (http://argocd.homelab.local)
```

## セットアップ（Raspberry Pi 上）

### 1. uv のインストール

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

### 2. リポジトリの配置

```bash
git clone https://github.com/fukui-yuto/proxmox-lab-mcp.git ~/proxmox-lab-mcp
cd ~/proxmox-lab-mcp
```

### 3. 環境変数の設定

```bash
cp .env.example .env
vi .env  # 各サービスの接続情報を記入
```

必須の環境変数:

| 変数名 | 説明 |
|---|---|
| `PROXMOX_HOST` | Proxmox ホスト IP |
| `PROXMOX_USER` | Proxmox ユーザー (例: `root@pam`) |
| `PROXMOX_TOKEN_NAME` | API トークン名 |
| `PROXMOX_TOKEN_VALUE` | API トークン値 |
| `TERRAFORM_DIR` | terraform ディレクトリのパス |
| `ANSIBLE_DIR` | ansible ディレクトリのパス |
| `KUBECONFIG` | kubeconfig ファイルのパス |

ArgoCD ツールを使用する場合（任意）:

| 変数名 | 説明 |
|---|---|
| `ARGOCD_SERVER` | ArgoCD サーバー URL (例: `http://argocd.homelab.local`) |
| `ARGOCD_TOKEN` | ArgoCD API トークン（期限なし）|
| `ARGOCD_VERIFY_SSL` | SSL 検証 (`true`/`false`、デフォルト: `false`) |

**ArgoCD API トークンの取得方法:**

```bash
# admin アカウントに apiKey 権限を付与（初回のみ）
kubectl -n argocd patch configmap argocd-cm \
  -p '{"data": {"accounts.admin": "apiKey,login"}}'

# セッショントークンを取得してからAPIトークンを生成
SESSION=$(curl -sk -X POST https://<argocd-url>/api/v1/session \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<password>"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -sk -X POST https://<argocd-url>/api/v1/account/admin/token \
  -H "Authorization: Bearer $SESSION" \
  -H 'Content-Type: application/json' \
  -d '{"expiresIn": 0, "id": "mcp-token"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])"
```

また、Pi の `/etc/hosts` に ArgoCD のホスト名を追加しておく必要があります:

```bash
echo "192.168.210.21 argocd.homelab.local" >> /etc/hosts
```

### 4. 起動確認

```bash
uv run lab-mcp
# → http://0.0.0.0:8000/sse で起動
```

### 5. systemd サービス登録（常時起動）

```bash
sudo tee /etc/systemd/system/proxmox-lab-mcp.service > /dev/null <<EOF
[Unit]
Description=Proxmox Lab MCP Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/proxmox-lab-mcp
ExecStart=/root/.local/bin/uv run lab-mcp
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now proxmox-lab-mcp
sudo systemctl status proxmox-lab-mcp
```

## Proxmox API トークン作成

Proxmox Web UI → Datacenter → Permissions → API Tokens で作成:
- User: `root@pam`
- Token ID: `mcp-token`
- Privilege Separation: OFF（root 権限を継承）

## Claude Code への登録

```bash
claude mcp add --transport sse -s user proxmox-lab http://<pi-ip>:8000/sse
```

## 利用可能なツール

### Phase 1: Proxmox 読み取り系 ✅

| ツール名 | 説明 |
|---|---|
| `proxmox_list_nodes` | ノード一覧・CPU/メモリ/稼働状態 |
| `proxmox_list_vms` | 全ノードの VM/LXC 一覧 |
| `proxmox_get_vm_status` | 特定 VM の詳細状態 |
| `proxmox_get_node_resources` | ノードのリソース使用量 |
| `proxmox_list_storage` | ストレージプール一覧・使用量 |

### Proxmox 操作系 ✅

| ツール名 | 説明 | 破壊的 |
|---|---|---|
| `proxmox_start_vm` | VM / LXC 起動 | ✗ |
| `proxmox_stop_vm` | VM / LXC 停止 | ✓ confirm 必須 |
| `proxmox_reboot_vm` | VM / LXC 再起動 | ✓ confirm 必須 |
| `proxmox_list_snapshots` | スナップショット一覧 | ✗ |
| `proxmox_create_snapshot` | スナップショット作成 | ✗ |
| `proxmox_rollback_snapshot` | スナップショットへロールバック | ✓ confirm 必須 |
| `proxmox_list_tasks` | 直近タスク一覧 | ✗ |

### Proxmox 調査系 ✅

| ツール名 | 説明 |
|---|---|
| `proxmox_get_vm_config` | VM / LXC の設定詳細（CPU / メモリ / ディスク / ネットワーク） |
| `proxmox_get_task_log` | タスク UPID のログ取得（list_tasks で得た UPID を指定） |
| `proxmox_get_cluster_status` | クラスター全体の健全性ステータス |
| `proxmox_list_networks` | ノードのネットワーク設定一覧 |
| `proxmox_get_storage_content` | ストレージ内の ISO / テンプレート一覧 |
| `proxmox_get_replication_status` | ZFS レプリケーションジョブの状態（node01 ↔ node02 同期確認） |
| `proxmox_get_backup_jobs` | vzdump バックアップタスク履歴 |
| `proxmox_get_certificate_info` | TLS 証明書情報と残り有効日数 |

### Phase 2: Terraform tools ✅

| ツール名 | 説明 | 破壊的 |
|---|---|---|
| `terraform_plan` | terraform plan 実行・差分表示 | ✗ |
| `terraform_validate` | 構文検証のみ（apply なし） | ✗ |
| `terraform_state_list` | state 内リソース一覧 | ✗ |
| `terraform_state_show` | 特定リソースの state 詳細 | ✗ |
| `terraform_output` | output 値取得 | ✗ |
| `terraform_apply` | terraform apply 実行 | ✓ confirm 必須 |
| `terraform_destroy` | terraform destroy 実行 | ✓ confirm 必須 |

### Phase 3: Ansible tools ✅

| ツール名 | 説明 | 破壊的 |
|---|---|---|
| `ansible_ping` | 全ホスト疎通確認 | ✗ |
| `ansible_list_inventory` | インベントリ構成確認 | ✗ |
| `ansible_run_module` | アドホックモジュール実行（shell, setup 等） | ✗ |
| `ansible_get_facts` | ホストの facts 収集（OS / ハードウェア情報） | ✗ |
| `ansible_run_playbook` | playbook 実行 | ✓ confirm 必須 |

### Phase 4: kubectl / Helm tools ✅

| ツール名 | 説明 | 破壊的 |
|---|---|---|
| `kubectl_get` | kubectl get \<resource\>（label_selector / output / **jq_filter** 引数対応） | ✗ |
| `kubectl_describe` | kubectl describe \<resource\> \<name\> | ✗ |
| `kubectl_logs` | Pod ログ取得（--previous / container / since 引数対応） | ✗ |
| `kubectl_exec` | Pod 内コマンド実行（シェル調査・疎通確認等） | ✗ |
| `kubectl_get_events` | Namespace / Pod のイベント一覧（障害原因特定） | ✗ |
| `kubectl_get_secret` | Secret 内容確認（値はマスク表示） | ✗ |
| `kubectl_get_configmap` | ConfigMap 内容確認 | ✗ |
| `kubectl_run` | 一時 Pod でコマンド実行（Pod は自動削除） | ✗ |
| `kubectl_port_forward` | ローカルへのポートフォワード（バックグラウンド実行） | ✗ |
| `kubectl_apply` | マニフェスト apply（ファイルパス or **インライン YAML** 対応） | ✓ confirm 必須 |
| `kubectl_delete` | リソース削除 | ✓ confirm 必須 |
| `kubectl_patch` | リソース部分更新（merge / strategic / json パッチ対応） | ✗ |
| `kubectl_annotate` | アノテーション追加・更新 | ✗ |
| `kubectl_rollout_status` | Deployment ロールアウト状態確認 | ✗ |
| `kubectl_rollout_restart` | Deployment / StatefulSet / DaemonSet のローリングリスタート | ✗ |
| `kubectl_wait` | リソースが指定条件になるまで待機（condition / timeout 指定可） | ✗ |
| `kubectl_top` | Node / Pod リソース使用量 | ✗ |
| `helm_list` | Helm リリース一覧 | ✗ |
| `helm_get_values` | リリースの values 確認 | ✗ |
| `helm_show_values` | チャートのデフォルト values 確認（インストール前の設定確認に有用） | ✗ |
| `helm_upgrade` | リリースのアップグレード／インストール | ✓ confirm 必須 |
| `helm_uninstall` | リリースの削除 | ✓ confirm 必須 |

### Phase 5: ArgoCD tools ✅

環境変数 `ARGOCD_SERVER` / `ARGOCD_TOKEN` が必要。

| ツール名 | 説明 | 破壊的 |
|---|---|---|
| `argocd_list_apps` | 全アプリの一覧と sync/health 状態 | ✗ |
| `argocd_get_app` | アプリ詳細（リソース一覧・条件付き状態） | ✗ |
| `argocd_sync` | アプリの sync 実行（revision / prune / dry_run 対応） | ✓ |
| `argocd_refresh` | hard refresh トリガー（Git から再取得） | ✗ |

### Lab ユーティリティ ✅

| ツール名 | 説明 |
|---|---|
| `lab_ping` | Raspberry Pi から疎通確認 |
| `lab_wakeup` | Wake-on-LAN でホスト起動 |
| `lab_exec` | SSH 経由で VM / ホスト上のコマンドを直接実行（**timeout_seconds** 対応、stdout/stderr 分離出力） |
| `lab_check_port` | ポート開閉・疎通の確認 |
| `lab_dns_lookup` | DNS 名前解決（Pi-hole 経由確認等） |
| `lab_cluster_health` | ラボ全体の健全性サマリー（Proxmox + K8s ノード + 異常 Pod 一括確認） |

## 安全設計

破壊的操作には `confirm: bool` パラメータを必須化：

```python
@mcp.tool()
def terraform_apply(confirm: bool = False) -> str:
    if not confirm:
        return "ERROR: confirm=true を明示してください"
    # 実行
```
