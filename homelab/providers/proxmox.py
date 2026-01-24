import os

import pulumi
import pulumi_proxmoxve as proxmox

from config.models import NodeSpec, TemplateSpec


def _env_bool(name: str) -> bool:
    v = os.environ.get(name, "").strip().lower()
    if v in ("1", "true", "yes", "y", "on"):
        return True
    if v in ("0", "false", "no", "n", "off"):
        return False
    raise ValueError(f"{name} must be a boolean-like string (true/false). Got: {os.environ.get(name)!r}")


def create_proxmox_provider() -> proxmox.Provider:
    endpoint = os.environ.get("PROXMOX_VE_ENDPOINT")
    username = os.environ.get("PROXMOX_VE_USERNAME")
    password = os.environ.get("PROXMOX_VE_PASSWORD")
    insecure = os.environ.get("PROXMOX_VE_INSECURE")

    if not endpoint or not username or not password or insecure is None:
        raise ValueError(
            "Missing env vars: PROXMOX_VE_ENDPOINT, PROXMOX_VE_USERNAME, PROXMOX_VE_PASSWORD, PROXMOX_VE_INSECURE"
        )

    return proxmox.Provider(
        "proxmoxve",
        endpoint=endpoint,
        username=username,
        password=password,
        insecure=_env_bool("PROXMOX_VE_INSECURE"),
    )


def create_vm(
    *,
    node: NodeSpec,
    template: TemplateSpec,
    ssh_user: str,
    provider: proxmox.Provider,
) -> proxmox.vm.VirtualMachine:
    """
    Clone a Proxmox VM from a template and configure cloud-init networking.

    Best practice (simplicity):
      - SSH public keys live in the template (cloud-init template).
      - Pulumi does not manage SSH key distribution.
    """
    return proxmox.vm.VirtualMachine(
        resource_name=node.name,
        node_name=node.proxmoxNode,
        vm_id=node.vmId,
        name=node.name,
        on_boot=True,
        tags=["pulumi", "k3s", node.role],
        description=f"Managed by Pulumi (pulumi-automate). Role={node.role}.",

        agent=proxmox.vm.VirtualMachineAgentArgs(
            enabled=True,
            type="virtio",
            trim=True,
            wait_for_ip=proxmox.vm.VirtualMachineAgentWaitForIpArgs(ipv4=True),
        ),

        cpu=proxmox.vm.VirtualMachineCpuArgs(cores=node.cores, sockets=1),
        memory=proxmox.vm.VirtualMachineMemoryArgs(dedicated=node.memoryMb),
        operating_system=proxmox.vm.VirtualMachineOperatingSystemArgs(type="l26"),

        clone=proxmox.vm.VirtualMachineCloneArgs(
            node_name=template.nodeName,
            vm_id=template.vmId,
            full=True,
        ),

        disks=[
            proxmox.vm.VirtualMachineDiskArgs(
                interface="scsi0",
                datastore_id=node.datastoreId,
                size=node.diskGb,
                file_format="qcow2",
            )
        ],

        network_devices=[
            proxmox.vm.VirtualMachineNetworkDeviceArgs(
                bridge=node.bridge,
                model="virtio",
                vlan_id=node.vlanId,
            )
        ],

        initialization=proxmox.vm.VirtualMachineInitializationArgs(
            type="nocloud",
            datastore_id=node.initDatastoreId,
            ip_configs=[
                proxmox.vm.VirtualMachineInitializationIpConfigArgs(
                    ipv4=proxmox.vm.VirtualMachineInitializationIpConfigIpv4Args(
                        address=node.ip4,
                        gateway=node.gw4,
                    )
                )
            ],
            user_account=proxmox.vm.VirtualMachineInitializationUserAccountArgs(
                username=ssh_user
            ),
        ),

        opts=pulumi.ResourceOptions(provider=provider),
    )
