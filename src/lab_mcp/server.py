import json
from mcp.server.fastmcp import FastMCP
from lab_mcp import config
from lab_mcp.tools import proxmox, terraform, ansible, kubectl, lab, argocd

mcp = FastMCP("proxmox-lab", host=config.MCP_HOST, port=config.MCP_PORT)


# ── Proxmox ──────────────────────────────────────────────────────────────────

@mcp.tool()
def proxmox_list_nodes() -> str:
    """Proxmox クラスタのノード一覧と CPU / メモリ / 稼働状態を返す。"""
    return json.dumps(proxmox.list_nodes(), ensure_ascii=False, indent=2)


@mcp.tool()
def proxmox_list_vms() -> str:
    """全ノードの VM / LXC 一覧（vmid, 名前, 状態, スペック）を返す。"""
    return json.dumps(proxmox.list_vms(), ensure_ascii=False, indent=2)


@mcp.tool()
def proxmox_get_vm_status(node: str, vmid: int, vm_type: str = "qemu") -> str:
    """特定の VM / LXC の詳細ステータスを返す。

    Args:
        node: ノード名 (例: pve1)
        vmid: VM ID (例: 100)
        vm_type: "qemu" または "lxc"
    """
    return json.dumps(proxmox.get_vm_status(node, vmid, vm_type), ensure_ascii=False, indent=2)


@mcp.tool()
def proxmox_get_node_resources(node: str) -> str:
    """指定ノードの CPU / メモリ / スワップ使用量を返す。

    Args:
        node: ノード名 (例: pve1)
    """
    return json.dumps(proxmox.get_node_resources(node), ensure_ascii=False, indent=2)


@mcp.tool()
def proxmox_list_storage() -> str:
    """全ノードのストレージプール一覧と使用量を返す。"""
    return json.dumps(proxmox.list_storage(), ensure_ascii=False, indent=2)


# ── Proxmox 操作系 ───────────────────────────────────────────────────────────

@mcp.tool()
def proxmox_start_vm(node: str, vmid: int, vm_type: str = "qemu") -> str:
    """VM / LXC を起動する。

    Args:
        node: ノード名 (例: pve-node01)
        vmid: VM ID
        vm_type: "qemu" または "lxc"
    """
    return proxmox.start_vm(node, vmid, vm_type)


@mcp.tool()
def proxmox_stop_vm(node: str, vmid: int, vm_type: str = "qemu", confirm: bool = False) -> str:
    """VM / LXC を停止する。破壊的操作のため confirm=true が必須。

    Args:
        node: ノード名
        vmid: VM ID
        vm_type: "qemu" または "lxc"
        confirm: true を明示しないと実行されない
    """
    if not confirm:
        return "ERROR: 破壊的操作です。confirm=true を明示してください。"
    return proxmox.stop_vm(node, vmid, vm_type)


@mcp.tool()
def proxmox_reboot_vm(node: str, vmid: int, vm_type: str = "qemu", confirm: bool = False) -> str:
    """VM / LXC を再起動する。破壊的操作のため confirm=true が必須。

    Args:
        node: ノード名
        vmid: VM ID
        vm_type: "qemu" または "lxc"
        confirm: true を明示しないと実行されない
    """
    if not confirm:
        return "ERROR: 破壊的操作です。confirm=true を明示してください。"
    return proxmox.reboot_vm(node, vmid, vm_type)


@mcp.tool()
def proxmox_list_snapshots(node: str, vmid: int, vm_type: str = "qemu") -> str:
    """VM / LXC のスナップショット一覧を返す。

    Args:
        node: ノード名
        vmid: VM ID
        vm_type: "qemu" または "lxc"
    """
    return json.dumps(proxmox.list_snapshots(node, vmid, vm_type), ensure_ascii=False, indent=2)


@mcp.tool()
def proxmox_list_tasks(node: str, limit: int = 20) -> str:
    """ノードの直近タスク一覧を返す。

    Args:
        node: ノード名
        limit: 取得件数 (デフォルト: 20)
    """
    return json.dumps(proxmox.list_tasks(node, limit), ensure_ascii=False, indent=2)


