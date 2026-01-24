# pulumi-automate

Provision a small, long-running **K3s** cluster on **Proxmox** using **Pulumi (Python 3.12)**, then install **Longhorn** with replicas restricted to SSD-backed nodes.

This repo is designed for a modern homelab setup:
- **Pulumi ProxmoxVE provider** creates/clones VMs from a cloud-init template
- **Pulumi Command (remote SSH)** bootstraps K3s on those VMs
- **Pulumi Kubernetes** installs Longhorn via Helm
- Nodes are labeled at bootstrap so you can use affinity/selection later (see below for details)
- Proxmox auth uses a **Proxmox API token stored as a Pulumi secret** (no shell `export ...` required)

## What it creates

### Topology
- **proxmox1**: 1x K3s server + 1x K3s worker
- **proxmox2**: 1x K3s server + 1x K3s worker
- **proxmox3**: 1x K3s worker

### Storage policy
- Longhorn is installed on the cluster
- Longhorn default disks (and thus replicas) are created **only on SSD nodes**
  - You provide the SSD node names via `ssdNodeNames`

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

## Prerequisites

### local

* Python 3.12+
* Pulumi CLI
* SSH access to VMs (see next section)

### Proxmox
* cloud-init enabled VM template (Ubuntu recommended)
* Your __SSH public key baked into template__
    * Pulumi uses your private key to SSH in for bootstrap



### Proxmox Authentication

This repo uses Pulumi stack config for Proxmox connection info, and stores the API token as an encrypted Pulumi secret.

```bash
# 1. Select/init a stack
pulumi stack select dev
#or
pulumi stack init dev

# 2. Set proxmox config
pulumi config set proxmoxEndpoint "https://proxmox1:8006/"
pulumi config set proxmoxUsername "root@pam"
pulumi config set proxmoxInsecure true

# 4. Token (secret)
pulumi config set --secret proxmoxApiToken "USER@REALM!TOKENID=UUID"

# 5. Buff security
pulumi config set proxmoxMinTls "1.3"
```



### SSH (VM access + bootstrap)

#### Public key
- Must exist in your Proxmox template (cloud-init template)
- Pulumi does not push public keys

#### Private key
Pulumi uses your private key to SSH in for:
- bootstrapping K3s
- reading kubeconfig (for Kubernetes provider)

Set path to your private key:

```bash
pulumi config set pulumi-automate:sshPrivateKeyPath "~/.ssh/id_ed25519"
```



### K3s + Longhorn config

Set k3s version and token used for nodes to join the cluster:

```bash
pulumi config set pulumi-automate:k3sVersion "v1.33.3+k3s1"
pulumi config set --secret pulumi-automate:k3sToken "some-long-random-token"
```

### Example `Pulumi.dev.yaml`

Adjust VMIDs, IPs, datastores, and networks to match your homelab:

```yaml
config:
  # Proxmox Provider (recommended homelab modern setup)
  proxmoxEndpoint: "https://proxmox1:8006/"
  proxmoxUsername: "root@pam"
  proxmoxInsecure: true
  proxmoxApiToken:
    secure: "REDACTED"

  # SSH for bootstrap (public key is in template)
  pulumi-automate:sshUser: ubuntu
  pulumi-automate:sshPrivateKey:
    secure: "REDACTED"

  # K3s
  pulumi-automate:k3sVersion: "v1.33.3+k3s1"
  pulumi-automate:k3sToken:
    secure: "REDACTED"

  # Template
  pulumi-automate:template:
    nodeName: proxmox1
    vmId: 9000

  # SSD nodes (names must match NodeSpec.name)
  pulumi-automate:ssdNodeNames:
    - k3s-px1-server
    - k3s-px1-worker
    - k3s-px2-server
    - k3s-px2-worker

  pulumi-automate:longhornReplicaCount: 2
  pulumi-automate:longhornKubeletRootDir: "/var/lib/rancher/k3s/agent/kubelet"

  # Nodes
  pulumi-automate:nodes:
    - name: k3s-px1-server
      role: server
      proxmoxNode: proxmox1
      vmId: 101
      ip4: 10.10.0.101/24
      gw4: 10.10.0.1
      cores: 2
      memoryMb: 4096
      diskGb: 40
      datastoreId: local-lvm
      initDatastoreId: local-lvm
      bridge: vmbr0
      vlanId: 2

    - name: k3s-px1-worker
      role: worker
      proxmoxNode: proxmox1
      vmId: 102
      ip4: 10.10.0.102/24
      gw4: 10.10.0.1
      cores: 2
      memoryMb: 4096
      diskGb: 80
      datastoreId: local-lvm
      initDatastoreId: local-lvm
      bridge: vmbr0
      vlanId: 2

    - name: k3s-px2-server
      role: server
      proxmoxNode: proxmox2
      vmId: 201
      ip4: 10.10.0.201/24
      gw4: 10.10.0.1
      cores: 2
      memoryMb: 4096
      diskGb: 40
      datastoreId: local-lvm
      initDatastoreId: local-lvm
      bridge: vmbr0
      vlanId: 2

    - name: k3s-px2-worker
      role: worker
      proxmoxNode: proxmox2
      vmId: 202
      ip4: 10.10.0.202/24
      gw4: 10.10.0.1
      cores: 2
      memoryMb: 4096
      diskGb: 80
      datastoreId: local-lvm
      initDatastoreId: local-lvm
      bridge: vmbr0
      vlanId: 2

    - name: k3s-px3-worker
      role: worker
      proxmoxNode: proxmox3
      vmId: 301
      ip4: 10.10.0.301/24
      gw4: 10.10.0.1
      cores: 2
      memoryMb: 4096
      diskGb: 120
      datastoreId: hdd-store
      initDatastoreId: hdd-store
      bridge: vmbr0
      vlanId: 2
```

## Deployment

```bash
# Install deps
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create Infra
pulumi preview
pulumi up
```

### Outputs
After a successful run, Pulumi exports
- `stack`
- `kubeApiServer`
- `longhornNamespace`
- `ssdNodeNames`

### Node labels

Nodes labeled at bootstrap via k3s in `/etc/rancher/k3s/config.yaml`

Exmaples:
- `homelab.pukar.io/cluster=<stack>`
    - Tag for which Pulumi stack
- `homelab.pukar.io/role=server|worker`
- `homelab.pukar.io/storage=ssd|hdd`
- `homelab.pukar.io/nodepool=core|bulk`
    - groups nodes into pools (ssd=core vs hdd=bulk)
- `topology.kubernetes.io/zone=zone-a|zone-b|zone-c`
    - zone-a=proxmox1, zone-b=proxmox2, zone-c=proxmox3

### Longhorn SSD-only behavior

This repo labels SSD nodes with:
- `node.longhorn.io/create-default-disk=true`

sets:
- `defaultSettings.createDefaultDiskLabeledNodes=true`

So Longhorn creates default disks only on labeled nodes, effectively restricting replicas to SSD nodes when needed.

## Philosophy

`__main__.py` stays intentionally small and boring:
- load config
- create provider
- create VMs
- bootstrap K3s
- create k8s provider
- install Longhorn
- export outputs

if it grows move logic into modules/components, not the other way around.






<!-- ## Install Dependencies

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
``` -->

