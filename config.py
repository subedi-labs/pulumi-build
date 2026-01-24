from dataclasses import dataclass
from typing import Literal
import pulumi
from .utils import ip_no_cidr

NodeRole = Literal["server", "worker"]

@dataclass(frozen=True)
class NodeSpec:
    name: str
    role: NodeRole
    proxmoxNode: str
    vmId: int
    ip4: str
    gw4: str
    cores: int
    memoryMb: int
    diskGb: int
    datastoreId: str
    initDatastoreId: str
    bridge: str
    vlanId: int | None = None

@dataclass(frozen=True)
class TemplateSpec:
    nodeName: str
    vmId: int

@dataclass(frozen=True)
class LonghornSpec:
    replica_count: int
    kubelet_root_dir: str
    ssd_node_names: list[str]

@dataclass(frozen=True)
class Config:
    stack: str
    nodes: list[NodeSpec]
    template: TemplateSpec
    ssh_user: str
    ssh_private_key: pulumi.Output[str]
    k3s_version: str
    k3s_token: pulumi.Output[str]
    longhorn: LonghornSpec
    primary_server_ip: str

def load_config() -> Config:
    c = pulumi.Config()
    stack = pulumi.get_stack()

    ssh_user = c.get("sshUser") or "ubuntu"
    ssh_private_key = c.require_secret("sshPrivateKey")

    k3s_version = c.get("k3sVersion") or ""
    k3s_token = c.require_secret("k3sToken")

    nodes = [NodeSpec(**n) for n in c.require_object("nodes")]
    template = TemplateSpec(**c.require_object("template"))

    ssd_node_names = c.require_object("ssdNodeNames")
    longhorn = LonghornSpec(
        replica_count=int(c.get("longhornReplicaCount") or 2),
        kubelet_root_dir=str(c.get("longhornKubeletRootDir") or "/var/lib/rancher/k3s/agent/kubelet"),
        ssd_node_names=ssd_node_names,
    )

    servers = [n for n in nodes if n.role == "server"]
    if not servers:
        raise ValueError("Define at least one server node.")
    primary_server_ip = ip_no_cidr(servers[0].ip4)

    return Config(
        stack=stack,
        nodes=nodes,
        template=template,
        ssh_user=ssh_user,
        ssh_private_key=ssh_private_key,
        k3s_version=k3s_version,
        k3s_token=k3s_token,
        longhorn=longhorn,
        primary_server_ip=primary_server_ip,
    )
