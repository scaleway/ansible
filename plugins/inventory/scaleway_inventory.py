from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional, Any

from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable
from ansible.errors import AnsibleError

DOCUMENTATION =r"""

"""
EXAMPLES = r"""
plugin: scaleway.scaleway.scaleway
regions:
    - fr-par-2
    - nl-ams-1
tags:
    - dev
state:
    - stopped
"""
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

    ''' TO DO create a method to check_sdk '''



@dataclass
class _Host(ABC):
    """Abstract base host object with common fields and network handling."""

    id: str
    tags: list[str]
    zone: Zone
    state: ServerState
    hostname: str

    public_ipv4: list[str] = field(default_factory=list)
    private_ipv4: list[str] = field(default_factory=list)
    public_ipv6: list[str] = field(default_factory=list)
    private_ipv6: list[str] = field(default_factory=list)

    @abstractmethod
    def populate_network(self, server, client: Client) -> None:
        """Extract IPs/DNS from the Scaleway SDK object."""

    def _populate_private_network(self, client: Client, private_networks_id: list[str]) -> None:
        """Fetch private IPs from IPAM api."""
        ipam_api = IpamV1API(client=client)
        ips: list[IP] = [
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
    public_dns: list[str] = field(default_factory=list)

    def populate_network(self, server: DediboxServer, client: Client) -> None:
        for interface in server.interfaces or []:
            for ip in interface.ips or []:
                target_list_ip = self.public_ipv4 if ip.version == DediboxIPVersion.IPV4 else self.public_ipv6
                target_list_ip.append(ip.address)
                if ip.reverse:
                    self.public_dns.append(ip.reverse)

class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = "scaleway.scaleway.scaleway"
    _ALLOWED_FILE_NAME_SUFFIXES = (
        "scaleway.yaml",
        "scaleway.yml",
        "scw.yaml",
        "scw.yml",
    )

    def __init__(self):
        super().__init__()
        self.FILTERS_HOSTS = {}

    def _get_client(self):
        return Client.from_config_file_and_env(
            filepath=self.get_option("config_file") or os.getenv("SCW_CONFIG_FILE"),
            profile_name=self.get_option("profile") or os.getenv("SCW_PROFILE"),
        )

    def _check_sdk(self):
        if not HAS_SCALEWAY_SDK:
            raise AnsibleError(
                "Scaleway SDK is not installed. Please install the 'scaleway' Python package."
            )

    def _register_filter(self, name, func):
        self.FILTERS_HOSTS[name] = func

    def _apply_filters(self, hosts):
        """Apply all registered filters to the list of hosts."""
        for name, filter_func in self.FILTERS_HOSTS.items():
            options = self.get_option(name)  # Ansible auto-reads from inventory file
            if not options:
                continue
            if isinstance(options, str):
                options_list = [opt.strip() for opt in options.split(",")]
            elif isinstance(options, (list, tuple)):
                options_list = list(options)
            else:
                continue
            hosts = [h for h in hosts if filter_func(h, options_list)]
        return hosts


    def verify_file(self, path: str) -> bool:
        """ return true/false if this is possibly a valid file for this plugin to consume """
        ''' source: https://docs.ansible.com/ansible/latest/dev_guide/developing_inventory.html#verify-file-method '''
        valid = False
        if super(InventoryModule, self).verify_file(path):
            if path.endswith(self._ALLOWED_FILE_NAME_SUFFIXES):
                valid = True
        return valid

    def get_cached_result(self, path: str, cache: bool) -> tuple[bool, Optional[Any]]:
        if not cache:
            return False, None

        # user has not caching enabled
        if not self.get_option("cache"):
            return False, None

        cache_key = self.get_cache_key(path)
        try:
            cached_result = self._cache[cache_key]
        except KeyError: # no cache (expires or missing)
            return False, None
        return True, cached_result

    @staticmethod
    def _host_to_dict(host: _Host) -> dict[str, Any]:
        return asdict(host)

    @staticmethod
    def _get_instances(client: Client) -> list[_InstanceServerHost]:
        instance_api = InstanceV1API(client)
        servers = instance_api.list_servers_all()
        results: list[_InstanceServerHost] = []

        for server in servers:
            host = _InstanceServerHost(
                id=server.id,
                tags=server.tags or [],
                zone=server.zone,
                state=server.state,
                hostname=server.name,
            )
            host.populate_network(server, client)
            results.append(host)
        return results

    @staticmethod
    def _get_elastic_metal(client: Client) -> list[_ElasticMetalHost]:
        baremetal_api = BaremetalV1API(client)
        servers = baremetal_api.list_servers_all()
        results: list[_ElasticMetalHost] = []

        for server in servers:
            host = _ElasticMetalHost(
                id=server.id,
                tags=server.tags or [],
                zone=server.zone,
                state=server.state,
                hostname=server.name,
            )
            host.populate_network(server, client)
            results.append(host)
        return results

    @staticmethod
    def _get_apple_silicon(client: Client) -> list[_ApplesiliconHost]:
        applesilicon_api = ApplesiliconV1Alpha1API(client)
        servers = applesilicon_api.list_servers_all()
        results: list[_ApplesiliconHost] = []

        for server in servers:
            host = _ApplesiliconHost(
                id=server.id,
                tags=server.tags or [],
                zone=server.zone,
                state=server.state,
                hostname=server.name,
            )
            host.populate_network(server, client)
            results.append(host)
        return results

    @staticmethod
    def _get_dedibox(client: Client) -> list[_DediboxHost]:
        dedibox_api = DediboxV1API(client)
        servers = dedibox_api.list_servers_all()
        results: list[_DediboxHost] = []

        for server in servers:
            host = _DediboxHost(
                id=server.id,
                tags=server.tags or [],
                zone=server.zone,
                state=server.state,
                hostname=server.name,
            )
            host.populate_network(server, client)
            results.append(host)
        return results


    def get_inventory(self):
        client = self._get_client()

        instances: list[_InstanceServerHost] = self._get_instances(client)
        elastic_metals: list[_ElasticMetalHost] = self._get_elastic_metal(client)
        apple_silicon: list[_ApplesiliconHost] = self._get_apple_sillicon(client)
        dedibox: list[_DediboxHost] = self._get_dedibox(client)

        return instances + elastic_metals + apple_silicon + dedibox

    def parse(self, inventory, loader, path, cache=True):
        """ Parse a file into a dict """
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._read_config_data(path)  # Loads config + auto-loads cache plugin

        # Cache handling
        use_cached, cached_result = self.get_cached_result(path, cache)

        ## Filters management
        self._register_filter("regions", lambda h, regions: str(h.region) in regions)
        self._register_filter("tags", lambda h, tags: any(t in h.tags for t in tags))
        self._register_filter("state", lambda h, states: h.state in states)

        # Use cache
        if not use_cached:
            self.populate(cached_result)

        # Fetch fresh data
        try:
            all_hosts = self.get_inventory()
        except Exception as e:
            raise AnsibleError(f"Failed to query Scaleway API: {e}")

        # Update cache
        cache_key = self.get_cache_key(path)
        self._cache[cache_key] = [self._host_to_dict(h) for h in all_hosts]

        filtered_hosts = self._apply_filters(all_hosts)

        self.populate(filtered_hosts)














