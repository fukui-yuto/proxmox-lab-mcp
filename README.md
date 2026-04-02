# proxmox-lab-mcp

Proxmox ホームラボ管理用 MCP サーバー。Raspberry Pi 上で稼働し、Claude Code から HTTP/SSE で接続する。

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

### 4. 依存パッケージのインストールと起動確認

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
```

## Proxmox API トークン作成

Proxmox Web UI → Datacenter → Permissions → API Tokens で作成:
- User: `root@pam`
- Token ID: `mcp-token`
- Privilege Separation: OFF（root 権限を継承）

## Claude Code への登録

`~/.claude/settings.json` に追記：

```json
{
  "mcpServers": {
    "proxmox-lab": {
      "type": "sse",
      "url": "http://<pi-ip>:8000/sse"
    }
  }
}
```

## 実装フェーズ

| フェーズ | スコープ | 状態 |
|---|---|---|
| Phase 1 | Proxmox 読み取り系 | ✅ 実装済み |
| Phase 2 | Terraform plan / state | 未実装 |
| Phase 3 | Ansible ping / inventory | 未実装 |
| Phase 4 | 破壊的操作 (apply/playbook) | 未実装 |