@mcp.tool()
def proxmox_create_snapshot(node: str, vmid: int, snapname: str, description: str = "", vm_type: str = "qemu") -> str:
    """VM / LXC のスナップショットを作成する。

    Args:
        node: ノード名
        vmid: VM ID
        snapname: スナップショット名
        description: 説明 (任意)
        vm_type: "qemu" または "lxc"
    """
    return proxmox.create_snapshot(node, vmid, snapname, description, vm_type)


@mcp.tool()
def proxmox_rollback_snapshot(node: str, vmid: int, snapname: str, vm_type: str = "qemu", confirm: bool = False) -> str:
    """VM / LXC を指定スナップショットにロールバックする。破壊的操作のため confirm=true が必須。

    Args:
        node: ノード名
        vmid: VM ID
        snapname: ロールバック先スナップショット名
        vm_type: "qemu" または "lxc"
        confirm: true を明示しないと実行されない
    """
    if not confirm:
        return "ERROR: 破壊的操作です。confirm=true を明示してください。"
    return proxmox.rollback_snapshot(node, vmid, snapname, vm_type)


# ── Terraform ────────────────────────────────────────────────────────────────

@mcp.tool()
def terraform_plan() -> str:
    """terraform plan を実行して差分を返す。TERRAFORM_DIR で実行される。"""
    return terraform.plan()


@mcp.tool()
def terraform_state_list() -> str:
    """terraform state list を実行して管理中のリソース一覧を返す。"""
    return terraform.state_list()


@mcp.tool()
def terraform_state_show(resource: str) -> str:
    """指定リソースの terraform state show を返す。

    Args:
        resource: リソースアドレス (例: proxmox_vm_qemu.k3s_node[0])
    """
    return terraform.state_show(resource)


@mcp.tool()
def terraform_output() -> str:
    """terraform output を返す。"""
    return terraform.output()


@mcp.tool()
def terraform_apply(confirm: bool = False) -> str:
    """terraform apply を実行する。破壊的操作のため confirm=true が必須。

    Args:
        confirm: true を明示しないと実行されない
    """
    if not confirm:
        return "ERROR: 破壊的操作です。confirm=true を明示してください。"
    return terraform.apply()


# ── Ansible ──────────────────────────────────────────────────────────────────

@mcp.tool()
def ansible_ping(hosts: str = "all") -> str:
    """ansible ping で疎通確認する。ANSIBLE_DIR で実行される。

    Args:
        hosts: 対象ホスト/グループ (デフォルト: all)
    """
    return ansible.ping(hosts)


@mcp.tool()
def ansible_list_inventory() -> str:
    """インベントリのホスト構成を YAML で返す。"""
    return ansible.list_inventory()


@mcp.tool()
def ansible_run_playbook(playbook: str, confirm: bool = False) -> str:
    """指定 playbook を実行する。破壊的操作のため confirm=true が必須。

    Args:
        playbook: playbook ファイルパス (例: site.yml)
        confirm: true を明示しないと実行されない
    """
    if not confirm:
        return "ERROR: 破壊的操作です。confirm=true を明示してください。"
    return ansible.run_playbook(playbook)


# ── kubectl / Helm ───────────────────────────────────────────────────────────

@mcp.tool()
def kubectl_get(resource: str, namespace: str = "", label_selector: str = "",
                output: str = "wide", jq_filter: str = "") -> str:
    """kubectl get <resource> を実行する。

    Args:
        resource: リソース種別 (例: pods, nodes, deployments)
        namespace: 名前空間。省略時は全 namespace
        label_selector: ラベルセレクタ (例: app=nginx, env=prod)
        output: 出力形式 (例: wide, yaml, json。デフォルト: wide)
        jq_filter: jq フィルタ式 (例: '.items[].metadata.name')。指定すると json 出力に適用
    """
    return kubectl.get(resource, namespace or None, label_selector, output, jq_filter)


