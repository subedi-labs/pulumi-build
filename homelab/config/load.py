import os
import pulumi

from .models import Config, NodeSpec, TemplateSpec, LonghornSpec
from ..utils.net import ip_no_cidr


def _read_private_key_from_path(path: str) -> pulumi.Output[str]:
    expanded = os.path.expanduser(path)
    if not os.path.isfile(expanded):
        raise FileNotFoundError(f"sshPrivateKeyPath does not exist: {expanded}")

    with open(expanded, "r", encoding="utf-8") as f:
        data = f.read()

    # Keep it secret inside Pulumi even though it was loaded locally
    return pulumi.Output.secret(data)


def load_config() -> Config:
    """
    Reads stack config from Pulumi.<stack>.yaml + Pulumi secrets.

    SSH behavior:
      - Prefer sshPrivateKeyPath (read ~/.ssh/... at deploy time)
      - Fallback to sshPrivateKey (secret in Pulumi config)

    Required keys:
      - template (object)
      - nodes (list)
      - ssdNodeNames (list)
      - k3sVersion
      - k3sToken (secret)
      - proxmoxEndpoint/proxmoxUsername/proxmoxApiToken/etc. (provider module reads these)
    """
    c = pulumi.Config()
    stack = pulumi.get_stack()

    ssh_user = c.get("sshUser") or "ubuntu"

    ssh_private_key_path = c.get("sshPrivateKeyPath")
    if ssh_private_key_path:
        ssh_private_key = _read_private_key_from_path(ssh_private_key_path)
    else:
        ssh_private_key = c.require_secret("sshPrivateKey")

    k3s_version = c.get("k3sVersion") or ""
    if not k3s_version:
        raise ValueError("Missing required config key: k3sVersion")

    k3s_token = c.require_secret("k3sToken")

    template_raw = c.require_object("template")
    template = TemplateSpec(**template_raw)

    nodes_raw = c.require_object("nodes")
    nodes = [NodeSpec(**n) for n in nodes_raw]

    valid_roles = {"server", "worker"}
    for n in nodes:
        if n.role not in valid_roles:
            raise ValueError(
                f"Invalid role {n.role!r} on node {n.name!r}. Must be one of {sorted(valid_roles)}"
            )

    ssd_node_names = c.require_object("ssdNodeNames")
    longhorn = LonghornSpec(
        replica_count=int(c.get("longhornReplicaCount") or 2),
        kubelet_root_dir=str(c.get("longhornKubeletRootDir") or "/var/lib/rancher/k3s/agent/kubelet"),
        ssd_node_names=ssd_node_names,
    )

    servers = [n for n in nodes if n.role == "server"]
    if not servers:
        raise ValueError("Config error: define at least one server node (role: 'server').")

    primary_server_ip = ip_no_cidr(servers[0].ip4)

    return Config(
        stack=stack,
        nodes=nodes,
        template=template,
        ssh_user=ssh_user,
        ssh_private_key=ssh_private_key,
        ssh_private_key_path=ssh_private_key_path,
        k3s_version=k3s_version,
        k3s_token=k3s_token,
        longhorn=longhorn,
        primary_server_ip=primary_server_ip,
    )
