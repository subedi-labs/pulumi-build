from dataclasses import dataclass
from typing import Literal

import pulumi

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
    ssh_private_key_path: str | None

    k3s_version: str
    k3s_token: pulumi.Output[str]

    longhorn: LonghornSpec
    primary_server_ip: str
