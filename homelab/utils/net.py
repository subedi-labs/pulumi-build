def ip_no_cidr(ip_with_cidr: str) -> str:
    return ip_with_cidr.split("/")[0]
