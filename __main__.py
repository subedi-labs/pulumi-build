import pulumi

from homelab.config.load import load_config
from homelab.providers.proxmox import create_proxmox_provider, create_vm
from homelab.components.k3s import bootstrap_k3s
from homelab.providers.kubernetes import make_k8s_provider_from_k3s
from homelab.components.longhorn import install_longhorn
from homelab.labels.constants import LONGHORN_NAMESPACE

# 1) load config
cfg = load_config()

# 2) create proxmox provider
proxmox_provider = create_proxmox_provider()

# 3) create VMs
vms = [
    create_vm(
        node=n,
        template=cfg.template,
        ssh_user=cfg.ssh_user,
        provider=proxmox_provider,
    )
    for n in cfg.nodes
]
vm_by_name = {n.name: vm for n, vm in zip(cfg.nodes, vms)}

# 4) bootstrap k3s
k3s_bootstrap = bootstrap_k3s(
    nodes=cfg.nodes,
    vm_by_name=vm_by_name,
    ssh_user=cfg.ssh_user,
    ssh_private_key=cfg.ssh_private_key,
    k3s_version=cfg.k3s_version,
    k3s_token=cfg.k3s_token,
    ssd_node_names=cfg.longhorn.ssd_node_names,
    cluster_name=cfg.stack,
)

# 5) create k8s provider
k8s_provider = make_k8s_provider_from_k3s(
    server_ip=cfg.primary_server_ip,
    ssh_user=cfg.ssh_user,
    ssh_private_key=cfg.ssh_private_key,
    depends_on=[k3s_bootstrap],
)

# 6) install longhorn
install_longhorn(
    provider=k8s_provider,
    namespace=LONGHORN_NAMESPACE,
    replica_count=cfg.longhorn.replica_count,
    kubelet_root_dir=cfg.longhorn.kubelet_root_dir,
    ssd_node_names=cfg.longhorn.ssd_node_names,
)

# 7) export outputs
pulumi.export("stack", cfg.stack)
pulumi.export("kubeApiServer", f"https://{cfg.primary_server_ip}:6443")
pulumi.export("longhornNamespace", LONGHORN_NAMESPACE)
pulumi.export("ssdNodeNames", cfg.longhorn.ssd_node_names)
