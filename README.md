# pulumi-automate

Provision a small, long-running **K3s** cluster on **Proxmox** using **Pulumi (Python 3.12)**, then install **Longhorn** with replicas restricted to SSD-backed nodes.

This repo is designed for a modern homelab setup:
- **Pulumi ProxmoxVE provider** creates/clones VMs from a cloud-init template
- **Pulumi Command (remote SSH)** bootstraps K3s on those VMs
- **Pulumi Kubernetes** installs Longhorn via Helm
- Nodes are labeled at bootstrap so you can use affinity/selection later
    - `homelab.pukar.io/cluster=<cluster_name>`
    - `homelab.pukar.io/role=<role>` | server or worker
    - `homelab.pukar.io/storage=<storage_type>` | ssd or hdd
    - `homelab.pukar.io/nodepool=<nodepool>` | core if ssd, bulk if hdd
- Proxmox auth uses a **Proxmox API token stored as a Pulumi secret** (no shell `export ...` required)

---

## What it creates

### Topology
- **proxmox1**: 1x K3s server + 1x K3s worker
- **proxmox2**: 1x K3s server + 1x K3s worker
- **proxmox3**: 1x K3s worker

### Storage policy
- Longhorn is installed on the cluster
- Longhorn default disks (and thus replicas) are created **only on SSD nodes**
  - You provide the SSD node names via `ssdNodeNames`

---

## Repo structure

```text
pulumi-automate/
  __main__.py                    # tiny orchestration "story"
  Pulumi.yaml
  Pulumi.<stack>.yaml            # per-stack config (nodes/template/etc.)
  requirements.txt
  README.md

  pulumi_automate/
    constants.py                   # label keys, zone mapping, longhorn constants

    components/
      k3s.py                       # SSH bootstrap K3s + node labels + prereqs
      longhorn.py                  # install Longhorn + label SSD nodes for disks

    config/
      models.py                    # dataclasses/types
      load.py                      # reads Pulumi config and validates

    providers/
      kubernetes.py                # build k8s Provider from kubeconfig over SSH
      proxmox.py                   # Proxmox provider + VM creation

    utils/
      net.py                       # small helpers
```

`__main__.py` stays intentionally small:
1. load config
2. create proxmox provider
3. create VMs
4. bootstrap k3s
5. create k8s provider
6. install longhorn
7. export outputs

---

## Prerequisites

### local

* Python 3.12+
* Pulumi CLI
* SSH access to VMs (see next section)

### Proxmox
* cloud-init enabled VM template (Ubuntu recommended)
* Your __SSH public key baked into template__
    * Pulumi uses your private key to SSH in for bootstrap

---

## Authentication

---

## Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Pulumi stack setup

```bash
# Create/select a stack
pulumi stack init dev
# or
pulumi stack select dev
```

