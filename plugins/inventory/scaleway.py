#-*- coding: utf-8 -*-

# Copyright: (c), Ansible Project
# Copyright: (c), Devtool's Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import ipaddress

DOCUMENTATION = r"""
name: scaleway
author:
    - Devtool's Team
short_description: Scaleway inventory source
version_added: "1.0.0"
requirements:
    - scaleway >= 2.9.0
description:
    - Scaleway inventory plugin.
    - Uses configuration file that ends with '(scaleway|scw).(yaml|yml)'.
extends_documentation_fragment:
    - scaleway.scaleway.scaleway
    - constructed
    - inventory_cache
options:
    plugin:
        description:
            - The name of the Scaleway Inventory Plugin, this should always be C(scaleway.scaleway.scaleway).
        required: true
        choices: ['scaleway.scaleway.scaleway']
    zones:
        description:
            - List of zones to filter on.
        type: list
        elements: str
        default:
            - fr-par-1
            - fr-par-2
            - fr-par-3
            - nl-ams-1
            - nl-ams-2
            - pl-waw-1
            - pl-waw-2
    tags:
        description:
            - List of tags to filter on.
        type: list
        elements: str
        default: []
    state:
        description:
            - Instance server status
        type: list
        elements: str
        default: [running]
    hostnames:
        description: A list in order of precedence for hostname variables.
        type: list
        elements: str
        default:
            - public_ipv4
        choices:
            - public_ipv4
            - private_ipv4
            - public_ipv6
            - hostname
            - id
    variables:
        description:
            - "Variables mapping to apply to hosts in the format destination_variable: host_variable."
            - "You can use the following host variables:"
            - "  - C(id): The server id."
            - "  - C(tags): The server tags."
            - "  - C(zone): The server zone."
            - "  - C(state): The server state."
            - "  - C(hostname): The server hostname."
            - "  - C(public_ipv4): The server public ipv4."
            - "  - C(private_ipv4): The server private ipv4."
            - "  - C(public_ipv6): The server public ipv6."
            - "  - C(public_dns): The server public dns."
            - "  - C(private_dns): The server private dns."
            - "If the variable is not found, the host will be ignored."
        type: dict
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
variables:
    ansible_host: public_ipv4
"""


import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional, Any

from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable
from ansible.errors import AnsibleError


try:
    from scaleway_core.bridge import Zone
    from scaleway import Client, ScalewayException
    from scaleway.flexibleip.v1alpha1 import FlexibleipV1Alpha1API
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
class Host(ABC):
    """Abstract base host object with common fields and network handling."""

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
    def populate_network(self, server, client: "Client") -> None:
        """Extract IPs/DNS from the Scaleway SDK object."""

    def _populate_private_network(self, client: "Client", private_networks_id: list[str]) -> None:
        """Fetch private IPs from IPAM api."""
        ipam_api = IpamV1API(client=client)
        ips: list[IP] = [
            ip
            for pn in private_networks_id
            for ip in ipam_api.list_i_ps_all(resource_id=pn.id, attached=True)
        ]

        self.private_ipv4.extend(ip.address.split("/")[0] for ip in ips if not ip.is_ipv6)
        self.private_ipv6.extend(ip.address.split("/")[0] for ip in ips if ip.is_ipv6)

    def _populate_flexible_ip(self, client: "Client", server: Any ) -> None:
        supported_types = ("InstanceServer", "BaremetalServer")
        if server.__class__.__name__ not in supported_types:
            return
        flexible_ip_api = FlexibleipV1Alpha1API(client=client)
        fips = flexible_ip_api.list_flexible_i_ps_all(zone=server.zone, server_ids=[server.id])
        for fip in fips:
            ip_address = fip.ip_address.split("/")[0]
            if self.get_ip_version(fip.ip_address) == "IPv6":
                getattr(self, "flexible_ipv6", []).append(ip_address)
                getattr(self, "public_flexible_dns_ipv6", []).append(fip.reverse)
            else:
                getattr(self, "flexible_ipv4", []).append(ip_address)
                getattr(self, "public_flexible_dns_ipv4", []).append(fip.reverse)



    def normalized_state(self) -> str:
        """Normalize server state into standard values."""
        mapping = {
            "running": "running",
            "ready": "running",
            "started": "running",
            "stopped": "stopped",
        }
        state_str = str(self.state).lower()
        return mapping.get(state_str, state_str)

    def get_ip_version(self, ip: str) -> str:
        """
        https://docs.python.org/3/library/ipaddress.html
        """
        try:
            parsed_ip = ipaddress.ip_network(ip)
            return "IPv4" if isinstance(parsed_ip, ipaddress.IPv4Network) else "IPv6"
        except ValueError:
            return "Invalid"



