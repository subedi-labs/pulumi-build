import * as pulumi from "@pulumi/pulumi";
import * as proxmox from "@muhlba91/pulumi-proxmoxve";


interface VMConfig {
    name: string;
    nodeName: string;  // Proxmox host to deploy to
    vmId?: number;     // Optional VM ID
    cpu: {
        cores: number;
        sockets: number;
    };
    memory: {
        dedicated: number;  // MB
    };
    disk: {
        interface: string;
        datastoreId: string;
        size: number;       // GB
        fileFormat?: string;
    };
    network: {
        bridge: string;
        model: string;
    };
    clone?: {
        nodeName: string;
        vmId: number;
        full: boolean;
    };
    cloudInit?: {
        datastoreId: string;
        dns?: {
            domain: string;
            server: string;
        };
        ipv4?: {
            address: string;
            gateway: string;
        };
        sshKeys?: string[];
        username?: string;
        password?: string;
    };
}



async function main() {
    const config = new pulumi.Config();

    const endpoint = config.require("proxmox:endpoint");
    const apiToken = config.requireSecret("proxmox:apiToken");
    const insecure = config.getBoolean("proxmox:insecure") ?? false;
    const provider = new proxmox.Provider("proxmoxve", {
        endpoint: endpoint,
        apiToken: apiToken,
        insecure: insecure,
    });

    // Get VM configurations from Pulumi.<stack>.yaml
    const vmConfigs: VMConfig[] = config.requireObject("vms");

    // Create VMs based on configuration
    const vms: pulumi.Output<any>[] = [];

    for (const vmConfig of vmConfigs) {
        const vm = new proxmox.vm.VirtualMachine(
            vmConfig.name,
            {
                name: vmConfig.name,
                nodeName: vmConfig.nodeName,
                vmId: vmConfig.vmId,

                cpu: {
                    cores: vmConfig.cpu.cores,
                    sockets: vmConfig.cpu.sockets,
                },

                memory: {
                    dedicated: vmConfig.memory.dedicated,
                },

                disks: [
                    {
                        interface: vmConfig.disk.interface,
                        datastoreId: vmConfig.disk.datastoreId,
                        size: vmConfig.disk.size,
                        fileFormat: vmConfig.disk.fileFormat || "qcow2",
                    },
                ],

                networkDevices: [
                    {
                        bridge: vmConfig.network.bridge,
                        model: vmConfig.network.model,
                    },
                ],

                // Clone configuration (if provided)
                ...(vmConfig.clone && {
                    clone: {
                        nodeName: vmConfig.clone.nodeName,
                        vmId: vmConfig.clone.vmId,
                        full: vmConfig.clone.full,
                    },
                }),

                // Cloud-init configuration (if provided)
                ...(vmConfig.cloudInit && {
                    initialization: {
                        type: "nocloud",
                        datastoreId: vmConfig.cloudInit.datastoreId,
                        ...(vmConfig.cloudInit.dns && {
                            dns: {
                                domain: vmConfig.cloudInit.dns.domain,
                                server: vmConfig.cloudInit.dns.server,
                            },
                        }),
                        ...(vmConfig.cloudInit.ipv4 && {
                            ipConfigs: [
                                {
                                    ipv4: {
                                        address: vmConfig.cloudInit.ipv4.address,
                                        gateway: vmConfig.cloudInit.ipv4.gateway,
                                    },
                                },
                            ],
                        }),
                        ...(vmConfig.cloudInit.sshKeys && {
                            userAccount: {
                                username: vmConfig.cloudInit.username || "root",
                                keys: vmConfig.cloudInit.sshKeys,
                                ...(vmConfig.cloudInit.password && {
                                    password: vmConfig.cloudInit.password,
                                }),
                            },
                        }),
                    },
                }),

                // Additional settings
                bios: "seabios",
                onBoot: true,
                agent: {
                    enabled: true,
                    trim: true,
                    type: "virtio",
                },
                operatingSystem: {
                    type: "l26",  // Linux 2.6+ kernel
                },
            },
            {
                provider: provider,
            }
        );

        vms.push(vm.id);

        // Export VM information
        pulumi.export(`vm-${vmConfig.name}-id`, vm.id);
        pulumi.export(`vm-${vmConfig.name}-name`, vm.name);
    }

    // Export summary
    pulumi.export("total-vms", vms.length);
}

main();