@mcp.tool()
def kubectl_describe(resource: str, name: str, namespace: str = "") -> str:
    """kubectl describe <resource> <name> を実行する。

    Args:
        resource: リソース種別 (例: pod, node, deployment)
        name: リソース名
        namespace: 名前空間。省略時はデフォルト
    """
    return kubectl.describe(resource, name, namespace or None)


@mcp.tool()
def kubectl_logs(pod: str, namespace: str = "default", tail: int = 100,
                 previous: bool = False, container: str = "", since: str = "") -> str:
    """Pod のログを取得する。

    Args:
        pod: Pod 名
        namespace: 名前空間 (デフォルト: default)
        tail: 末尾から取得する行数 (デフォルト: 100)
        previous: クラッシュ前のコンテナのログを取得 (CrashLoopBackOff 調査に有効)
        container: コンテナ名（複数コンテナ Pod の場合に指定）
        since: 指定期間以降のログを取得 (例: 1h, 30m, 2006-01-02T15:04:05Z)
    """
    return kubectl.logs(pod, namespace, tail, previous, container, since)


@mcp.tool()
def helm_list(namespace: str = "") -> str:
    """Helm リリース一覧を返す。

    Args:
        namespace: 名前空間。省略時は全 namespace
    """
    return kubectl.helm_list(namespace or None)


@mcp.tool()
def helm_get_values(release: str, namespace: str = "default") -> str:
    """指定 Helm リリースの values を返す。

    Args:
        release: リリース名
        namespace: 名前空間 (デフォルト: default)
    """
    return kubectl.helm_get_values(release, namespace)


@mcp.tool()
def helm_show_values(chart: str, version: str = "") -> str:
    """Helm チャートのデフォルト values を表示する（インストール前の設定確認に有用）。

    Args:
        chart: チャート名 (例: bitnami/nginx, stable/grafana)
        version: チャートバージョン (省略時は最新)
    """
    return kubectl.helm_show_values(chart, version)


# ── kubectl 操作系 ───────────────────────────────────────────────────────────

@mcp.tool()
def kubectl_apply(manifest: str = "", manifest_content: str = "", confirm: bool = False) -> str:
    """kubectl apply を実行する。ファイルパスまたはインライン YAML を受け付ける。破壊的操作のため confirm=true が必須。

    Args:
        manifest: マニフェストファイルパス または URL（ファイルが存在する場合）
        manifest_content: インライン YAML 文字列（ファイルなしで直接 apply したい場合）
        confirm: true を明示しないと実行されない
    """
    if not confirm:
        return "ERROR: 破壊的操作です。confirm=true を明示してください。"
    return kubectl.apply(manifest, manifest_content)


@mcp.tool()
def kubectl_rollout_status(deployment: str, namespace: str = "default") -> str:
    """Deployment のロールアウト状態を返す。

    Args:
        deployment: Deployment 名
        namespace: 名前空間 (デフォルト: default)
    """
    return kubectl.rollout_status(deployment, namespace)


@mcp.tool()
def kubectl_rollout_restart(resource: str, namespace: str = "default") -> str:
    """Deployment / StatefulSet / DaemonSet をローリングリスタートする。

    Args:
        resource: リソース指定 (例: deployment/nginx, statefulset/postgres, daemonset/fluentd)
        namespace: 名前空間 (デフォルト: default)
    """
    return kubectl.rollout_restart(resource, namespace)


@mcp.tool()
def kubectl_patch(resource: str, name: str, patch_json: str,
                  namespace: str = "", patch_type: str = "merge") -> str:
    """kubectl patch でリソースを部分更新する。

    Args:
        resource: リソース種別 (例: deployment, service, configmap)
        name: リソース名
        patch_json: パッチ内容（JSON 文字列）(例: '{"spec":{"replicas":3}}')
        namespace: 名前空間。省略時はデフォルト
        patch_type: パッチ種別 ("merge", "strategic", "json")。デフォルト: merge
    """
    return kubectl.patch(resource, name, patch_json, namespace or None, patch_type)


