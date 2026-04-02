import json
from mcp.server.fastmcp import FastMCP
from lab_mcp import config
from lab_mcp.tools import proxmox, terraform, ansible, kubectl, lab

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
def kubectl_get(resource: str, namespace: str = "") -> str:
    """kubectl get <resource> を実行する。

    Args:
        resource: リソース種別 (例: pods, nodes, deployments)
        namespace: 名前空間。省略時は全 namespace
    """
    return kubectl.get(resource, namespace or None)


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
def kubectl_logs(pod: str, namespace: str = "default", tail: int = 100) -> str:
    """Pod のログを取得する。

    Args:
        pod: Pod 名
        namespace: 名前空間 (デフォルト: default)
        tail: 末尾から取得する行数 (デフォルト: 100)
    """
    return kubectl.logs(pod, namespace, tail)


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


# ── kubectl 操作系 ───────────────────────────────────────────────────────────

@mcp.tool()
def kubectl_apply(manifest: str, confirm: bool = False) -> str:
    """kubectl apply -f <manifest> を実行する。破壊的操作のため confirm=true が必須。

    Args:
        manifest: マニフェストファイルパス または URL
        confirm: true を明示しないと実行されない
    """
    if not confirm:
        return "ERROR: 破壊的操作です。confirm=true を明示してください。"
    return kubectl.apply(manifest)


@mcp.tool()
def kubectl_rollout_status(deployment: str, namespace: str = "default") -> str:
    """Deployment のロールアウト状態を返す。

    Args:
        deployment: Deployment 名
        namespace: 名前空間 (デフォルト: default)
    """
    return kubectl.rollout_status(deployment, namespace)


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


# ── エントリポイント ──────────────────────────────────────────────────────────

def main() -> None:
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
