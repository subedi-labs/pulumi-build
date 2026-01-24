import pulumi
from pulumi_command.remote import Command, CommandArgs, ConnectionArgs
import pulumi_kubernetes as k8s

def make_k8s_provider_from_k3s(
    *,
    server_ip: str,
    ssh_user: str,
    ssh_private_key: pulumi.Output[str],
    depends_on: list[pulumi.Resource],
) -> k8s.Provider:
    get_kubeconfig = Command(
        "k3s-get-kubeconfig",
        CommandArgs(
            connection=ConnectionArgs(
                host=server_ip,
                user=ssh_user,
                private_key=ssh_private_key,
                port=22,
            ),
            create="\n".join([
                "set -euo pipefail",
                f'sudo cat /etc/rancher/k3s/k3s.yaml | sed "s/127.0.0.1/{server_ip}/"',
            ]),
            triggers=[server_ip],
        ),
        opts=pulumi.ResourceOptions(depends_on=depends_on),
    )

    return k8s.Provider("k8s", kubeconfig=get_kubeconfig.stdout)
