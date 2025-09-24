from dataclasses import field, dataclass
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from scaleway.k8s.v1.tests.test_k8s_sk import private_network

_ALLOWED_FILE_NAME_SUFFIXES = (
    "scaleway.yaml",
    "scaleway.yml",
    "scw.yaml",
    "scw.yml",
)

try:
    from scaleway_core.bridge import Zone
    from scaleway import Client, ScalewayException
    from scaleway.applesilicon.v1alpha1 import ApplesiliconV1Alpha1API, ApplesiliconV1Alpha1PrivateNetworkAPI, \
    ServerPrivateNetworkStatus
    from scaleway.applesilicon.v1alpha1 import Server as ApplesiliconServer
    from scaleway.baremetal.v1 import BaremetalV1API, IPVersion as BaremetalIPVersion, IPVersion, \
    BaremetalV1PrivateNetworkAPI
    from scaleway.baremetal.v1 import Server as BaremetalServer
    from scaleway.instance.v1 import InstanceV1API, ServerState
    from scaleway.instance.v1 import Server as InstanceServer
    from scaleway.dedibox.v1 import DediboxV1API, IPVersion as DediboxIPVersion
    from scaleway.dedibox.v1 import ServerSummary as DediboxServer
    from scaleway.ipam.v1 import IpamV1API, IP

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False

@dataclass
class _Host(ABC):
    id: str
    tags: list[str]
    zone: "Zone"
    state: "ServerState"

    hostname: str
    public_ipv4: list[str] = field(default_factory=list)
    private_ipv4: list[str] = field(default_factory=list)
    public_ipv6: list[str] = field(default_factory=list)
    private_ipv6: list[str] = field(default_factory=list)

    @abstractmethod
    def populate_network(self, server, api):
        ...
    """Extract IPs/DNS from the Scaleway SDK object."""


@dataclass
class _ApplesiliconHost(_Host):
    def populate_network(self, server: "ApplesiliconServer", client: "Client") -> None:
        if server.ip:
            self.public_ipv4.append(server.ip)
        if server.vpc_status == ServerPrivateNetworkStatus.VPC_DISABLED:
            return

        applesilicon_api = ApplesiliconV1Alpha1PrivateNetworkAPI(client=client)
        ipam_api = IpamV1API(client=client)

        private_networks = applesilicon_api.list_server_private_networks_all(server_id=server.id)

        ips: List[IP] = [
            ip
            for pn in private_networks
            for ip in ipam_api.list_i_ps_all(resource_id=pn.id, attached=True)
        ]

        self.private_ipv4.extend(ip.address.split("/")[0] for ip in ips if not ip.is_ipv6)
        self.private_ipv6.extend(ip.address.split("/")[0] for ip in ips if ip.is_ipv6)

@dataclass
class _InstanceServerHost(_Host):
    public_dns: str | None = None
    private_dns: str | None = None
    def populate_network(self, server: "InstanceServer", client: "Client") -> None:
        self.public_dns = f"{server.id}.pub.instances.scw.cloud"
        self.private_dns = f"{server.id}.priv.instances.scw.cloud"
        if server.public_ips:
            for ip in server.public_ips:
                if ip.family == "ipv4":
                    self.public_ipv4.append(ip.address)
                else:
                    self.public_ipv6.append(ip.address)

        ipam_api = IpamV1API(client=client)

        ips: List[IP] = [
            ip
            for pn in server.private_nics
            for ip in ipam_api.list_i_ps_all(resource_id=pn.id, attached=True)
        ]

        self.private_ipv4.extend(ip.address.split("/")[0] for ip in ips if not ip.is_ipv6)
        self.private_ipv6.extend(ip.address.split("/")[0] for ip in ips if ip.is_ipv6)


class _ElasticMetalHost(_Host):
    def populate_network(self, server: "BaremetalServer", client: "Client") -> None:
        for ip in server.ips or []:
            target_list = self.public_ipv4 if ip.version.lower() == "ipv4" else self.public_ipv6
            target_list.append(ip.address)

        baremetal_pn_api = BaremetalV1PrivateNetworkAPI(client=client)
        private_networks = baremetal_pn_api.list_server_private_networks_all(server_id=server.id)
        ipam_api = IpamV1API(client=client)
        ips: List[IP] = [
            ip
            for pn in private_networks
            for ip in ipam_api.list_i_ps_all(resource_id=pn.id, attached=True)
        ]

        self.private_ipv4.extend(ip.address.split("/")[0] for ip in ips if not ip.is_ipv6)
        self.private_ipv6.extend(ip.address.split("/")[0] for ip in ips if ip.is_ipv6)











