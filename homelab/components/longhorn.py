import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Release, ReleaseArgs, RepositoryOptsArgs

from .constants import LONGHORN_DISK_LABEL

def install_longhorn(
    *,
    provider: k8s.Provider,
    namespace: str,
    replica_count: int,
    kubelet_root_dir: str,
    ssd_node_names: list[str],
) -> None:
    ns = k8s.core.v1.Namespace(
        namespace,
        metadata={"name": namespace},
        opts=pulumi.ResourceOptions(provider=provider),
    )

    patches = [
        k8s.core.v1.NodePatch(
            f"label-{node_name}-longhorn-disk",
            metadata={
                "name": node_name,
                "labels": {LONGHORN_DISK_LABEL: "true"},
            },
            opts=pulumi.ResourceOptions(provider=provider),
        )
        for node_name in ssd_node_names
    ]

    Release(
        "longhorn",
        ReleaseArgs(
            chart="longhorn",
            namespace=ns.metadata["name"],
            repository_opts=RepositoryOptsArgs(repo="https://charts.longhorn.io"),
            values={
                "defaultSettings": {
                    "createDefaultDiskLabeledNodes": "true",
                    "defaultReplicaCount": str(replica_count),
                },
                "persistence": {"defaultClassReplicaCount": replica_count},
                "csi": {"kubeletRootDir": kubelet_root_dir},
            },
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[ns, *patches]),
    )
