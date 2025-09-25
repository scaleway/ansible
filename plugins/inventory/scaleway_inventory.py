from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

_ALLOWED_FILE_NAME_SUFFIXES = (
    "scaleway.yaml",
    "scaleway.yml",
    "scw.yaml",
    "scw.yml",
)

try:
    from scaleway_core.bridge import Zone
    from scaleway import Client, ScalewayException
    from scaleway.applesilicon.v1alpha1 import (
        ApplesiliconV1Alpha1API,
        ApplesiliconV1Alpha1PrivateNetworkAPI,
        ServerPrivateNetworkStatus,
        Server as ApplesiliconServer,
    )
    from scaleway.baremetal.v1 import (
        BaremetalV1API,
        BaremetalV1PrivateNetworkAPI,
        Server as BaremetalServer,
    )
    from scaleway.instance.v1 import (
        InstanceV1API,
        ServerState,
        ServerIpIpFamily,
        Server as InstanceServer,
    )
    from scaleway.dedibox.v1 import (
        DediboxV1API,
        IPVersion as DediboxIPVersion,
        ServerSummary as DediboxServer,
    )
    from scaleway.ipam.v1 import IpamV1API, IP

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False



@dataclass
class _Host(ABC):
    """Abstract base host object with common fields and network handling."""

    id: str
    tags: List[str]
    zone: Zone
    state: ServerState
    hostname: str

    public_ipv4: List[str] = field(default_factory=list)
    private_ipv4: List[str] = field(default_factory=list)
    public_ipv6: List[str] = field(default_factory=list)
    private_ipv6: List[str] = field(default_factory=list)

    @abstractmethod
    def populate_network(self, server, client: Client) -> None:
        """Extract IPs/DNS from the Scaleway SDK object."""

    def _populate_private_network(self, client: Client, private_networks_id: list[str]) -> None:
        """Fetch private IPs from IPAM api."""
        ipam_api = IpamV1API(client=client)
        ips: List[IP] = [
            ip
            for pn in private_networks_id
            for ip in ipam_api.list_i_ps_all(resource_id=pn.id, attached=True)
        ]

        self.private_ipv4.extend(ip.address.split("/")[0] for ip in ips if not ip.is_ipv6)
        self.private_ipv6.extend(ip.address.split("/")[0] for ip in ips if ip.is_ipv6)



# ---------------------------------------------------------------------------
# Product-specific subclasses
# ---------------------------------------------------------------------------

@dataclass
class _ApplesiliconHost(_Host):
    def populate_network(self, server: ApplesiliconServer, client: Client) -> None:
        if server.ip:
            self.public_ipv4.append(server.ip)

        if server.vpc_status == ServerPrivateNetworkStatus.VPC_DISABLED:
            return

        applesilicon_api = ApplesiliconV1Alpha1PrivateNetworkAPI(client=client)

        private_networks = applesilicon_api.list_server_private_networks_all(server_id=server.id)
        self._populate_private_network(client, private_networks)


@dataclass
class _InstanceServerHost(_Host):
    public_dns: Optional[str] = None
    private_dns: Optional[str] = None

    def populate_network(self, server: InstanceServer, client: Client) -> None:
        self.public_dns = f"{server.id}.pub.instances.scw.cloud"
        self.private_dns = f"{server.id}.priv.instances.scw.cloud"

        for ip in server.public_ips or []:
            if ip.family == ServerIpIpFamily.INET:
                self.public_ipv4.append(ip.address)
            else:
                self.public_ipv6.append(ip.address)

        self._populate_private_network(client, [pn.id for pn in server.private_nics])


@dataclass
class _ElasticMetalHost(_Host):
    def populate_network(self, server: BaremetalServer, client: Client) -> None:
        for ip in server.ips or []:
            target_list = self.public_ipv4 if ip.version.lower() == "ipv4" else self.public_ipv6
            target_list.append(ip.address)

        has_private_network = any(opt.name == "Private Network" for opt in server.options)
        if not has_private_network:
            return

        baremetal_pn_api = BaremetalV1PrivateNetworkAPI(client=client)

        private_networks = baremetal_pn_api.list_server_private_networks_all(server_id=server.id)
        self._populate_private_network(client, private_networks)


@dataclass
class _DediboxHost(_Host):
    public_dns: List[str] = field(default_factory=list)

    def populate_network(self, server: DediboxServer, client: Client) -> None:
        for interface in server.interfaces or []:
            for ip in interface.ips or []:
                target_list_ip = self.public_ipv4 if ip.version == DediboxIPVersion.IPV4 else self.public_ipv6
                target_list_ip.append(ip.address)
                if ip.reverse:
                    self.public_dns.append(ip.reverse)