@mcp.tool()
def kubectl_annotate(resource: str, name: str, annotations: str,
                     namespace: str = "", overwrite: bool = True) -> str:
    """kubectl annotate でアノテーションを追加・更新する。

    Args:
        resource: リソース種別 (例: pod, deployment, application)
        name: リソース名
        annotations: スペース区切りの key=value (例: "argocd.argoproj.io/refresh=hard")
        namespace: 名前空間。省略時はデフォルト
        overwrite: 既存アノテーションを上書きする (デフォルト: true)
    """
    return kubectl.annotate(resource, name, annotations, namespace or None, overwrite)


@mcp.tool()
def kubectl_wait(resource: str, condition: str, namespace: str = "",
                 timeout_seconds: int = 60) -> str:
    """kubectl wait でリソースが指定条件になるまで待機する。

    Args:
        resource: リソース指定 (例: pod/my-pod, deployment/nginx, pods --all)
        condition: 待機条件 (例: condition=Ready, condition=Available, delete)
        namespace: 名前空間。省略時は全 namespace
        timeout_seconds: 最大待機秒数 (デフォルト: 60)
    """
    return kubectl.wait(resource, condition, namespace or None, timeout_seconds)


@mcp.tool()
def kubectl_top(resource: str = "nodes", namespace: str = "") -> str:
    """Node / Pod のリソース使用量を返す。

    Args:
        resource: "nodes" または "pods" (デフォルト: nodes)
        namespace: pods の場合の名前空間。省略時は全 namespace
    """
    return kubectl.top(resource, namespace or None)


@mcp.tool()
def kubectl_delete(resource: str, name: str, namespace: str = "", confirm: bool = False) -> str:
    """kubectl delete <resource> <name> を実行する。破壊的操作のため confirm=true が必須。

    Args:
        resource: リソース種別 (例: pod, deployment, pvc)
        name: リソース名
        namespace: 名前空間。省略時はデフォルト
        confirm: true を明示しないと実行されない
    """
    if not confirm:
        return "ERROR: 破壊的操作です。confirm=true を明示してください。"
    return kubectl.delete(resource, name, namespace or None)


@mcp.tool()
def helm_upgrade(release: str, chart: str, namespace: str = "default", values_file: str = "", confirm: bool = False) -> str:
    """helm upgrade --install でリリースをアップグレード／インストールする。破壊的操作のため confirm=true が必須。

    Args:
        release: リリース名
        chart: チャート名 (例: bitnami/nginx)
        namespace: 名前空間 (デフォルト: default)
        values_file: values ファイルパス (任意)
        confirm: true を明示しないと実行されない
    """
    if not confirm:
        return "ERROR: 破壊的操作です。confirm=true を明示してください。"
    return kubectl.helm_upgrade(release, chart, namespace, values_file)


@mcp.tool()
def helm_uninstall(release: str, namespace: str = "default", confirm: bool = False) -> str:
    """helm uninstall でリリースを削除する。破壊的操作のため confirm=true が必須。

    Args:
        release: リリース名
        namespace: 名前空間 (デフォルト: default)
        confirm: true を明示しないと実行されない
    """
    if not confirm:
        return "ERROR: 破壊的操作です。confirm=true を明示してください。"
    return kubectl.helm_uninstall(release, namespace)


# ── kubectl 調査系（追加） ────────────────────────────────────────────────────

@mcp.tool()
def kubectl_exec(pod: str, command: str, namespace: str = "default", container: str = "") -> str:
    """Pod 内でコマンドを実行する（シェル調査・疎通確認等）。

    Args:
        pod: Pod 名
        command: 実行するコマンド (例: "ls -la /tmp", "cat /etc/hosts")
        namespace: 名前空間 (デフォルト: default)
        container: コンテナ名（複数コンテナ Pod の場合に指定）
    """
    return kubectl.exec(pod, command, namespace, container)


