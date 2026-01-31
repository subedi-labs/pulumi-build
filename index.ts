import * as pulumi from "@pulumi/pulumi";
import * as proxmox from "@muhlba91/pulumi-proxmoxve";

/**
 * Configuration interface for a VM
 */
interface VMConfig {
    name: string;
    nodeName: string; // Proxmox host to deploy to
    vmId?: number; // Optional VM ID
    cpu: {
        cores: number;
        sockets: number;
    };
    memory: {
        dedicated: number; // MB
    };
    disk: {
        interface: string;
        datastoreId: string;
        size: number; // GB
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
            servers: string[];
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

/**
 * Pulumi program entrypoint
 */
async function main() {
    const config = new pulumi.Config();

    // Proxmox API credentials from Pulumi config
    // Set with:
    //   pulumi config set proxmox:endpoint https://<host>:8006/api2/json
    //   pulumi config set --secret proxmox:apiToken "USER@REALM!TOKENID=SECRET"
    const endpoint = config.require("proxmox:endpoint");
    const apiToken = config.requireSecret("proxmox:apiToken");
    const insecure = config.getBoolean("proxmox:insecure") ?? false;

    // Proxmox provider (API token auth)
    const provider = new proxmox.Provider("proxmoxve", {
        endpoint,
        apiToken,
        insecure,
    });

    // VM configurations from Pulumi.<stack>.yaml
    const vmConfigs: VMConfig[] = config.requireObject("vms");

    // Create VMs and capture outputs in a structured way
    const vmsByName: Record<
        string,
        {
            id: pulumi.Output<any>;
            name: pulumi.Output<string>;
            nodeName: string;
            requestedVmId?: number;
        }
    > = {};

    const vmIds: pulumi.Output<any>[] = [];

    for (const vmConfig of vmConfigs) {
        const vm = new proxmox.vm.VirtualMachine(
            vmConfig.name,
            {
                name: vmConfig.name,
                nodeName: vmConfig.nodeName,
                vmId: vmConfig.vmId,

                // CPU configuration
                cpu: {
                    cores: vmConfig.cpu.cores,
                    sockets: vmConfig.cpu.sockets,
                },

                // Memory configuration
                memory: {
                    dedicated: vmConfig.memory.dedicated,
                },

                // Disk configuration
                disks: [
                    {
                        interface: vmConfig.disk.interface,
                        datastoreId: vmConfig.disk.datastoreId,
                        size: vmConfig.disk.size,
                        fileFormat: vmConfig.disk.fileFormat ?? "qcow2",
                    },
                ],

                // Network configuration
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
                                servers: vmConfig.cloudInit.dns.servers,
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

                        // If sshKeys provided, create userAccount. (Optionally include password)
                        ...(vmConfig.cloudInit.sshKeys && {
                            userAccount: {
                                username: vmConfig.cloudInit.username ?? "root",
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
                    type: "l26", // Linux 2.6+ kernel
                },
            },
            {
                provider,
            }
        );

        vmIds.push(vm.id);

        // Collect outputs per VM
        vmsByName[vmConfig.name] = {
            id: vm.id,
            name: vm.name,
            nodeName: vmConfig.nodeName,
            requestedVmId: vmConfig.vmId,
        };
    }

    // Extra summary outputs (handy for automation / scripts)
    // Note: these are stack outputs in TypeScript via `export const ...` (NOT pulumi.export)
    return {
        totalVms: vmConfigs.length,
        vmsByName,
        vmIdList: pulumi.all(vmIds),
    };
}

// Run main and export stack outputs
const outputs = main();
export const totalVms = outputs.then((o) => o.totalVms);
export const vmsByName = outputs.then((o) => o.vmsByName);
export const vmIdList = outputs.then((o) => o.vmIdList);
