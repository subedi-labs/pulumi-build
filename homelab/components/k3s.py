import pulumi
from pulumi_command.remote import Command, CommandArgs, ConnectionArgs
from typing import Mapping

from config.models import NodeSpec
from utils.net import ip_no_cidr
from labels.constants import (
    LABEL_CLUSTER,
    LABEL_ROLE,
    LABEL_STORAGE,
    LABEL_NODEPOOL,
    LABEL_ZONE,
    ZONE_MAP,
)

def bootstrap_k3s(
    *,
    nodes: list[NodeSpec],
    vm_by_name: Mapping[str, pulumi.Resource],  # ✅ Mapping fixes invariance issue
    ssh_user: str,
    ssh_private_key: pulumi.Output[str],
    k3s_version: str,
    k3s_token: pulumi.Output[str],
    ssd_node_names: list[str],
    cluster_name: str,
) -> pulumi.ComponentResource:
    """
    Bootstrap a K3s cluster across the given nodes.

    Depends_on strategy (minimal but correct):
      - each node prereq depends only on that node VM
      - primary server depends on its prereq
      - join servers/workers depend on (their prereq + primary server)
    """
    servers = [n for n in nodes if n.role == "server"]
    workers = [n for n in nodes if n.role == "worker"]
    if not servers:
        raise ValueError("Need at least one server node.")

    primary = servers[0]
    primary_ip = ip_no_cidr(primary.ip4)
    ssd_set: set[str] = set(ssd_node_names)

    component = pulumi.ComponentResource(
        "pulumi-automate:k3s:Bootstrap",
        "k3s-bootstrap",
        None,
    )

    def conn(host: str) -> ConnectionArgs:
        return ConnectionArgs(
            host=host,
            user=ssh_user,
            private_key=ssh_private_key,
            port=22,
        )

    def remote(
        name: str,
        *,
        host: str,
        script: pulumi.Input[str],
        triggers: list[str],
        depends_on: list[pulumi.Resource] | None = None,
    ) -> Command:
        return Command(
            name,
            CommandArgs(
                connection=conn(host),
                create=script,
                triggers=triggers,
            ),
            opts=pulumi.ResourceOptions(
                parent=component,
                depends_on=depends_on,
            ),
        )

    def node_label_kv(node: NodeSpec) -> list[str]:
        storage = "ssd" if node.name in ssd_set else "hdd"
        zone = ZONE_MAP.get(node.proxmoxNode, node.proxmoxNode)
        nodepool = "core" if storage == "ssd" else "bulk"

        return [
            f"{LABEL_CLUSTER}={cluster_name}",
            f"{LABEL_ROLE}={node.role}",
            f"{LABEL_STORAGE}={storage}",
            f"{LABEL_NODEPOOL}={nodepool}",
            f"{LABEL_ZONE}={zone}",
        ]

    def write_config(node: NodeSpec, *, is_server: bool, server_url: str | None) -> pulumi.Output[str]:
        labels = node_label_kv(node)

        def render(token: str) -> str:
            yaml_lines: list[str] = []

            if is_server:
                yaml_lines += [
                    'write-kubeconfig-mode: "644"',
                    "disable:",
                    "  - traefik",
                    "  - local-storage",
                ]

            yaml_lines.append(f'token: "{token}"')
            if server_url:
                yaml_lines.append(f'server: "{server_url}"')

            yaml_lines.append("node-label:")
            yaml_lines += [f'  - "{lbl}"' for lbl in labels]

            return "\n".join(
                [
                    "set -euo pipefail",
                    "sudo mkdir -p /etc/rancher/k3s",
                    "sudo tee /etc/rancher/k3s/config.yaml >/dev/null <<'YAML'",
                    "\n".join(yaml_lines),
                    "YAML",
                ]
            )

        return pulumi.Output.all(k3s_token).apply(lambda xs: render(xs[0]))

    # 1) prereqs per node (depend only on that node's VM)
    prereq_by_node: dict[str, Command] = {}
    for n in nodes:
        host = ip_no_cidr(n.ip4)
        vm = vm_by_name.get(n.name)
        if vm is None:
            raise ValueError(f"vm_by_name is missing a VM resource for node {n.name!r}")

        prereq_by_node[n.name] = remote(
            f"{n.name}-prereqs",
            host=host,
            script="\n".join(
                [
                    "set -euo pipefail",
                    "sudo apt-get update -y",
                    "sudo apt-get install -y open-iscsi nfs-common",
                    "sudo systemctl enable --now iscsid || true",
                ]
            ),
            triggers=[n.name],
            depends_on=[vm],
        )

    # 2) primary server
    server1 = remote(
        f"{primary.name}-k3s-server",
        host=primary_ip,
        script=pulumi.Output.concat(
            write_config(primary, is_server=True, server_url=None),
            "\n",
            f'curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="{k3s_version}" sh -s - server\n',
        ),
        triggers=[primary.name, k3s_version],
        depends_on=[prereq_by_node[primary.name]],
    )

    # 3) additional servers
    for s in servers[1:]:
        host = ip_no_cidr(s.ip4)
        remote(
            f"{s.name}-k3s-server",
            host=host,
            script=pulumi.Output.concat(
                write_config(s, is_server=True, server_url=f"https://{primary_ip}:6443"),
                "\n",
                f'curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="{k3s_version}" sh -s - server\n',
            ),
            triggers=[s.name, host, k3s_version],
            depends_on=[prereq_by_node[s.name], server1],
        )

    # 4) workers
    for w in workers:
        host = ip_no_cidr(w.ip4)
        remote(
            f"{w.name}-k3s-agent",
            host=host,
            script=pulumi.Output.concat(
                write_config(w, is_server=False, server_url=f"https://{primary_ip}:6443"),
                "\n",
                f'curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="{k3s_version}" sh -s - agent\n',
            ),
            triggers=[w.name, host, k3s_version],
            depends_on=[prereq_by_node[w.name], server1],
        )

    component.register_outputs({})
    return component
