# Proxmox VM Deployment with Pulumi (TypeScript + Pulumi ESC)

A modern Pulumi project for deploying and managing Virtual Machines on Proxmox VE using TypeScript.  
This project utilizes Pulumi ESC (Environments, Secrets, and Configuration) for keeping sensitive values out of repo config.

## Features

- ✅ **API Token Authentication** - Secure authentication using Proxmox API tokens (no username/password)
- ✅ **Pulumi ESC for secrets**
- ✅ **Multi-Host Support** — deploy VMs across multiple Proxmox nodes
- ✅ **Flexible VM Configuration** — unique configuration per VM via stack YAML
- ✅ **Cloud-Init Support** — automate network + SSH + user setup
- ✅ **Type Safety** — TypeScript types and validation patterns


## Prerequisites

- Node.js >= 18
- Pulumi CLI >= 3
- Proxmox VE 7+
- Proxmox API token


## Project Structure

```
.
├── index.ts                 # Main Pulumi program
├── Pulumi.yaml              # Project config
├── Pulumi.dev.yaml          # Dev stack config - usually NOT committed
├── Pulumi.prod.yaml         # Prod stack config - commit only if appropriate
├── Pulumi.example.yaml      # Example/template config
├── package.json             # Node.js dependencies
├── tsconfig.json            # TypeScript configuration
├── .gitignore
└── README.md
```


## 1) Install Dependencies

```bash
npm install
```


## 2) Create a Proxmox API Token

On your Proxmox server:

1. Datacenter → Permissions → API Tokens → Add
2. Select user (e.g., `root@pam`)
3. Enter Token ID (e.g., `pulumi`)
4. Uncheck "Privilege Separation" if you want the token to have full user privileges → Add
5. Copy secret (it won't be shown again)

Token format: `USER@REALM!TOKENID=SECRET`

Example: `root@pam!pulumi=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

## 3) Initialize Stack and Attach ESC

From the project directory:

```bash
pulumi login
pulumi stack init prod
pulumi config env add subedi-labs/proxmox-prod
```

Verify ESC is attached:

```bash
pulumi config env ls
```

## 4) Create and Configure Pulumi ESC

Standard naming convention: `<org>/<env>` 

example: `subedi-labs/proxmox-prod`


Create it (once):

```bash
pulumi env init subedi-labs/proxmox-prod
```

Set configs in ESC.

```bash
pulumi env set subedi-labs/proxmox-prod "proxmox:endpoint" "https://YOUR_PROXMOX_HOST:8006"
pulumi env set subedi-labs/proxmox-prod "proxmox:insecure" true
pulumi env set subedi-labs/proxmox-prod "proxmox:apiToken" --secret "root@pam!pulumi=YOUR_SECRET"
```


## 5) VM definitions per stack

Create stack YAML files to define your `vms:` list.  

Example: `Pulumi.prod.yaml`

```yaml
config:
  vms:
    # VM 1 - Cloned from template
    - name: server-01
      nodeName: proxmox1    # Proxmox host name
      vmId: 100   # Optional: specific VM ID
      cpu: 
        cores: 1 
        sockets: 1
      memory: 
        dedicated: 1000
      disk:
        interface: scsi0
        datastoreId: local-lvm
        size: 20
        fileFormat: qcow2
      network:
        bridge: vmbr0
        model: virtio
      clone:
        nodeName: pve1
        vmId: 9000    # Template VM ID
        full: true
      cloudInit:
        datastoreId: local-lvm
        dns:
          domain: example.com
          server: 10.0.0.1,8.8.8.8
        ipv4:
          address: 10.0.0.100/24
          gateway: 10.0.0.1
        sshKeys:
          - "ssh-rsa AAAA...your-public-key"
        username: admin

    # VM 2 - Different host, different configuration
    - name: server-02
      nodeName: pve2
      vmId: 101
      cpu:
        cores: 1
        sockets: 1
      memory:
        dedicated: 1000
      disk:
        interface: scsi0
        datastoreId: local-lvm
        size: 20
      network:
        bridge: vmbr0
        model: virtio
      clone:
        nodeName: pve2
        vmId: 9000
        full: true
      cloudInit:
        datastoreId: local-lvm
        dns:
          domain: example.com
          server: 10.0.0.1,8.8.8.8
        ipv4:
          address: 10.0.0.101/24
          gateway: 10.0.0.1
        sshKeys:
          - "ssh-rsa AAAAB3NzaC1yc2E... your-key-here"
        username: admin

    # VM 3 - Another VM on first host
    - name: worker-01
      nodeName: pve1
      vmId: 102
      cpu:
        cores: 1
        sockets: 1
      memory:
        dedicated: 2048
      disk:
        interface: scsi0
        datastoreId: local-lvm
        size: 20
      network:
        bridge: vmbr0
        model: virtio
      clone:
        nodeName: pve1
        vmId: 9000
        full: true
      cloudInit:
        datastoreId: local-lvm
        ipv4:
          address: 10.0.0.102/24
          gateway: 10.0.0.1
        sshKeys:
          - "ssh-rsa AAAAB3NzaC1yc2E... your-key-here"
```

## Usage

### Deploy

```bash
pulumi stack select prod
pulumi preview
pulumi up
```

### Update

1. Edit `Pulumi.<stack>.yaml` (VM definitions)
2. Run:

```bash
pulumi up
```

### Destroy

```bash
pulumi destroy
```

### Stack Outputs

```bash
pulumi stack output
# Get specific VM ID
pulumi stack output worker-01
```

## Configuration Reference

### VM Configuration

Each VM in the `vms` array supports:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | VM name |
| `nodeName` | string | Yes | Proxmox host to deploy to |
| `vmId` | number | No | Specific VM ID |
| `cpu.cores` | number | Yes | Number of CPU cores |
| `cpu.sockets` | number | Yes | Number of CPU sockets |
| `memory.dedicated` | number | Yes | Memory in MB |
| `disk.interface` | string | Yes | Disk interface (e.g., scsi0) |
| `disk.datastoreId` | string | Yes | Storage datastore |
| `disk.size` | number | Yes | Disk size in GB |
| `disk.fileFormat` | string | No | Disk format (default: qcow2) |
| `network.bridge` | string | Yes | Network bridge (e.g., vmbr0) |
| `network.model` | string | Yes | Network model (e.g., virtio) |
| `clone` | object | No | Clone from template VM |
| `cloudInit` | object | No | Cloud-init configuration |

## Advanced Usage

### Multiple Proxmox Providers

To deploy to multiple Proxmox clusters:

```typescript
const provider1 = new proxmox.Provider("proxmox-dc1", {
  endpoint: config.require("proxmox1:endpoint"),
  apiToken: config.requireSecret("proxmox1:apiToken"),
});

const provider2 = new proxmox.Provider("proxmox-dc2", {
  endpoint: config.require("proxmox2:endpoint"),
  apiToken: config.requireSecret("proxmox2:apiToken"),
});
```

### Organizing Multiple VMs

For large deployments, consider extracting VM configurations to separate files:

```typescript
// vm-configs.ts
export const webServers: VMConfig[] = [/* ... */];
export const dbServers: VMConfig[] = [/* ... */];

// index.ts
import { webServers, dbServers } from './vm-configs';
const allVMs = [...webServers, ...dbServers];
```

## Troubleshooting

### Permission Errors

**Problem**: "Permission check failed"

**Solution**: Ensure your API token has required permissions:

```bash
# On Proxmox server
pveum acl modify / -token 'root@pam!pulumi' -role Administrator
```