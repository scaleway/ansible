from dataclasses import dataclass
from typing import Dict, Optional

try:
    from scaleway import Client
    from scaleway.instance.v1 import Server as InstanceServer
    from scaleway.ipam.v1 import IpamV1API
    from scaleway.vpc.v2 import VpcV2API
except ImportError:
    HAS_SCALEWAY_SDK = False


@dataclass
class VpcIps:
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None


def get_instance_private_ips(
    client: "Client", servers: list["InstanceServer"]
) -> Dict[str, VpcIps]:
    """
    return a mapping of first found vpc IPs with the instance
    """
    vpc_api = VpcV2API(client)
    ipam_api = IpamV1API(client)

    vpc_ips = {}

    for server in servers:
        for pnic in server.private_nics:
            server_pn = vpc_api.get_private_network(
                private_network_id=pnic.private_network_id
            )
            vpc_ips[server.id] = VpcIps

            for ip in ipam_api.list_i_ps(vpc_id=server_pn.vpc_id).ips:
                if ip.is_ipv6:
                    vpc_ips[server.id].ipv6 = ip.address.split("/")[0]
                else:
                    vpc_ips[server.id].ipv4 = ip.address.split("/")[0]

    return vpc_ips