# ---------------------------------------------------------------------------
# Product-specific subclasses
# ---------------------------------------------------------------------------

@dataclass
class ApplesiliconHost(Host):
    def populate_network(self, server: "ApplesiliconServer", client: "Client") -> None:
        if server.ip:
            self.public_ipv4.append(server.ip)

        if server.vpc_status == ServerPrivateNetworkStatus.VPC_DISABLED:
            return

        applesilicon_api = ApplesiliconV1Alpha1PrivateNetworkAPI(client=client)

        private_networks = applesilicon_api.list_server_private_networks_all(server_id=server.id)
        self._populate_private_network(client, [pn.id for pn in private_networks])


@dataclass
class InstanceServerHost(Host):
    public_dns: Optional[str] = None
    private_dns: Optional[str] = None
    flexible_ipv4: list[str] = field(default_factory=list)
    flexible_ipv6: list[str] = field(default_factory=list)
    public_flexible_dns_ipv4: list[str] = field(default_factory=list)
    public_flexible_dns_ipv6: list[str] = field(default_factory=list)


    def populate_network(self, server: "InstanceServer", client: "Client") -> None:
        self.public_dns = f"{server.id}.pub.instances.scw.cloud"
        self.private_dns = f"{server.id}.priv.instances.scw.cloud"

        for ip in server.public_ips or []:
            if ip.family == ServerIpIpFamily.INET:
                self.public_ipv4.append(ip.address)
            else:
                self.public_ipv6.append(ip.address)

        self._populate_private_network(client, [pn.id for pn in server.private_nics])
        self._populate_flexible_ip(client, server)

@dataclass
class ElasticMetalHost(Host):
    flexible_ipv4: list[str] = field(default_factory=list)
    flexible_ipv6: list[str] = field(default_factory=list)
    public_flexible_dns_ipv4: list[str] = field(default_factory=list)
    public_flexible_dns_ipv6: list[str] = field(default_factory=list)

    def populate_network(self, server: "BaremetalServer", client: "Client") -> None:
        if server.ips is None:
            return
        for ip in server.ips:
            target_list = self.public_ipv4 if ip.version.lower() == "ipv4" else self.public_ipv6
            target_list.append(ip.address)

        has_private_network = any(opt.name == "Private Network" for opt in server.options)
        if not has_private_network:
            return

        baremetal_pn_api = BaremetalV1PrivateNetworkAPI(client=client)

        private_networks = baremetal_pn_api.list_server_private_networks_all(server_id=server.id)
        self._populate_private_network(client, [pn.id for pn in private_networks])
        self._populate_flexible_ip(client, server)


