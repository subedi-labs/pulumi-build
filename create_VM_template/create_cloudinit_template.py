#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_IMAGE_URL = "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
DEFAULT_ISO_DIR = Path("/var/lib/vz/template/iso")


def run(cmd: list[str], *, dry_run: bool) -> None:
    print("+", " ".join(cmd))
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def require_root() -> None:
    if os.geteuid() != 0:
        raise SystemExit("This script must be run as root (on a Proxmox host). Try: sudo -i")


def require_cmd(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"Missing required command: {name!r}. Install it and try again.")


def vm_exists(vmid: int, *, dry_run: bool) -> bool:
    # If dry-run, assume it does not exist to print the full plan.
    if dry_run:
        return False
    res = subprocess.run(["qm", "status", str(vmid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return res.returncode == 0


def download_image(url: str, dest: Path, *, dry_run: bool) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"Image already exists: {dest} (skipping download)")
        return
    run(["wget", "-O", str(dest), url], dry_run=dry_run)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a Proxmox cloud-init enabled Ubuntu VM template (downloads image, imports disk, sets cloud-init, converts to template)."
    )
    parser.add_argument("--vmid", type=int, required=True, help="Template VMID (e.g. 9000)")
    parser.add_argument("--name", default="ubuntu-cloudinit-template", help="Template VM name")
    parser.add_argument("--storage", default="local-lvm", help="Target storage for disks (e.g. local-lvm, zfs-ssd)")
    parser.add_argument("--bridge", default="vmbr0", help="Proxmox bridge (e.g. vmbr0)")
    parser.add_argument("--cores", type=int, default=2)
    parser.add_argument("--memory", type=int, default=2048, help="Memory in MB")
    parser.add_argument("--image-url", default=DEFAULT_IMAGE_URL, help="Ubuntu cloud image URL (qcow2 .img)")
    parser.add_argument("--image-path", default="", help="Local path to image file (skip download if set)")
    parser.add_argument("--iso-dir", default=str(DEFAULT_ISO_DIR), help="Where to store downloaded images")
    parser.add_argument("--disk-resize", default="", help='Optional resize, e.g. "32G" (applies to scsi0)')
    parser.add_argument("--ciuser", default="ubuntu", help="cloud-init user (ciuser)")
    parser.add_argument("--sshkeys", default="", help="Path to a public key file (or authorized_keys) to bake into template via cloud-init")
    parser.add_argument("--ipconfig", default="dhcp", help='Cloud-init ipconfig0 value (e.g. "dhcp" or "ip=10.0.0.10/24,gw=10.0.0.1")')
    parser.add_argument("--vlan", type=int, default=0, help="Optional VLAN tag for net0 (0 = none)")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    args = parser.parse_args()

    require_root()
    require_cmd("qm")
    require_cmd("wget")

    if vm_exists(args.vmid, dry_run=args.dry_run):
        raise SystemExit(f"VMID {args.vmid} already exists. Choose another VMID or delete the existing VM/template.")

    # Determine image path
    if args.image_path:
        image_path = Path(args.image_path).expanduser()
        if not image_path.exists():
            raise SystemExit(f"--image-path does not exist: {image_path}")
    else:
        iso_dir = Path(args.iso_dir)
        image_path = iso_dir / Path(DEFAULT_IMAGE_URL).name
        download_image(args.image_url, image_path, dry_run=args.dry_run)

    # 1) Create VM shell
    net0 = f"virtio,bridge={args.bridge}"
    if args.vlan and args.vlan > 0:
        net0 += f",tag={args.vlan}"

    run(
        [
            "qm",
            "create",
            str(args.vmid),
            "--name",
            args.name,
            "--memory",
            str(args.memory),
            "--cores",
            str(args.cores),
            "--net0",
            net0,
            "--ostype",
            "l26",
        ],
        dry_run=args.dry_run,
    )

    # 2) Import disk
    run(["qm", "importdisk", str(args.vmid), str(image_path), args.storage], dry_run=args.dry_run)

    # 3) Attach imported disk as scsi0 + boot from it
    # Proxmox typically names it vm-<vmid>-disk-0 after import.
    imported_disk_ref = f"{args.storage}:vm-{args.vmid}-disk-0"
    run(["qm", "set", str(args.vmid), "--scsihw", "virtio-scsi-pci", "--scsi0", imported_disk_ref], dry_run=args.dry_run)
    run(["qm", "set", str(args.vmid), "--boot", "order=scsi0"], dry_run=args.dry_run)

    # 4) Add cloud-init drive
    run(["qm", "set", str(args.vmid), "--ide2", f"{args.storage}:cloudinit"], dry_run=args.dry_run)

    # 5) Nice defaults: serial console + guest agent
    run(["qm", "set", str(args.vmid), "--serial0", "socket", "--vga", "serial0"], dry_run=args.dry_run)
    run(["qm", "set", str(args.vmid), "--agent", "enabled=1"], dry_run=args.dry_run)

    # 6) Cloud-init settings
    if args.ciuser:
        run(["qm", "set", str(args.vmid), "--ciuser", args.ciuser], dry_run=args.dry_run)
    if args.sshkeys:
        sshkeys_path = str(Path(args.sshkeys).expanduser())
        run(["qm", "set", str(args.vmid), "--sshkeys", sshkeys_path], dry_run=args.dry_run)
    if args.ipconfig:
        # Proxmox expects e.g. "ipconfig0 ip=dhcp" or "ip=...,gw=..."
        value = args.ipconfig
        if value.strip().lower() == "dhcp":
            value = "ip=dhcp"
        run(["qm", "set", str(args.vmid), "--ipconfig0", value], dry_run=args.dry_run)

    # 7) Optional disk resize
    if args.disk_resize:
        run(["qm", "resize", str(args.vmid), "scsi0", args.disk_resize], dry_run=args.dry_run)

    # 8) Convert to template
    run(["qm", "template", str(args.vmid)], dry_run=args.dry_run)

    print("\n✅ Done. Template created.")
    print(f"   VMID: {args.vmid}")
    print(f"   Name: {args.name}")
    print(f"   Storage: {args.storage}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Command failed with exit code {e.returncode}", file=sys.stderr)
        raise
