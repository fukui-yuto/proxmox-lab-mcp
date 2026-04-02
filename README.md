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
    └── kubectl (kubeconfig)
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
vi .env  # Proxmox の接続情報を記入
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

### Phase 2: Terraform tools ✅

| ツール名 | 説明 | 破壊的 |
|---|---|---|
| `terraform_plan` | terraform plan 実行・差分表示 | ✗ |
| `terraform_state_list` | state 内リソース一覧 | ✗ |
| `terraform_state_show` | 特定リソースの state 詳細 | ✗ |
| `terraform_output` | output 値取得 | ✗ |
| `terraform_apply` | terraform apply 実行 | ✓ confirm 必須 |

### Phase 3: Ansible tools ✅

| ツール名 | 説明 | 破壊的 |
|---|---|---|
| `ansible_ping` | 全ホスト疎通確認 | ✗ |
| `ansible_list_inventory` | インベントリ構成確認 | ✗ |
| `ansible_run_playbook` | playbook 実行 | ✓ confirm 必須 |

### Phase 4: kubectl / Helm tools ✅

| ツール名 | 説明 |
|---|---|
| `kubectl_get` | kubectl get \<resource\> |
| `kubectl_describe` | kubectl describe \<resource\> \<name\> |
| `kubectl_logs` | Pod ログ取得 |
| `helm_list` | Helm リリース一覧 |
| `helm_get_values` | リリースの values 確認 |

## 安全設計

破壊的操作には `confirm: bool` パラメータを必須化：

```python
@mcp.tool()
def terraform_apply(confirm: bool = False) -> str:
    if not confirm:
        return "ERROR: confirm=true を明示してください"
    # 実行
```