@mcp.tool()
def kubectl_get_events(namespace: str = "", field_selector: str = "") -> str:
    """Namespace / Pod のイベント一覧を返す（障害原因特定に有効）。

    Args:
        namespace: 名前空間。省略時は全 namespace
        field_selector: フィールドセレクタ (例: involvedObject.name=my-pod)
    """
    return kubectl.get_events(namespace or None, field_selector)


@mcp.tool()
def kubectl_get_secret(name: str, namespace: str = "default") -> str:
    """Secret の内容をマスク付きで返す（値は *** に置換）。

    Args:
        name: Secret 名
        namespace: 名前空間 (デフォルト: default)
    """
    return kubectl.get_secret(name, namespace)


@mcp.tool()
def kubectl_get_configmap(name: str, namespace: str = "default") -> str:
    """ConfigMap の内容を返す。

    Args:
        name: ConfigMap 名
        namespace: 名前空間 (デフォルト: default)
    """
    return kubectl.get_configmap(name, namespace)


@mcp.tool()
def kubectl_run(image: str, command: str, namespace: str = "default") -> str:
    """一時 Pod でコマンドを実行して出力を返す（Pod は自動削除）。

    Args:
        image: コンテナイメージ (例: busybox, curlimages/curl)
        command: 実行するコマンド (例: "nslookup kubernetes.default")
        namespace: 名前空間 (デフォルト: default)
    """
    return kubectl.run_pod(image, command, namespace)


@mcp.tool()
def kubectl_port_forward(resource: str, ports: str, namespace: str = "default") -> str:
    """kubectl port-forward をバックグラウンドで開始する。

    Args:
        resource: 転送先リソース (例: pod/my-pod, svc/my-svc, deployment/my-deploy)
        ports: ポートマッピング (例: 8080:80, 5432:5432)
        namespace: 名前空間 (デフォルト: default)
    """
    return kubectl.port_forward(resource, ports, namespace)


# ── Proxmox 調査系（追加） ────────────────────────────────────────────────────

@mcp.tool()
def proxmox_get_vm_config(node: str, vmid: int, vm_type: str = "qemu") -> str:
    """VM / LXC の設定詳細（CPU / メモリ / ディスク / ネットワーク）を返す。

    Args:
        node: ノード名 (例: pve1)
        vmid: VM ID
        vm_type: "qemu" または "lxc"
    """
    return json.dumps(proxmox.get_vm_config(node, vmid, vm_type), ensure_ascii=False, indent=2)


@mcp.tool()
def proxmox_get_task_log(node: str, upid: str) -> str:
    """タスク UPID のログを返す（proxmox_list_tasks で取得した UPID を指定）。

    Args:
        node: ノード名
        upid: タスク UPID (例: UPID:pve1:00001234:...)
    """
    return json.dumps(proxmox.get_task_log(node, upid), ensure_ascii=False, indent=2)


@mcp.tool()
def proxmox_get_cluster_status() -> str:
    """Proxmox クラスター全体の健全性ステータスを返す。"""
    return json.dumps(proxmox.get_cluster_status(), ensure_ascii=False, indent=2)


@mcp.tool()
def proxmox_list_networks(node: str) -> str:
    """ノードのネットワーク設定一覧を返す。

    Args:
        node: ノード名 (例: pve1)
    """
    return json.dumps(proxmox.list_networks(node), ensure_ascii=False, indent=2)


@mcp.tool()
def proxmox_get_replication_status(node: str) -> str:
    """ノードの ZFS レプリケーションジョブの状態を返す（node01 ↔ node02 の同期確認）。

    Args:
        node: ノード名 (例: pve-node01)
    """
    return json.dumps(proxmox.get_replication_status(node), ensure_ascii=False, indent=2)


@mcp.tool()
def proxmox_get_backup_jobs(node: str, limit: int = 20) -> str:
    """vzdump バックアップタスクの履歴を返す。

    Args:
        node: ノード名
        limit: 取得件数 (デフォルト: 20)
    """
    return json.dumps(proxmox.get_backup_jobs(node, limit), ensure_ascii=False, indent=2)


