# Proxmox VM Deployment with Pulumi

A modern, production-ready Pulumi project for deploying and managing Virtual Machines on Proxmox VE using TypeScript. This project follows Pulumi best practices and uses API token authentication for secure, automated deployments.

## Features

- ✅ **API Token Authentication** - Secure authentication using Proxmox API tokens (no username/password)
- ✅ **Multi-Host Support** - Deploy VMs across multiple Proxmox hosts
- ✅ **Flexible VM Configuration** - Unique configuration for each VM
- ✅ **Secrets Management** - Sensitive data stored securely in Pulumi config (not in state)
- ✅ **Cloud-Init Support** - Automated VM initialization with network and SSH configuration
- ✅ **Type Safety** - Full TypeScript type checking
- ✅ **Modern Structure** - Follows latest Pulumi best practices

## Prerequisites

- [Node.js](https://nodejs.org/) >= 18.0.0
- [Pulumi CLI](https://www.pulumi.com/docs/get-started/install/) >= 3.0.0
- Proxmox VE 7.0 or later
- A Proxmox API token (see setup instructions below)

## Project Structure

```
.
├── index.ts                # Main Pulumi program
├── Pulumi.yaml            # Project configuration
├── Pulumi.dev.yaml        # Development stack configuration (example)
├── package.json           # Node.js dependencies
├── tsconfig.json          # TypeScript configuration
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Installation

### 1. Install Dependencies

```bash
npm install
```

### 2. Create a Proxmox API Token

On your Proxmox server:

1. Navigate to **Datacenter → Permissions → API Tokens**
2. Click **Add**
3. Select a user (e.g., `root@pam`)
4. Enter a Token ID (e.g., `pulumi`)
5. Uncheck "Privilege Separation" if you want the token to have full user privileges
6. Click **Add**
7. **Important**: Copy the displayed secret immediately - it won't be shown again!

The token format will be: `USER@REALM!TOKENID=SECRET`

Example: `root@pam!pulumi=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

### 3. Initialize Pulumi Stack

```bash
# Login to Pulumi (or use self-hosted backend)
pulumi login

# Create a new stack (e.g., 'dev', 'staging', 'prod')
pulumi stack init homelab
```

### 4. Configure Pulumi

Set your Proxmox connection details:

```bash
# Set Proxmox endpoint
pulumi config set proxmox:endpoint "https://your-proxmox-host:8006"

# Set API token as a secret (will be encrypted)
pulumi config set --secret proxmox:apiToken "root@pam!pulumi=your-secret-token"

# Optional: Skip TLS verification (for self-signed certificates)
pulumi config set proxmox:insecure true
```

### 5. Configure Your VMs

Edit `Pulumi.dev.yaml` (or create `Pulumi.<your-stack>.yaml`) to define your VMs:

```yaml
config:
  proxmox:endpoint: https://proxmox.example.com:8006
  proxmox:insecure: false
  
  vms:
    - name: my-vm
      nodeName: pve1          # Proxmox host
      vmId: 100               # Optional
      cpu:
        cores: 2
        sockets: 1
      memory:
        dedicated: 4096       # MB
      disk:
        interface: scsi0
        datastoreId: local-lvm
        size: 32              # GB
      network:
        bridge: vmbr0
        model: virtio
      clone:                  # Optional: clone from template
        nodeName: pve1
        vmId: 9000
        full: true
      cloudInit:              # Optional: cloud-init configuration
        datastoreId: local-lvm
        ipv4:
          address: 192.168.1.100/24
          gateway: 192.168.1.1
        sshKeys:
          - "ssh-rsa AAAAB3N... your-key"
```

## Usage

### Deploy VMs

```bash
# Preview changes
pulumi preview

# Deploy infrastructure
pulumi up
```

### Update Configuration

1. Modify your `Pulumi.<stack>.yaml` file
2. Run `pulumi up` to apply changes

### Destroy VMs

```bash
# Destroy all resources
pulumi destroy
```

### View Stack Outputs

```bash
# List all stack outputs
pulumi stack output

# Get specific VM ID
pulumi stack output vm-web-server-01-id
```

## Configuration Reference

### Proxmox Provider Configuration

| Config Key | Type | Required | Description |
|------------|------|----------|-------------|
| `proxmox:endpoint` | string | Yes | Proxmox API endpoint (https://host:8006) |
| `proxmox:apiToken` | secret | Yes | API token (USER@REALM!TOKENID=SECRET) |
| `proxmox:insecure` | boolean | No | Skip TLS verification (default: false) |

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

## Security Best Practices

1. **Never commit secrets** - API tokens are stored encrypted in Pulumi config
2. **Use API tokens** - More secure than username/password
3. **Principle of least privilege** - Create Proxmox users/tokens with only required permissions
4. **Enable TLS verification** - Set `proxmox:insecure: false` in production
5. **Use separate stacks** - Different stacks for dev/staging/prod environments

## Advanced Usage

### Using Pulumi ESC (Environments, Secrets, and Configuration)

For better secrets management across projects:

```bash
# Create an ESC environment
pulumi env init my-org/proxmox-prod

# Set values in ESC
pulumi env set my-org/proxmox-prod proxmox.endpoint "https://proxmox.example.com:8006"
pulumi env set my-org/proxmox-prod proxmox.apiToken --secret "root@pam!pulumi=xxx"

# Import in your stack
pulumi config env add my-org/proxmox-prod
```

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

### API Token Issues

**Problem**: "no such token" error

**Solution**: Ensure token format is correct: `USER@REALM!TOKENID=SECRET`

```bash
# Correct format
pulumi config set --secret proxmox:apiToken "root@pam!pulumi=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### TLS Certificate Errors

**Problem**: SSL certificate verification failed

**Solution**: Either add proper certificates or temporarily skip verification:

```bash
pulumi config set proxmox:insecure true
```

### VM ID Conflicts

**Problem**: VM ID already exists

**Solution**: Either:
- Remove `vmId` to let Proxmox auto-assign
- Use a different VM ID
- Delete the existing VM

### Permission Errors

**Problem**: "Permission check failed"

**Solution**: Ensure your API token has required permissions:

```bash
# On Proxmox server
pveum acl modify / -token 'root@pam!pulumi' -role Administrator
```

