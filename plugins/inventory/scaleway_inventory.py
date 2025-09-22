from dataclasses import field, dataclass
from abc import ABC, abstractmethod

_ALLOWED_FILE_NAME_SUFFIXES = (
    "scaleway.yaml",
    "scaleway.yml",
    "scw.yaml",
    "scw.yml",
)

try:
    from scaleway_core.bridge import Zone
    from scaleway import Client, ScalewayException
    from scaleway.applesilicon.v1alpha1 import ApplesiliconV1Alpha1API
    from scaleway.applesilicon.v1alpha1 import Server as ApplesiliconServer
    from scaleway.baremetal.v1 import BaremetalV1API, IPVersion as BaremetalIPVersion
    from scaleway.baremetal.v1 import Server as BaremetalServer
    from scaleway.instance.v1 import InstanceV1API, ServerState
    from scaleway.instance.v1 import Server as InstanceServer
    from scaleway.dedibox.v1 import DediboxV1API, IPVersion as DediboxIPVersion
    from scaleway.dedibox.v1 import ServerSummary as DediboxServer

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

    @abstractmethod
    def populate_network(self, server, api):
        ...
    """Extract IPs/DNS from the Scaleway SDK object."""

@dataclass
class _InstanceHost(_Host):
    public_dns: str | None = None
    private_dns: str | None = None

    def populate_network(self, server: "InstanceServer", api: "InstanceV1API"):
        if server.public_ip:
            self.public_ipv4.append(server.public_ip.address)
        if server.private_ip:
            self.private_ipv4.append(server.private_ip)
        if server.ipv6:
            self.public_ipv6.append(server.ipv6.address)

        # DNS
        self.public_dns = f"{server.id}.pub.instances.scw.cloud"
        self.private_dns = f"{server.id}.priv.instances.scw.cloud"


@dataclass
class _ApplesiliconHost(_Host):
    def populate_network(self, server: "ApplesiliconServer", api: "ApplesiliconV1Alpha1API"):



