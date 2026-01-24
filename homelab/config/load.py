import pulumi

from .models import Config, NodeSpec, TemplateSpec, LonghornSpec
from ..utils.net import ip_no_cidr


def load_config() -> Config:
    """
    Reads stack config from Pulumi.<stack>.yaml + Pulumi secrets.

    Required keys:
      - sshUser (optional, default ubuntu)
      - sshPrivateKey (secret)
      - k3sVersion
      - k3sToken (secret)
      - template (object)
      - nodes (list)
      - ssdNodeNames (list)
      - longhornReplicaCount (optional)
      - longhornKubeletRootDir (optional)
    """
    c = pulumi.Config()
    stack = pulumi.get_stack()

    ssh_user = c.get("sshUser") or "ubuntu"
    ssh_private_key = c.require_secret("sshPrivateKey")

    k3s_version = c.get("k3sVersion") or ""
    k3s_token = c.require_secret("k3sToken")

    nodes_raw = c.require_object("nodes")
    nodes = [NodeSpec(**n) for n in nodes_raw]

    # Validate roles early (fast fail on typos)
    valid_roles = {"server", "worker"}
    for n in nodes:
        if n.role not in valid_roles:
            raise ValueError(
                f"Invalid role {n.role!r} on node {n.name!r}. Must be one of {sorted(valid_roles)}"
            )

    template_raw = c.require_object("template")
    template = TemplateSpec(**template_raw)

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
        k3s_version=k3s_version,
        k3s_token=k3s_token,
        longhorn=longhorn,
        primary_server_ip=primary_server_ip,
    )
