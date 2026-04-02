import json
from mcp.server.fastmcp import FastMCP
from lab_mcp import config
from lab_mcp.tools import proxmox, terraform

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


# ── エントリポイント ──────────────────────────────────────────────────────────

def main() -> None:
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
