# pulumi_automate/constants.py

# Your label namespace (good practice to avoid collisions)
LABEL_PREFIX = "homelab.pukar.io"

# Vendor-neutral labels (capabilities + topology)
LABEL_CLUSTER = f"{LABEL_PREFIX}/cluster"
LABEL_ROLE = f"{LABEL_PREFIX}/role"
LABEL_STORAGE = f"{LABEL_PREFIX}/storage"
LABEL_NODEPOOL = f"{LABEL_PREFIX}/nodepool"

# Kubernetes standard topology label
LABEL_ZONE = "topology.kubernetes.io/zone"

# Map your hypervisor hosts -> vendor-neutral zones
ZONE_MAP = {
    "proxmox1": "zone-a",
    "proxmox2": "zone-b",
    "proxmox3": "zone-c",
}

# Longhorn constants
LONGHORN_NAMESPACE = "longhorn-system"
LONGHORN_DISK_LABEL = "node.longhorn.io/create-default-disk"
