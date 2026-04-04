# proxmox-lab-mcp アーキテクチャ解説

MCP (Model Context Protocol) の学習用に、このリポジトリのコードロジックと全体フローを詳細に解説します。

---

## 目次

1. [MCP とは何か](#1-mcp-とは何か)
2. [このプロジェクトの全体像](#2-このプロジェクトの全体像)
3. [ディレクトリ構成](#3-ディレクトリ構成)
4. [全体フロー図](#4-全体フロー図)
5. [各ファイルの詳細解説](#5-各ファイルの詳細解説)
   - [pyproject.toml](#51-pyprojecttoml--依存関係とエントリポイント)
   - [config.py](#52-configpy--設定層)
   - [tools/proxmox.py](#53-toolsproxmoxpy--proxmox-api-クライアント)
   - [tools/kubectl.py](#54-toolskubectlpy--kubernetes-操作)
   - [tools/ansible.py](#55-toolsansiblepy--ansible-操作)
   - [tools/terraform.py](#56-toolsterraformpy--terraform-操作)
   - [tools/lab.py](#57-toolslabpy--ラボユーティリティ)
   - [server.py](#58-serverpy--mcp-公開層)
6. [MCP ツール登録の仕組み](#6-mcp-ツール登録の仕組み)
7. [安全設計：confirm ガード](#7-安全設計confirm-ガード)
8. [2種類のバックエンド実装パターン](#8-2種類のバックエンド実装パターン)
9. [起動から応答までの完全フロー](#9-起動から応答までの完全フロー)
10. [ツール一覧と対応関数](#10-ツール一覧と対応関数)

---

## 1. MCP とは何か

MCP (Model Context Protocol) は、AI (Claude など) が外部ツール・システムを呼び出すための標準プロトコルです。

```
┌─────────────┐   MCP プロトコル   ┌──────────────────┐
│   Claude    │ ◄────────────────► │   MCP サーバー   │
│   (AI)      │   (JSON-RPC風)     │  (このプロジェクト) │
└─────────────┘                   └──────────────────┘
                                          │
                               ┌──────────┼──────────┐
                               ▼          ▼          ▼
                           Proxmox    kubectl    Ansible
```

MCP サーバーは「どんなツールが使えるか」をAIに教え、AIがツールを呼ぶと実際の処理を実行して結果を返します。

---

## 2. このプロジェクトの全体像

自宅ラボ環境（Proxmox + Kubernetes + Ansible + Terraform）を Claude が操作できるようにする MCP サーバーです。

- Claude が「VM の一覧を見せて」と言うと → `proxmox_list_vms` ツールが呼ばれる
- Claude が「nginx の Pod を確認して」と言うと → `kubectl_get` ツールが呼ばれる
- Claude が「site.yml を実行して」と言うと → `ansible_run_playbook` ツールが呼ばれる

---

## 3. ディレクトリ構成

```
proxmox-lab-mcp/
├── pyproject.toml              # パッケージ定義・依存関係・エントリポイント
├── .env.example                # 環境変数のテンプレート
└── src/
    └── lab_mcp/
        ├── __init__.py         # パッケージ初期化（空）
        ├── config.py           # 環境変数の読み込みと共有
        ├── server.py           # MCPツール定義（唯一の公開レイヤー）
        └── tools/
            ├── __init__.py     # ツールパッケージ初期化（空）
            ├── proxmox.py      # Proxmox API ラッパー
            ├── kubectl.py      # kubectl / helm コマンドラッパー
            ├── ansible.py      # ansible コマンドラッパー
            ├── terraform.py    # terraform コマンドラッパー
            └── lab.py          # ping / SSH / WoL / DNS ユーティリティ
```

**設計の大原則：「ツール定義」と「実装」を分離する**

- `server.py` → MCPに何を公開するかだけを定義
- `tools/*.py` → 実際の処理ロジックだけを担当

---

## 4. 全体フロー図

```
                        ┌─────────────────────────────────────────┐
                        │            server.py                    │
                        │  @mcp.tool() で登録されたツール群        │
                        │                                         │
  Claude ──MCP──►  tool: proxmox_list_vms()  ──────────────────► │
                   tool: kubectl_get()                            │
                   tool: ansible_ping()       ...etc              │
                        └──────┬──────────────────────────────────┘
                               │ 各ツールが対応モジュールを呼び出す
                    ┌──────────┼───────────────────────────────┐
                    ▼          ▼          ▼          ▼          ▼
             proxmox.py  kubectl.py  ansible.py  terraform.py  lab.py
                    │          │          │          │          │
                    ▼          ▼          ▼          ▼          ▼
             proxmoxer   subprocess   subprocess  subprocess  subprocess
             (REST API)  (kubectl)    (ansible)   (terraform) (ping/ssh)
                    │
                    ▼
             Proxmox API
             (HTTPS/REST)
```

---

## 5. 各ファイルの詳細解説

### 5.1 `pyproject.toml` — 依存関係とエントリポイント

```toml
[project]
name = "proxmox-lab-mcp"
dependencies = [
    "mcp[cli]>=1.0.0",        # MCPフレームワーク本体（FastMCP を含む）
    "proxmoxer>=2.0.0",        # Proxmox REST API の Python クライアント
    "requests>=2.31.0",        # proxmoxer の HTTP バックエンド
    "python-dotenv>=1.0.0",    # .env ファイルの読み込み
]

[project.scripts]
lab-mcp = "lab_mcp.server:main"   # `lab-mcp` コマンドで server.py の main() を実行
```

`lab-mcp` コマンドを実行すると `server.py` の `main()` が呼ばれ、MCPサーバーが起動します。

---

### 5.2 `config.py` — 設定層

```python
from dotenv import load_dotenv
load_dotenv()  # .env ファイルを読み込む

def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"環境変数 {key} が未設定です")  # 起動時に即エラー
    return value

# 必須変数（未設定なら起動失敗）
PROXMOX_HOST        = _require("PROXMOX_HOST")
PROXMOX_USER        = _require("PROXMOX_USER")
PROXMOX_TOKEN_NAME  = _require("PROXMOX_TOKEN_NAME")
PROXMOX_TOKEN_VALUE = _require("PROXMOX_TOKEN_VALUE")

# 任意変数（デフォルト値あり）
PROXMOX_VERIFY_SSL = os.getenv("PROXMOX_VERIFY_SSL", "false").lower() == "true"
TERRAFORM_DIR      = os.getenv("TERRAFORM_DIR", "")
ANSIBLE_DIR        = os.getenv("ANSIBLE_DIR", "")
KUBECONFIG         = os.getenv("KUBECONFIG", "~/.kube/config")
SSH_USER           = os.getenv("SSH_USER", "")
SSH_KEY            = os.getenv("SSH_KEY", "")
MCP_HOST           = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT           = int(os.getenv("MCP_PORT", "8000"))
```

**ポイント：**
- `_require()` により Proxmox の認証情報が未設定なら起動時に即エラーになる（実行中に失敗するより早期検出が安全）
- すべての `tools/*.py` は `from lab_mcp import config` でこのモジュールを参照し、設定値を共有する

---

### 5.3 `tools/proxmox.py` — Proxmox API クライアント

**他のツールと異なる点：CLIコマンドでなく REST API を直接叩く**

```python
from proxmoxer import ProxmoxAPI

def _client() -> ProxmoxAPI:
    """毎回新しい API クライアントを生成する。"""
    return ProxmoxAPI(
        config.PROXMOX_HOST,
        user=config.PROXMOX_USER,
        token_name=config.PROXMOX_TOKEN_NAME,   # APIトークン認証
        token_value=config.PROXMOX_TOKEN_VALUE,
        verify_ssl=config.PROXMOX_VERIFY_SSL,
    )
```

`_client()` は呼ばれるたびに新しい接続を作ります（コネクションプーリングなし）。シンプルさを優先した設計です。

**proxmoxer の API 構造：**

proxmoxer は Proxmox の REST API パス構造をそのまま Python のメソッドチェーンに変換します。

```python
# REST API: GET /nodes/{node}/qemu/{vmid}/status/current
pve.nodes(node).qemu(vmid).status.current.get()

# REST API: POST /nodes/{node}/qemu/{vmid}/snapshot
pve.nodes(node).qemu(vmid).snapshot.post(snapname="snap1")

# REST API: POST /nodes/{node}/lxc/{vmid}/status/start
pve.nodes(node).lxc(vmid).status.start.post()
```

パスのセグメントが引数を取る場合は `nodes(node)` のように関数呼び出し、取らない場合は `.status` のようにプロパティアクセスになります。

**主な関数：**

| 関数 | 内部で呼ぶ API | 説明 |
|------|--------------|------|
| `list_nodes()` | `pve.nodes.get()` | ノード一覧を取得し CPU/メモリをGB換算 |
| `list_vms()` | `pve.nodes(n).qemu.get()` + `.lxc.get()` | 全ノードの QEMU VM と LXC コンテナを列挙 |
| `get_vm_status()` | `.status.current.get()` | 特定VMのリアルタイムステータス |
| `start_vm()` | `.status.start.post()` | VM起動（POST = 状態変更） |
| `create_snapshot()` | `.snapshot.post()` | スナップショット作成 |
| `get_certificate_info()` | `.certificates.info.get()` | TLS証明書の残り日数を計算して返す |

---

### 5.4 `tools/kubectl.py` — Kubernetes 操作

**設計パターン：`_run()` ヘルパーで subprocess を共通化**

```python
def _run(args: list[str]) -> str:
    env = {"KUBECONFIG": config.KUBECONFIG}   # kubeconfig のパスを注入
    result = subprocess.run(
        args,
        capture_output=True,   # stdout/stderr を変数に格納（ターミナルに出力しない）
        text=True,             # bytes ではなく str で受け取る
        env={**os.environ, **env},  # 既存の環境変数を維持しつつ KUBECONFIG を上書き
    )
    return (result.stdout + result.stderr).strip()  # 両方合わせて返す
```

`_run()` を通すことで、すべての関数が同じ方法でコマンドを実行し、同じ形式で結果を返します。

**特徴的な関数：**

```python
# Secret の値をマスクする
def get_secret(name, namespace):
    result = _run(["kubectl", "get", "secret", name, "-o", "json"])
    data = json.loads(result)
    data["data"] = {k: "***" for k in data["data"]}  # 全キーの値を *** に置換
    return json.dumps(data, indent=2)

# 一時 Pod の自動削除
def run_pod(image, command, namespace):
    pod_name = f"debug-{int(time.time())}"  # タイムスタンプでユニークな名前
    args = ["kubectl", "run", pod_name, ..., "--rm", "--attach", "--"] + shlex.split(command)
    # --rm: 実行後に Pod を自動削除
    # --attach: コマンドの出力をリアルタイムに受け取る

# port-forward だけは subprocess.Popen（バックグラウンド実行）
def port_forward(resource, ports, namespace):
    proc = subprocess.Popen(...)    # run() ではなく Popen = 非ブロッキング
    return f"PID: {proc.pid} ..."  # PID を返してユーザーが kill できるようにする
```

`port_forward` だけが `Popen`（バックグラウンド実行）を使う理由：`subprocess.run()` はプロセスが終了するまでブロックするため、ポートフォワードのような長時間プロセスには使えないからです。

---

### 5.5 `tools/ansible.py` — Ansible 操作

```python
def _run(args: list[str]) -> str:
    result = subprocess.run(
        args,
        cwd=config.ANSIBLE_DIR,   # ANSIBLE_DIR をカレントディレクトリとして実行
        capture_output=True,
        text=True,
    )
    return (result.stdout + result.stderr).strip()
```

kubectl と同じパターンですが、`cwd=config.ANSIBLE_DIR` で実行ディレクトリを固定しています。インベントリファイルへの相対パス（`inventory/hosts.yml`）がこのディレクトリを基準に解決されます。

```python
def ping(hosts="all"):
    return _run(["ansible", "-i", "inventory/hosts.yml", hosts, "-m", "ping"])

def run_module(hosts, module, args=""):
    cmd = ["ansible", "-i", "inventory/hosts.yml", hosts, "-m", module]
    if args:
        cmd += ["-a", args]   # モジュール引数は -a で渡す
    return _run(cmd)
```

---

### 5.6 `tools/terraform.py` — Terraform 操作

```python
def _run(args: list[str], cwd=None) -> str:
    result = subprocess.run(
        ["terraform"] + args,       # 先頭に "terraform" を自動付与
        cwd=cwd or config.TERRAFORM_DIR,
        capture_output=True,
        text=True,
    )
    return (result.stdout + result.stderr).strip()

def plan():
    return _run(["plan", "-no-color"])   # -no-color: ANSIエスケープを除去してテキストをクリーンに

def apply():
    return _run(["apply", "-auto-approve", "-no-color"])  # -auto-approve: 確認プロンプトをスキップ
```

`-auto-approve` により Terraform が対話的に確認を求めなくなります。代わりに `server.py` 側の `confirm=True` ガードで安全性を担保しています。

---

### 5.7 `tools/lab.py` — ラボユーティリティ

汎用的なネットワーク・SSH 操作をまとめたモジュールです。

```python
# Wake-on-LAN の仕組み
def wakeup(mac, broadcast):
    mac_bytes = bytes.fromhex(mac.replace(":", ""))  # AA:BB:CC → bytes
    magic = b"\xff" * 6 + mac_bytes * 16             # Magic Packet の構造
    #   └── 6バイトの 0xFF ──┘  └── MACアドレス16回繰り返し ──┘

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # ブロードキャスト有効化
    sock.sendto(magic, (broadcast, 9))  # UDP ポート 9 に送信

# SSH コマンド実行
def exec(host, command, user="", ssh_key=""):
    _user = user or config.SSH_USER   # 引数 → 環境変数の優先順位
    _key  = ssh_key or config.SSH_KEY

    args = ["ssh",
            "-o", "StrictHostKeyChecking=no",  # ホスト鍵確認をスキップ（ラボ環境向け）
            "-o", "BatchMode=yes",              # パスワード入力プロンプトを出さない
            target, command]

# TCP ポート疎通確認
def check_port(host, port, timeout=3.0):
    with socket.create_connection((host, port), timeout=timeout):
        return f"{host}:{port} は開いています"
    # 接続できれば OPEN、例外なら CLOSED/TIMEOUT
```

---

### 5.8 `server.py` — MCP 公開層

このファイルが MCP サーバーの心臓部です。

**FastMCP の初期化：**

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("proxmox-lab", host=config.MCP_HOST, port=config.MCP_PORT)
```

`FastMCP` はMCPフレームワークが提供するサーバークラスです。名前 (`"proxmox-lab"`) はClaude側で表示されるサーバー名になります。

**ツールの登録：**

```python
@mcp.tool()                      # ← このデコレータが関数をMCPツールとして登録する
def proxmox_list_nodes() -> str:
    """Proxmox クラスタのノード一覧と CPU / メモリ / 稼働状態を返す。"""
    # ↑ この docstring が Claude に「このツールは何をするか」を伝える説明文になる
    return json.dumps(proxmox.list_nodes(), ensure_ascii=False, indent=2)
```

`@mcp.tool()` デコレータを付けるだけで：
1. 関数名がツール名になる（`proxmox_list_nodes`）
2. docstring がツールの説明になる
3. 引数と型ヒントがツールのパラメータスキーマになる
4. 戻り値（文字列）がClaude に返るレスポンスになる

**エントリポイント：**

```python
def main() -> None:
    mcp.run(transport="sse")   # SSE (Server-Sent Events) トランスポートで起動
```

`transport="sse"` は HTTP + SSE でサーバーを公開します。Claude の MCP 設定に `http://localhost:8000/sse` を登録することで接続できます。

---

## 6. MCP ツール登録の仕組み

`@mcp.tool()` デコレータの動作を詳しく見てみましょう。

```python
@mcp.tool()
def proxmox_get_vm_status(node: str, vmid: int, vm_type: str = "qemu") -> str:
    """特定の VM / LXC の詳細ステータスを返す。

    Args:
        node: ノード名 (例: pve1)
        vmid: VM ID (例: 100)
        vm_type: "qemu" または "lxc"
    """
    return json.dumps(proxmox.get_vm_status(node, vmid, vm_type), ...)
```

FastMCP はこれを以下のMCPツールスキーマとして自動生成します：

```json
{
  "name": "proxmox_get_vm_status",
  "description": "特定の VM / LXC の詳細ステータスを返す。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "node":    { "type": "string", "description": "ノード名 (例: pve1)" },
      "vmid":    { "type": "integer", "description": "VM ID (例: 100)" },
      "vm_type": { "type": "string", "default": "qemu", "description": "\"qemu\" または \"lxc\"" }
    },
    "required": ["node", "vmid"]
  }
}
```

Claude はこのスキーマを受け取り、「どんな引数でこのツールを呼べばよいか」を理解します。

---

## 7. 安全設計：confirm ガード

破壊的操作（VM停止・削除・デプロイ等）には `confirm: bool = False` パラメータが付いています。

```python
@mcp.tool()
def proxmox_stop_vm(node: str, vmid: int, vm_type: str = "qemu", confirm: bool = False) -> str:
    """VM / LXC を停止する。破壊的操作のため confirm=true が必須。"""
    if not confirm:                                             # ① デフォルトは False
        return "ERROR: 破壊的操作です。confirm=true を明示してください。"  # ② エラー文字列を返す
    return proxmox.stop_vm(node, vmid, vm_type)                # ③ True の時だけ実行
```

**なぜ例外でなく文字列を返すのか：**
- MCP ツールの戻り値はすべて文字列として Claude に返ります
- エラーメッセージをテキストで返すことで Claude がその内容を理解し、ユーザーに伝えられます
- 例外だとエラーメッセージが構造化されすぎてClaudeが処理しにくい場合があります

**confirm ガードが付いている操作：**

| 操作 | ツール名 |
|------|---------|
| VM 停止 | `proxmox_stop_vm` |
| VM 再起動 | `proxmox_reboot_vm` |
| スナップショットロールバック | `proxmox_rollback_snapshot` |
| Playbook 実行 | `ansible_run_playbook` |
| `kubectl apply` | `kubectl_apply` |
| `kubectl delete` | `kubectl_delete` |
| `helm upgrade` | `helm_upgrade` |
| `helm uninstall` | `helm_uninstall` |
| `terraform apply` | `terraform_apply` |
| `terraform destroy` | `terraform_destroy` |

---

## 8. 2種類のバックエンド実装パターン

このプロジェクトでは、バックエンドへのアクセス方法が2パターンあります。

### パターン A：REST API（proxmox.py）

```python
# proxmoxer ライブラリ経由で HTTP REST API を直接叩く
pve = ProxmoxAPI(host, user=..., token_name=..., token_value=...)
result = pve.nodes(node).qemu(vmid).status.current.get()
```

- **メリット**：構造化されたデータ（dict）をそのまま受け取れる、型が明確
- **デメリット**：ライブラリへの依存、APIの変更に追随が必要

### パターン B：subprocess（kubectl/ansible/terraform/lab）

```python
# CLI ツールをサブプロセスとして起動してテキスト出力を受け取る
result = subprocess.run(["kubectl", "get", "pods", "-o", "wide"], capture_output=True, text=True)
return result.stdout + result.stderr
```

- **メリット**：CLIと全く同じ動作、ツールのバージョンに左右されにくい
- **デメリット**：テキスト解析が必要、CLIが PATH にある必要がある

---

## 9. 起動から応答までの完全フロー

### サーバー起動時

```
1. `lab-mcp` コマンド実行
         ↓
2. server.py の main() が呼ばれる
         ↓
3. config.py が import される
   → load_dotenv() で .env を読み込む
   → _require() で必須変数をチェック（未設定なら即 RuntimeError）
         ↓
4. @mcp.tool() デコレータが全ツールを FastMCP に登録
         ↓
5. mcp.run(transport="sse")
   → 0.0.0.0:8000 で SSE サーバーが起動
   → Claude からの接続を待機
```

### Claude がツールを呼び出す時

```
1. Claude が「VMの一覧を見せて」と判断
         ↓
2. MCP プロトコルで tools/call リクエスト送信
   { "name": "proxmox_list_vms", "arguments": {} }
         ↓
3. server.py の proxmox_list_vms() が実行される
         ↓
4. proxmox.list_vms() を呼び出す
         ↓
5. _client() で ProxmoxAPI インスタンスを生成
         ↓
6. pve.nodes.get() → Proxmox REST API へ HTTP GET
         ↓
7. 各ノードで pve.nodes(n).qemu.get() と .lxc.get() を実行
         ↓
8. 結果を dict に整形（CPU/メモリを人間が読みやすい単位に変換）
         ↓
9. json.dumps() で JSON 文字列に変換
         ↓
10. MCP レスポンスとして Claude に返却
          ↓
11. Claude が JSON を解釈してユーザーに自然言語で説明
```

---

## 10. ツール一覧と対応関数

### Proxmox（読み取り系）

| MCPツール名 | tools/proxmox.py の関数 | 説明 |
|------------|------------------------|------|
| `proxmox_list_nodes` | `list_nodes()` | ノード一覧と CPU/メモリ |
| `proxmox_list_vms` | `list_vms()` | 全VM/LXC一覧 |
| `proxmox_get_vm_status` | `get_vm_status()` | 特定VMの詳細ステータス |
| `proxmox_get_vm_config` | `get_vm_config()` | VMの設定詳細 |
| `proxmox_get_node_resources` | `get_node_resources()` | ノードのリソース使用量 |
| `proxmox_list_storage` | `list_storage()` | ストレージ使用量 |
| `proxmox_list_snapshots` | `list_snapshots()` | スナップショット一覧 |
| `proxmox_list_tasks` | `list_tasks()` | 直近タスク一覧 |
| `proxmox_get_task_log` | `get_task_log()` | タスクの実行ログ |
| `proxmox_get_cluster_status` | `get_cluster_status()` | クラスター健全性 |
| `proxmox_list_networks` | `list_networks()` | ネットワーク設定 |
| `proxmox_get_replication_status` | `get_replication_status()` | ZFSレプリケーション状態 |
| `proxmox_get_backup_jobs` | `get_backup_jobs()` | バックアップ履歴 |
| `proxmox_get_certificate_info` | `get_certificate_info()` | TLS証明書の残り日数 |
| `proxmox_get_storage_content` | `get_storage_content()` | ストレージ内コンテンツ |

### Proxmox（操作系・confirm 必須）

| MCPツール名 | tools/proxmox.py の関数 | 説明 |
|------------|------------------------|------|
| `proxmox_start_vm` | `start_vm()` | VM起動 |
| `proxmox_stop_vm` | `stop_vm()` | VM停止 ⚠ |
| `proxmox_reboot_vm` | `reboot_vm()` | VM再起動 ⚠ |
| `proxmox_create_snapshot` | `create_snapshot()` | スナップショット作成 |
| `proxmox_rollback_snapshot` | `rollback_snapshot()` | ロールバック ⚠ |

### Kubernetes / Helm

| MCPツール名 | tools/kubectl.py の関数 | 説明 |
|------------|------------------------|------|
| `kubectl_get` | `get()` | リソース一覧 |
| `kubectl_describe` | `describe()` | リソース詳細 |
| `kubectl_logs` | `logs()` | Podのログ |
| `kubectl_exec` | `exec()` | Pod内コマンド実行 |
| `kubectl_get_events` | `get_events()` | イベント一覧 |
| `kubectl_get_secret` | `get_secret()` | Secret（値マスク済み）|
| `kubectl_get_configmap` | `get_configmap()` | ConfigMap |
| `kubectl_top` | `top()` | リソース使用量 |
| `kubectl_rollout_status` | `rollout_status()` | ロールアウト状態 |
| `kubectl_run` | `run_pod()` | 一時Pod実行（自動削除）|
| `kubectl_port_forward` | `port_forward()` | ポートフォワード |
| `helm_list` | `helm_list()` | Helmリリース一覧 |
| `helm_get_values` | `helm_get_values()` | Helm values |
| `kubectl_apply` | `apply()` | マニフェスト適用 ⚠ |
| `kubectl_delete` | `delete()` | リソース削除 ⚠ |
| `helm_upgrade` | `helm_upgrade()` | Helmアップグレード ⚠ |
| `helm_uninstall` | `helm_uninstall()` | Helmアンインストール ⚠ |

### Ansible

| MCPツール名 | tools/ansible.py の関数 | 説明 |
|------------|------------------------|------|
| `ansible_ping` | `ping()` | 疎通確認 |
| `ansible_list_inventory` | `list_inventory()` | インベントリ構成 |
| `ansible_run_module` | `run_module()` | アドホックモジュール |
| `ansible_get_facts` | `get_facts()` | ホストのfacts収集 |
| `ansible_run_playbook` | `run_playbook()` | Playbook実行 ⚠ |

### Terraform

| MCPツール名 | tools/terraform.py の関数 | 説明 |
|------------|--------------------------|------|
| `terraform_plan` | `plan()` | 差分確認 |
| `terraform_validate` | `validate()` | 構文検証 |
| `terraform_state_list` | `state_list()` | 管理リソース一覧 |
| `terraform_state_show` | `state_show()` | リソース詳細 |
| `terraform_output` | `output()` | Output値 |
| `terraform_apply` | `apply()` | インフラ適用 ⚠ |
| `terraform_destroy` | `destroy()` | インフラ削除 ⚠ |

### Lab ユーティリティ

| MCPツール名 | tools/lab.py の関数 | 説明 |
|------------|---------------------|------|
| `lab_ping` | `ping()` | ICMPで疎通確認 |
| `lab_wakeup` | `wakeup()` | Wake-on-LAN |
| `lab_exec` | `exec()` | SSH経由コマンド実行 |
| `lab_check_port` | `check_port()` | TCPポート開閉確認 |
| `lab_dns_lookup` | `dns_lookup()` | DNS名前解決 |
| `lab_cluster_health` | (server.py内で実装) | ラボ全体の健全性サマリー |

> ⚠ = `confirm=True` が必要な破壊的操作
