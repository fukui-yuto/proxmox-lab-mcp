import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"環境変数 {key} が未設定です")
    return value


PROXMOX_HOST = _require("PROXMOX_HOST")
PROXMOX_USER = _require("PROXMOX_USER")
PROXMOX_TOKEN_NAME = _require("PROXMOX_TOKEN_NAME")
PROXMOX_TOKEN_VALUE = _require("PROXMOX_TOKEN_VALUE")
PROXMOX_VERIFY_SSL = os.getenv("PROXMOX_VERIFY_SSL", "false").lower() == "true"

TERRAFORM_DIR = os.getenv("TERRAFORM_DIR", "")
ANSIBLE_DIR = os.getenv("ANSIBLE_DIR", "")
KUBECONFIG = os.getenv("KUBECONFIG", os.path.expanduser("~/.kube/config"))

SSH_USER = os.getenv("SSH_USER", "")
SSH_KEY = os.getenv("SSH_KEY", "")

ARGOCD_SERVER = os.getenv("ARGOCD_SERVER", "")
ARGOCD_TOKEN = os.getenv("ARGOCD_TOKEN", "")
ARGOCD_VERIFY_SSL = os.getenv("ARGOCD_VERIFY_SSL", "false").lower() == "true"
ARGOCD_USERNAME = os.getenv("ARGOCD_USERNAME", "")
ARGOCD_PASSWORD = os.getenv("ARGOCD_PASSWORD", "")

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))
