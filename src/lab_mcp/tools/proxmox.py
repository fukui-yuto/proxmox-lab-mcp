from proxmoxer import ProxmoxAPI
from lab_mcp import config


def _client() -> ProxmoxAPI:
    return ProxmoxAPI(
        config.PROXMOX_HOST,
        user=config.PROXMOX_USER,
        token_name=config.PROXMOX_TOKEN_NAME,
        token_value=config.PROXMOX_TOKEN_VALUE,
        verify_ssl=config.PROXMOX_VERIFY_SSL,
    )


def list_nodes() -> list[dict]:
    """ノード一覧とリソース使用状況を返す。"""
    pve = _client()
    nodes = []
    for node in pve.nodes.get():
        nodes.append({
            "node": node["node"],
            "status": node.get("status"),
            "cpu": round(node.get("cpu", 0) * 100, 1),
            "mem_used_gb": round(node.get("mem", 0) / 1024**3, 2),
            "mem_total_gb": round(node.get("maxmem", 0) / 1024**3, 2),
            "uptime_h": round(node.get("uptime", 0) / 3600, 1),
        })
    return nodes


def list_vms() -> list[dict]:
    """全ノードの VM / LXC 一覧を返す。"""
    pve = _client()
    vms = []
    for node in pve.nodes.get():
        node_name = node["node"]
        for vm in pve.nodes(node_name).qemu.get():
            vms.append({
                "type": "qemu",
                "node": node_name,
                "vmid": vm["vmid"],
                "name": vm.get("name", ""),
                "status": vm.get("status"),
                "cpu": vm.get("cpus"),
                "mem_mb": round(vm.get("maxmem", 0) / 1024**2),
            })
        for ct in pve.nodes(node_name).lxc.get():
            vms.append({
                "type": "lxc",
                "node": node_name,
                "vmid": ct["vmid"],
                "name": ct.get("name", ""),
                "status": ct.get("status"),
                "cpu": ct.get("cpus"),
                "mem_mb": round(ct.get("maxmem", 0) / 1024**2),
            })
    return vms


def get_vm_status(node: str, vmid: int, vm_type: str = "qemu") -> dict:
    """特定 VM / LXC の詳細ステータスを返す。vm_type は 'qemu' または 'lxc'。"""
    pve = _client()
    if vm_type == "lxc":
        status = pve.nodes(node).lxc(vmid).status.current.get()
    else:
        status = pve.nodes(node).qemu(vmid).status.current.get()
    return {
        "vmid": vmid,
        "name": status.get("name"),
        "status": status.get("status"),
        "cpu_usage": round(status.get("cpu", 0) * 100, 2),
        "mem_used_mb": round(status.get("mem", 0) / 1024**2),
        "mem_total_mb": round(status.get("maxmem", 0) / 1024**2),
        "disk_used_gb": round(status.get("disk", 0) / 1024**3, 2),
        "uptime_h": round(status.get("uptime", 0) / 3600, 1),
    }


def get_node_resources(node: str) -> dict:
    """ノードのリソース使用量を返す。"""
    pve = _client()
    status = pve.nodes(node).status.get()
    return {
        "node": node,
        "cpu_usage_pct": round(status["cpu"] * 100, 1),
        "cpu_cores": status["cpuinfo"]["cores"],
        "mem_used_gb": round(status["memory"]["used"] / 1024**3, 2),
        "mem_total_gb": round(status["memory"]["total"] / 1024**3, 2),
        "swap_used_gb": round(status["swap"]["used"] / 1024**3, 2),
        "swap_total_gb": round(status["swap"]["total"] / 1024**3, 2),
        "load_avg": status.get("loadavg"),
    }


def start_vm(node: str, vmid: int, vm_type: str = "qemu") -> str:
    """VM / LXC を起動する。"""
    pve = _client()
    if vm_type == "lxc":
        pve.nodes(node).lxc(vmid).status.start.post()
    else:
        pve.nodes(node).qemu(vmid).status.start.post()
    return f"VMID {vmid} の起動を開始しました。"


def stop_vm(node: str, vmid: int, vm_type: str = "qemu") -> str:
    """VM / LXC を停止する。"""
    pve = _client()
    if vm_type == "lxc":
        pve.nodes(node).lxc(vmid).status.stop.post()
    else:
        pve.nodes(node).qemu(vmid).status.stop.post()
    return f"VMID {vmid} の停止を開始しました。"


def reboot_vm(node: str, vmid: int, vm_type: str = "qemu") -> str:
    """VM / LXC を再起動する。"""
    pve = _client()
    if vm_type == "lxc":
        pve.nodes(node).lxc(vmid).status.reboot.post()
    else:
        pve.nodes(node).qemu(vmid).status.reboot.post()
    return f"VMID {vmid} の再起動を開始しました。"


def list_snapshots(node: str, vmid: int, vm_type: str = "qemu") -> list[dict]:
    """VM / LXC のスナップショット一覧を返す。"""
    pve = _client()
    if vm_type == "lxc":
        snaps = pve.nodes(node).lxc(vmid).snapshot.get()
    else:
        snaps = pve.nodes(node).qemu(vmid).snapshot.get()
    return [
        {
            "name": s.get("name"),
            "description": s.get("description", ""),
            "snaptime": s.get("snaptime"),
        }
        for s in snaps
    ]


def list_tasks(node: str, limit: int = 20) -> list[dict]:
    """ノードの直近タスク一覧を返す。"""
    pve = _client()
    tasks = pve.nodes(node).tasks.get(limit=limit)
    return [
        {
            "upid": t.get("upid"),
            "type": t.get("type"),
            "status": t.get("status"),
            "user": t.get("user"),
            "starttime": t.get("starttime"),
        }
        for t in tasks
    ]


def list_storage() -> list[dict]:
    """全ノードのストレージ一覧と使用量を返す。"""
    pve = _client()
    result = []
    for node in pve.nodes.get():
        node_name = node["node"]
        for s in pve.nodes(node_name).storage.get():
            result.append({
                "node": node_name,
                "storage": s["storage"],
                "type": s.get("type"),
                "status": s.get("active") and "active" or "inactive",
                "used_gb": round(s.get("used", 0) / 1024**3, 2),
                "total_gb": round(s.get("total", 0) / 1024**3, 2),
                "used_pct": round(s.get("used_fraction", 0) * 100, 1),
            })
    return result
