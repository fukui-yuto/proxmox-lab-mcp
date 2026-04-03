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


def create_snapshot(node: str, vmid: int, snapname: str, description: str = "", vm_type: str = "qemu") -> str:
    """VM / LXC のスナップショットを作成する。"""
    pve = _client()
    if vm_type == "lxc":
        pve.nodes(node).lxc(vmid).snapshot.post(snapname=snapname, description=description)
    else:
        pve.nodes(node).qemu(vmid).snapshot.post(snapname=snapname, description=description)
    return f"VMID {vmid} のスナップショット '{snapname}' を作成しました。"


def rollback_snapshot(node: str, vmid: int, snapname: str, vm_type: str = "qemu") -> str:
    """VM / LXC を指定スナップショットにロールバックする。"""
    pve = _client()
    if vm_type == "lxc":
        pve.nodes(node).lxc(vmid).snapshot(snapname).rollback.post()
    else:
        pve.nodes(node).qemu(vmid).snapshot(snapname).rollback.post()
    return f"VMID {vmid} をスナップショット '{snapname}' にロールバックしました。"


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


def get_vm_config(node: str, vmid: int, vm_type: str = "qemu") -> dict:
    """VM / LXC の設定詳細（CPU / メモリ / ディスク / ネットワーク）を返す。"""
    pve = _client()
    if vm_type == "lxc":
        cfg = pve.nodes(node).lxc(vmid).config.get()
    else:
        cfg = pve.nodes(node).qemu(vmid).config.get()
    return cfg


def get_task_log(node: str, upid: str) -> list[dict]:
    """タスク UPID のログを返す。"""
    pve = _client()
    return pve.nodes(node).tasks(upid).log.get()


def get_cluster_status() -> list[dict]:
    """クラスター全体の健全性ステータスを返す。"""
    pve = _client()
    return pve.cluster.status.get()


def list_networks(node: str) -> list[dict]:
    """ノードのネットワーク設定一覧を返す。"""
    pve = _client()
    return pve.nodes(node).network.get()


def get_replication_status(node: str) -> list[dict]:
    """ノードの ZFS レプリケーションジョブの状態一覧を返す。"""
    pve = _client()
    jobs = pve.nodes(node).replication.get()
    return [
        {
            "id": j.get("id"),
            "target": j.get("target"),
            "vmid": j.get("guest"),
            "type": j.get("type"),
            "enabled": j.get("enabled", 1),
            "last_sync": j.get("last_sync"),
            "last_try": j.get("last_try"),
            "fail_count": j.get("fail_count", 0),
            "error": j.get("error", ""),
        }
        for j in jobs
    ]


def get_backup_jobs(node: str, limit: int = 20) -> list[dict]:
    """vzdump バックアップタスクの履歴を返す。"""
    pve = _client()
    tasks = pve.nodes(node).tasks.get(limit=limit, typefilter="vzdump")
    return [
        {
            "upid": t.get("upid"),
            "status": t.get("status"),
            "starttime": t.get("starttime"),
            "endtime": t.get("endtime"),
            "user": t.get("user"),
        }
        for t in tasks
    ]


def get_certificate_info(node: str) -> list[dict]:
    """ノードの TLS 証明書情報（残り日数含む）を返す。"""
    import time
    pve = _client()
    certs = pve.nodes(node).certificates.info.get()
    now = time.time()
    result = []
    for c in certs:
        notafter = c.get("notafter", 0)
        days_left = round((notafter - now) / 86400) if notafter else None
        result.append({
            "filename": c.get("filename"),
            "subject": c.get("subject"),
            "issuer": c.get("issuer"),
            "notbefore": c.get("notbefore"),
            "notafter": notafter,
            "days_left": days_left,
            "fingerprint": c.get("fingerprint"),
        })
    return result


def get_storage_content(node: str, storage: str, content_type: str = "") -> list[dict]:
    """ストレージ内のコンテンツ（ISO / テンプレート等）一覧を返す。"""
    pve = _client()
    params = {}
    if content_type:
        params["content"] = content_type
    items = pve.nodes(node).storage(storage).content.get(**params)
    return [
        {
            "volid": i.get("volid"),
            "content": i.get("content"),
            "format": i.get("format"),
            "size_gb": round(i.get("size", 0) / 1024**3, 2),
        }
        for i in items
    ]