@mcp.tool()
def proxmox_get_certificate_info(node: str) -> str:
    """ノードの TLS 証明書情報と残り有効日数を返す。

    Args:
        node: ノード名 (例: pve-node01)
    """
    return json.dumps(proxmox.get_certificate_info(node), ensure_ascii=False, indent=2)


@mcp.tool()
def proxmox_get_storage_content(node: str, storage: str, content_type: str = "") -> str:
    """ストレージ内のコンテンツ（ISO / テンプレート等）一覧を返す。

    Args:
        node: ノード名
        storage: ストレージ名 (例: local, local-lvm)
        content_type: コンテンツ種別フィルタ (例: iso, vztmpl, images)。省略時は全種別
    """
    return json.dumps(proxmox.get_storage_content(node, storage, content_type), ensure_ascii=False, indent=2)


# ── Ansible 追加 ──────────────────────────────────────────────────────────────

@mcp.tool()
def ansible_run_module(hosts: str, module: str, args: str = "") -> str:
    """アドホックモジュールを実行する（ping 以外の任意モジュール）。

    Args:
        hosts: 対象ホスト/グループ (例: all, webservers, 192.168.1.10)
        module: モジュール名 (例: shell, command, setup, copy, file)
        args: モジュール引数 (例: "cmd='uptime'", "src=/tmp/a dest=/tmp/b")
    """
    return ansible.run_module(hosts, module, args)


@mcp.tool()
def ansible_get_facts(hosts: str = "all") -> str:
    """ホストの facts（OS / ハードウェア情報）を収集して返す。

    Args:
        hosts: 対象ホスト/グループ (デフォルト: all)
    """
    return ansible.get_facts(hosts)


# ── Terraform 追加 ────────────────────────────────────────────────────────────

@mcp.tool()
def terraform_validate() -> str:
    """terraform validate で構文検証を行う（apply なし）。TERRAFORM_DIR で実行される。"""
    return terraform.validate()


@mcp.tool()
def terraform_destroy(confirm: bool = False) -> str:
    """terraform destroy を実行する。破壊的操作のため confirm=true が必須。

    Args:
        confirm: true を明示しないと実行されない
    """
    if not confirm:
        return "ERROR: 破壊的操作です。confirm=true を明示してください。"
    return terraform.destroy()


# ── Lab ユーティリティ ────────────────────────────────────────────────────────

@mcp.tool()
def lab_ping(host: str, count: int = 4) -> str:
    """Raspberry Pi から指定ホストへの疎通確認を行う。

    Args:
        host: ホスト名または IP アドレス
        count: ping 回数 (デフォルト: 4)
    """
    return lab.ping(host, count)


@mcp.tool()
def lab_wakeup(mac: str, broadcast: str = "192.168.210.255") -> str:
    """Wake-on-LAN でホストを起動する。

    Args:
        mac: MAC アドレス (例: AA:BB:CC:DD:EE:FF)
        broadcast: ブロードキャストアドレス (デフォルト: 192.168.210.255)
    """
    return lab.wakeup(mac, broadcast)


@mcp.tool()
def lab_exec(host: str, command: str, user: str = "", ssh_key: str = "",
             timeout_seconds: int = 30) -> str:
    """SSH 経由で VM / ホスト上のコマンドを直接実行する。

    Args:
        host: 接続先ホスト名または IP アドレス
        command: 実行するコマンド (例: "df -h", "systemctl status nginx")
        user: SSH ユーザー名（省略時は SSH_USER 環境変数）
        ssh_key: SSH 秘密鍵パス（省略時は SSH_KEY 環境変数）
        timeout_seconds: タイムアウト秒数（デフォルト: 30、最大推奨: 300）
    """
    return lab.exec(host, command, user, ssh_key, timeout_seconds)


@mcp.tool()
def lab_check_port(host: str, port: int, timeout: float = 3.0) -> str:
    """指定ホスト・ポートの開閉・疎通を確認する。

    Args:
        host: ホスト名または IP アドレス
        port: ポート番号
        timeout: タイムアウト秒数 (デフォルト: 3.0)
    """
    return lab.check_port(host, port, timeout)


