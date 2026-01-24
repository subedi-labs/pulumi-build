from __future__ import annotations

import pulumi
import pulumi_proxmoxve as proxmoxve


def create_proxmox_provider() -> proxmoxve.Provider:
    """
    Create a Proxmox VE provider using Pulumi stack config.

    Config keys (in Pulumi.<stack>.yaml via `pulumi config set ...`):
      - proxmoxEndpoint (required)  e.g. https://proxmox1:8006/
      - proxmoxUsername (required)  e.g. root@pam or pulumi@pve
      - proxmoxApiToken (required, secret)  e.g. USER@REALM!TOKENID=UUID
      - proxmoxInsecure (optional, default true)
      - proxmoxMinTls (optional, default 1.3)  allowed: 1.0|1.1|1.2|1.3
    """
    cfg = pulumi.Config()

    endpoint = cfg.require("proxmoxEndpoint")
    username = cfg.require("proxmoxUsername")

    # Stored encrypted in the stack config/state
    api_token = cfg.require_secret("proxmoxApiToken")

    insecure = cfg.get_bool("proxmoxInsecure")
    if insecure is None:
        insecure = True  # sane homelab default (self-signed certs)

    min_tls = cfg.get("proxmoxMinTls") or "1.3"

    return proxmoxve.Provider(
        "proxmoxve",
        endpoint=endpoint,
        username=username,
        api_token=api_token,
        insecure=insecure,
        min_tls=min_tls,
    )
