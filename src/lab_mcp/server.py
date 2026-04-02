import json
from mcp.server.fastmcp import FastMCP
from lab_mcp import config
from lab_mcp.tools import proxmox

mcp = FastMCP("proxmox-lab")


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


# ── エントリポイント ──────────────────────────────────────────────────────────

def main() -> None:
    mcp.run(transport="sse", host=config.MCP_HOST, port=config.MCP_PORT)


if __name__ == "__main__":
    main()
