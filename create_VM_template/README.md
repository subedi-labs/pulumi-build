# Proxmox Cloud-Init Template Helper (Python)

This script creates a **cloud-init enabled Ubuntu VM template** on a Proxmox host by running the standard `qm` workflow:
- download an Ubuntu cloud image (qcow2 `.img`)
- `qm create` a VM shell
- `qm importdisk` the image
- attach it as `scsi0` + set boot order
- add a Proxmox cloud-init drive (`ide2: <storage>:cloudinit`)
- enable serial console + QEMU guest agent
- optionally set `ciuser`, `sshkeys`, `ipconfig0`, resize disk
- convert the VM into a **template**

This follows Proxmox’s documented Cloud-Init template flow. :contentReference[oaicite:0]{index=0}

## Requirements

Run this **on a Proxmox node** with:
- root access (`sudo -i` or `sudo ...`)
- `qm` available (Proxmox installed)
- `wget` installed

## Usage

> Recommended to scp `create_cloudinit_template.py` to each host and run it with root.

### Dry run (recommended)
Prints every command it would execute without changing anything:

```bash
sudo ./create_proxmox_cloudinit_template.py \
  --vmid 9000 \
  --name ubuntu-24.04-cloudinit-template \
  --storage local-lvm \
  --bridge vmbr0 \
  --ciuser ubuntu \
  --sshkeys /root/.ssh/authorized_keys \
  --ipconfig dhcp \
  --disk-resize 32G \
  --dry-run
```

### Create template

Remove `--dry-run`:

### flags
- `--vmid` (required): VMID for the template, e.g. 9000
- `--storage`: target storage for the VM disk + cloud-init drive (e.g. local-lvm, ssd-zfs)
- `--bridge`: network bridge, e.g. vmbr0
- `--sshkeys`: path to a public key file (or authorized_keys) to bake into cloud-init
- `--ipconfig`: dhcp or a static config like ip=10.10.0.50/24,gw=10.10.0.1
- `--disk-resize`: resize scsi0 (example: 32G)
- `--vlan`: VLAN tag for net0 (0 = none)
- `--image-url`: override the Ubuntu cloud image download URL
- `--image-path`: use an already-downloaded image file instead of downloading

### Nuances

- VMID must exist, --vmid fails if already used. (9000+ is common)
- Proxmox typically names the disk: `<storage>:vm-<vmid>-disk-0`
- The script enables the Proxmox-side guest agent (--agent enabled=1).
For full functionality, the guest OS should have qemu-guest-agent installed.
Some Ubuntu cloud images include it; some don’t.
- `--ipconfig dhcp` sets `ipconfig0 ip=dhcp` to set static the Proxmox format style is `ip=.../cidr,gw=...`

### What you get

After it completes, you’ll have a Proxmox template VM suitable for fast cloning via Pulumi/Proxmox. Default VMID: `999` and name: `ubuntu-2404-template`

Verify in Proxmox UI:
- VM shows a cloud-init drive
- VM is marked as Template