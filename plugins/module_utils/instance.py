from dataclasses import dataclass
from typing import Dict, Optional

try:
    from scaleway import Client
    from scaleway.instance.v1 import Server as InstanceServer
    from scaleway.ipam.v1 import IpamV1API
except ImportError:
    HAS_SCALEWAY_SDK = False


@dataclass
class VpcIp:
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None


def get_instance_private_ips(
    client: "Client", servers: list["InstanceServer"]
) -> Dict[str, VpcIp]:
    """
    return a mapping of first found vpc IPs with the instance
    """
    ipam_api = IpamV1API(client)

    vpc_ips = {}

    for server in servers:
        vpc_ip = VpcIp()
        vpc_ips[server.id] = vpc_ip
        for pnic in server.private_nics:
            for ip in ipam_api.list_i_ps_all(resource_id=pnic.id):
                if ip.is_ipv6:
                    vpc_ip.ipv6 = ip.address.split("/")[0]
                else:
                    vpc_ip.ipv4 = ip.address.split("/")[0]

    return vpc_ips