@dataclass
class DediboxHost(Host):
    public_dns: list[str] = field(default_factory=list)
    failover_ipv4: list[str] = field(default_factory=list)
    failover_ipv6: list[str] = field(default_factory=list)
    failover_dns_ipv4: list[str] = field(default_factory=list)
    failover_dns_ipv6: list[str] = field(default_factory=list)

    def populate_network(self, server: "DediboxServer", client: "Client") -> None:
        for interface in server.interfaces or []:
            for ip in interface.ips or []:
                target_list_ip = self.public_ipv4 if ip.version == DediboxIPVersion.IPV4 else self.public_ipv6
                target_list_ip.append(ip.address)
                if ip.reverse:
                    self.public_dns.append(ip.reverse)
        dedibox_api = DediboxV1API(client=client)
        failover_ips = dedibox_api.list_failover_i_ps_all(zone=server.zone)
        for failover_ip in failover_ips:
            if failover_ip.server_id != server.id:
                continue
            ip_target_list = self.failover_ipv4 if failover_ip.ip_version == DediboxIPVersion.IPV4 else self.failover_ipv6
            dns_target_list = self.failover_dns_ipv4 if failover_ip.ip_version == DediboxIPVersion.IPV4 else self.failover_dns_ipv6
            ip_target_list.append(failover_ip.address)
            dns_target_list.append(failover_ip.reverse)


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

    def verify_file(self, path: str) -> bool:
        """ return true/false if this is possibly a valid file for this plugin to consume """
        ''' source: https://docs.ansible.com/ansible/latest/dev_guide/developing_inventory.html#verify-file-method '''
        valid = False
        if super(InventoryModule, self).verify_file(path):
            if path.endswith(self._ALLOWED_FILE_NAME_SUFFIXES):
                valid = True
        self.display.vvv(
            "Skipping due to inventory source file name mismatch. "
            "The file name has to end with one of the following: "
            f"{', '.join(self._ALLOWED_FILE_NAME_SUFFIXES)}."
        )
        return valid

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
            options = self.get_option(name)# Ansible auto-reads from inventory file
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
    def _host_to_dict(host: Host) -> dict[str, Any]:
        return asdict(host)

    def _list_servers_safe(self, api, zone):
        try:
            return api.list_servers_all(zone=zone)
        except ScalewayException as e:
            msg = str(e).lower()
            # Skip zones where service is not available
            if "unknown service" in msg or "not_found" in msg or "404" in msg:
                self.display.vvv(f"Skipping {api.__class__.__name__} in {zone}: {e}")
                return []
            raise e

    def _get_instances(self, client: "Client") -> list[InstanceServerHost]:
        instance_api = InstanceV1API(client)
        servers: list[InstanceServer] = []
        zones = self.get_option("zones")
        for zone in zones:
            servers.extend(instance_api.list_servers_all(zone=zone))
        results: list[InstanceServerHost] = []

        for server in servers:
            host = InstanceServerHost(
                id=server.id,
                tags= ["instance"] + server.tags,
                zone=server.zone,
                state=server.state,
                hostname=server.name,
            )
            host.populate_network(server, client)
            results.append(host)
        return results

    def _get_elastic_metal(self, client: "Client") -> list[ElasticMetalHost]:
        baremetal_api = BaremetalV1API(client)
        servers: list[BaremetalServer] = []
        zones = self.get_option("zones")
        for zone in zones:
            servers.extend(self._list_servers_safe(baremetal_api, zone))

        results: list[ElasticMetalHost] = []

        for server in servers:
            host = ElasticMetalHost(
                id=server.id,
                tags=["elasticmetal"] + server.tags,
                zone=server.zone,
                state=server.status,
                hostname=server.name,
            )
            host.populate_network(server, client)
            results.append(host)
        return results

    def _get_apple_silicon(self, client: "Client") -> list[ApplesiliconHost]:
        api = ApplesiliconV1Alpha1API(client)
        servers = []
        for zone in self.get_option("zones"):
            servers.extend(self._list_servers_safe(api, zone))

        results: list[ApplesiliconHost] = []
        for server in servers:
            host = ApplesiliconHost(
                id=server.id,
                tags=["applesilicon"] + server.tags,
                zone=server.zone,
                state=server.status,
                hostname=server.name,
            )
            host.populate_network(server, client)
            results.append(host)
        return results

    def _get_dedibox(self, client: "Client") -> list[DediboxHost]:
        dedibox_api = DediboxV1API(client)
        servers: list[DediboxServer] = []
        zones = self.get_option("zones")
        for zone in zones:
            servers.extend(self._list_servers_safe(dedibox_api, zone))

        results: list[DediboxHost] = []

        for server in servers:
            host = DediboxHost(
                id=str(server.id),
                tags=["dedibox"],
                zone=server.zone,
                state=server.status,
                hostname=server.hostname,
            )
            host.populate_network(server, client)
            results.append(host)

        return results

    @staticmethod
    def _get_host_attribute(host: Host, host_attributes: list[str]):
        host_as_dict = host.__dict__

        for host_attribute in host_attributes:
            if host_attribute in host_as_dict and host_as_dict[host_attribute]:
                value = host_as_dict[host_attribute]
                # If list, return as-is (we’ll handle in populate)
                if isinstance(value, list):
                    return value
                return str(value)
        raise AnsibleError(f"{host.id} has no attribute {host_attributes}")


    def get_host_groups(self, host: Host):
        return set(self.sanitize_tag(tag) for tag in host.tags).union(
            {self.sanitize_tag(host.zone)}
        )

    def sanitize_tag(self, tag: str):
        forbidden_characters = [
            "-",
            " ",
            ":",
        ]
        for forbidden_character in forbidden_characters:
            tag = tag.strip().replace(forbidden_character, "_")

        return tag

    def populate(self, all_hosts: list[Host]):
        host_attributes = self.get_option("hostnames")
        print("value of get_options(hostname): ", host_attributes)
        variables = self.get_option("variables") or {}
        print("value of get_options(variable): ", variables)

        for host in all_hosts:
            groups = self.get_host_groups(host)
            try:
                hostname_value = self._get_host_attribute(host, host_attributes)
                print("value of _get_host_attribute(host, host_attributes): ", hostname_value)
            except AnsibleError as e:
                self.display.warning(f"Skipping host {host.id}: {e}")
                continue

            # If the hostname attribute is a list, create a host for each element
            hostnames = hostname_value if isinstance(hostname_value, list) else [hostname_value]
            print("value of hostnames: ", hostnames)

            for idx, hostname in enumerate(hostnames):
                # Ensure hostname is a string and unique if multiple
                print("vale of idx and hostnames: ", idx, hostname)
                if isinstance(hostname, list):
                    self.display.warning(f"Skipping host {host.id}: nested lists are not supported.")
                    continue

                unique_hostname = f"{hostname}" if len(hostnames) > 1 else str(hostname)

                self.inventory.add_host(host=unique_hostname)

                for variable, source in variables.items():
                    value = getattr(host, source, None)
                    # If the variable is a list, pick the corresponding element
                    if isinstance(value, list) and len(value) > idx:
                        value_to_set = value[idx]
                    elif isinstance(value, list):
                        value_to_set = value[0]  # fallback if list shorter than index
                    else:
                        value_to_set = value

                    if not value_to_set:
                        self.display.warning(
                            f"Skipping host {host.id}: Field {source} is not available."
                        )
                        # Remove host safely
                        host_obj = self.inventory.get_host(unique_hostname)
                        if host_obj:
                            self.inventory.remove_host(host_obj)
                        break

                    self.inventory.set_variable(unique_hostname, variable, value_to_set)
                else:
                    for group in groups:
                        self.inventory.add_group(group=group)
                        self.inventory.add_child(group=group, child=unique_hostname)


    def get_inventory(self):
        client = self._get_client()

        instances: list[InstanceServerHost] = self._get_instances(client)
        elastic_metals: list[ElasticMetalHost] = self._get_elastic_metal(client)
        apple_silicon: list[ApplesiliconHost] = self._get_apple_silicon(client)
        dedibox: list[DediboxHost] = self._get_dedibox(client)

        return instances + elastic_metals + apple_silicon + dedibox

    def parse(self, inventory, loader, path, cache=True):
        """ Parse a file into a dict """
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._read_config_data(path)  # Loads config + auto-loads cache plugin
        self._check_sdk()

        self.load_cache_plugin()
        # Cache handling
        use_cached, cached_result = self.get_cached_result(path, cache)

        ## Filters management
        self._register_filter(
            "tags",
            lambda h, tags: any(t in h.tags for t in tags))
        self._register_filter(
            "state",
            lambda h, states: h.normalized_state() in [s.lower() for s in states]
        )

        # Use cache
        if not use_cached and cached_result:
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














