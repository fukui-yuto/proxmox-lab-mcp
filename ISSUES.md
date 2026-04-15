# Issues / 改善要望

---

## Issue 1: `git_pull` MCP ツールの追加 【優先度: 高】

### 問題
Windows でコードを編集して `git push` した後、Raspberry Pi の Terraform 実行環境に変更が届かない。
`terraform_plan` / `terraform_apply` は `TERRAFORM_DIR` (Raspberry Pi 上の git リポジトリ) をそのまま参照するため、
**git pull を手動で行わないと最新の変更が反映されない**。

MCP には現在 git 操作のツールがなく、`lab_exec` の SSH も通常の認証設定では Raspberry Pi 自身への接続が難しい。

### 対象ファイル
- `src/lab_mcp/tools/terraform.py` — `git_pull()` 関数を追加
- `src/lab_mcp/server.py` — `git_pull` ツールを登録

### 修正方針

**`src/lab_mcp/tools/terraform.py`** に追加:
```python
def git_pull() -> str:
    """git pull で TERRAFORM_DIR のリポジトリを最新化する。"""
    import os
    # TERRAFORM_DIR の親 = git リポジトリルート
    repo_dir = str(Path(config.TERRAFORM_DIR).parent)
    result = subprocess.run(
        ["git", "pull", "origin", "main"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    return (result.stdout + result.stderr).strip()
```

**`src/lab_mcp/server.py`** に追加:
```python
@mcp.tool()
def git_pull() -> str:
    """git pull でリポジトリを最新化する。
    Windows での編集を terraform_plan/apply に反映するために使用する。
    """
    return terraform.git_pull()
```

---

## Issue 2: `ansible_run_module` で `shell` モジュールの stdout が欠落する 【優先度: 中】

### 問題
`ansible_run_module` で `module="shell"` を使うと、コマンドの出力が MCP のレスポンスに含まれない。

Ansible の一行出力フォーマットは以下の形式:
```
hostname | CHANGED | rc=0 >>
<shell コマンドの stdout>
```
しかし `git pull` のような**コマンドが stdout ではなく stderr に出力**する場合、`>>` の後が空になる。
Ansible はシェルコマンドの stdout のみを一行フォーマットの `>>` 後に表示し、stderr は通常出力しないため。

### 実際に見た症状
```
rasberrypi5 | CHANGED | rc=0 >>
```
← git pull の結果が表示されない

### 対象ファイル
- `src/lab_mcp/tools/ansible.py` — `run_module()` を修正

### 修正方針

`shell` モジュール使用時は `-v` (verbose) フラグを追加し、stderr も含めた詳細出力を得る:

```python
def run_module(hosts: str, module: str, args: str = "") -> str:
    cmd = ["ansible", "-i", "inventory/hosts.yml", hosts, "-m", module]
    if args:
        cmd += ["-a", args]
    if module == "shell":
        cmd += ["-v"]  # stderr も出力に含める
    return _run(cmd)
```

---

## Issue 3: `lab_exec` の SSH_USER デフォルトが空で接続失敗しやすい 【優先度: 低】

### 問題
`config.py:24` で `SSH_USER = os.getenv("SSH_USER", "")` と定義されており、
`.env` に `SSH_USER` を設定しない場合はユーザーなしの `ssh host` コマンドになる。
Linux の SSH クライアントはその場合、**実行ユーザー名 (root)** でログインを試みるが、
VM への SSH は `ubuntu` ユーザーが必要なため失敗する。

```
# lab_exec で user 引数を省略 + SSH_USER 未設定の場合
ssh -o ... 192.168.210.29 "df -h"   # root でログイン試みてエラー
```

### 対象ファイル
- `src/lab_mcp/config.py`
- `.env.example`

### 修正方針

`.env.example` に明示的なコメントを追記して、設定忘れを防ぐ:
```env
# k3s VM / Raspberry Pi への SSH ユーザー
# VM は ubuntu、Proxmox ホストは root
SSH_USER=ubuntu
SSH_KEY=/root/.ssh/id_ed25519
```

また `lab_exec` のツール説明文にも `user` 引数の必要性を強調する:
```python
# server.py の lab_exec ツール説明に追記
"""SSH 経由で VM / ホスト上のコマンドを直接実行する。
VM (k3s worker 等) には user="ubuntu"、Proxmox ホストには user="root" を指定する。
"""
```

---

## Issue 4: `terraform_plan` / `terraform_apply` の説明文に git pull 必須を明記 【優先度: 低】

### 問題
Windows での編集後に `terraform_plan` を実行しても変更が反映されないが、
ツールの説明文に git pull が必要であることが記載されていない。

### 対象ファイル
- `src/lab_mcp/server.py`

### 修正方針

```python
@mcp.tool()
def terraform_plan() -> str:
    """terraform plan を実行して差分を返す。TERRAFORM_DIR で実行される。
    Windows で main.tf を編集した場合は先に git_pull を実行すること。
    """
    return terraform.plan()
```

```python
@mcp.tool()
def terraform_apply(confirm: bool = False) -> str:
    """terraform apply を実行する。破壊的操作のため confirm=true が必須。
    実行前に git_pull で最新コードを取得していることを確認すること。

    Args:
        confirm: true を明示しないと実行されない
    """
```