@mcp.tool()
def lab_dns_lookup(host: str, server: str = "") -> str:
    """DNS 名前解決を行う（Pi-hole 経由の確認等）。

    Args:
        host: 解決するホスト名または IP（逆引き）
        server: 問い合わせ先 DNS サーバー (例: 192.168.210.1)。省略時はシステムデフォルト
    """
    return lab.dns_lookup(host, server)


@mcp.tool()
def lab_cluster_health() -> str:
    """ラボ全体の健全性サマリーを返す。

    Proxmox クラスター・Kubernetes ノード・異常 Pod を一括確認する。
    """
    result: dict = {}

    # Proxmox クラスター
    try:
        result["proxmox_cluster"] = proxmox.get_cluster_status()
    except Exception as e:
        result["proxmox_cluster"] = {"error": str(e)}

    # Proxmox ノードリソース
    try:
        result["proxmox_nodes"] = proxmox.list_nodes()
    except Exception as e:
        result["proxmox_nodes"] = {"error": str(e)}

    # Kubernetes ノード
    try:
        result["k8s_nodes"] = kubectl.get("nodes", output="wide")
    except Exception as e:
        result["k8s_nodes"] = {"error": str(e)}

    # 異常 Pod（Running / Completed 以外）
    try:
        all_pods = kubectl.get("pods", output="wide")
        unhealthy = [
            line for line in all_pods.splitlines()
            if any(s in line for s in ["CrashLoopBackOff", "Error", "OOMKilled",
                                        "Pending", "ImagePullBackOff", "Evicted"])
        ]
        result["unhealthy_pods"] = unhealthy if unhealthy else "異常な Pod はありません"
    except Exception as e:
        result["unhealthy_pods"] = {"error": str(e)}

    return json.dumps(result, ensure_ascii=False, indent=2)


# ── ArgoCD ───────────────────────────────────────────────────────────────────

@mcp.tool()
def argocd_list_apps(project: str = "") -> str:
    """ArgoCD の全アプリケーション一覧と sync/health 状態を返す。

    環境変数 ARGOCD_SERVER・ARGOCD_TOKEN が必要。

    Args:
        project: プロジェクト名でフィルタ（省略時は全プロジェクト）
    """
    try:
        return json.dumps(argocd.list_apps(project), ensure_ascii=False, indent=2)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def argocd_get_app(name: str) -> str:
    """指定 ArgoCD アプリケーションの詳細（sync/health/リソース一覧）を返す。

    Args:
        name: アプリケーション名
    """
    try:
        return json.dumps(argocd.get_app(name), ensure_ascii=False, indent=2)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def argocd_sync(name: str, revision: str = "", prune: bool = False,
                dry_run: bool = False) -> str:
    """ArgoCD アプリケーションの sync を実行する。

    Args:
        name: アプリケーション名
        revision: 同期するリビジョン（省略時は HEAD）
        prune: Kubernetes に存在するが Git にないリソースを削除する
        dry_run: 実際には変更せずに計画だけ表示する
    """
    try:
        result = argocd.sync_app(name, revision, prune, dry_run)
        return json.dumps(
            {
                "name": result.get("metadata", {}).get("name"),
                "sync_status": result.get("status", {}).get("sync", {}).get("status"),
                "health_status": result.get("status", {}).get("health", {}).get("status"),
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def argocd_refresh(name: str, hard: bool = True) -> str:
    """ArgoCD アプリケーションのキャッシュを更新する（hard refresh）。

    Args:
        name: アプリケーション名
        hard: True でハードリフレッシュ（Git から再取得）、False でソフトリフレッシュ
    """
    try:
        result = argocd.refresh_app(name, hard)
        return json.dumps(
            {
                "name": result.get("metadata", {}).get("name"),
                "sync_status": result.get("status", {}).get("sync", {}).get("status"),
                "health_status": result.get("status", {}).get("health", {}).get("status"),
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return f"ERROR: {e}"


# ── エントリポイント ──────────────────────────────────────────────────────────

def main() -> None:
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
