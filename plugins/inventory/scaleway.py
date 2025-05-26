# -*- coding: utf-8 -*-

# Copyright: (c), Ansible Project
# Copyright: (c), Nathanael Demacon (@quantumsheep)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
name: scaleway
author:
    - Nathanael Demacon (@quantumsheep)
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
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import List

from ansible.errors import AnsibleError
from ansible.module_utils.basic import missing_required_lib
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable

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

_ALLOWED_FILE_NAME_SUFFIXES = (
    "scaleway.yaml",
    "scaleway.yml",
    "scw.yaml",
    "scw.yml",
)


@dataclass
class _Filters:
    zones: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    state: List[str] = field(default_factory=list)


@dataclass
class _Host:
    id: str
    tags: List[str]
    zone: "Zone"
    state: "ServerState"

    hostname: str
    public_ipv4: list[str] = field(default_factory=list)
    private_ipv4: list[str] = field(default_factory=list)
    public_ipv6: list[str] = field(default_factory=list)

    # Instances-only
    public_dns: str | None = None
    private_dns: str | None = None


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = "scaleway.scaleway.scaleway"

    def verify_file(self, path: str):
        if not super(InventoryModule, self).verify_file(path):
            return False

        if not path.endswith(_ALLOWED_FILE_NAME_SUFFIXES):
            self.display.vvv(
                "Skipping due to inventory source file name mismatch. "
                "The file name has to end with one of the following: "
                f"{', '.join(_ALLOWED_FILE_NAME_SUFFIXES)}."
            )

            return False

        return True

    def parse(self, inventory, loader, path: str, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._read_config_data(path)

        self.load_cache_plugin()
        cache_key = self.get_cache_key(path)

        if not HAS_SCALEWAY_SDK:
            self.display.error(missing_required_lib("scaleway"))
            raise AnsibleError(missing_required_lib("scaleway"))

        user_cache_setting = self.get_option("cache")

        use_cache = user_cache_setting and cache
        update_cache = user_cache_setting and not cache

        if use_cache:
            try:
                all_hosts = self._cache[cache_key]
            except KeyError:
                update_cache = True

        if not use_cache or update_cache:
            all_hosts = self.get_inventory()

        if update_cache:
            self._cache[cache_key] = all_hosts

        self.populate(all_hosts)

    def populate(self, all_hosts: List[_Host]):
        host_attributes = self.get_option("hostnames")
        variables = self.get_option("variables") or {}

        for host in all_hosts:
            groups = self.get_host_groups(host)

            try:
                hostname = self._get_host_attribute(host, host_attributes)
            except AnsibleError as e:
                self.display.warning(f"Skipping host {host.id}: {e}")
                continue

            self.inventory.add_host(host=hostname)

            should_skip = False
            for variable, source in variables.items():
                value = getattr(host, source, None)
                if not value:
                    self.display.warning(
                        f"Skipping host {host.id}: Field {source} is not available."
                    )
                    self.inventory.remove_host(SimpleNamespace(name=hostname))
                    should_skip = True
                    break

                self.inventory.set_variable(hostname, variable, value)

            if should_skip:
                continue

            for group in groups:
                self.inventory.add_group(group=group)
                self.inventory.add_child(group=group, child=hostname)

    def get_host_groups(self, host: _Host):
        return set(self.sanitize_tag(tag) for tag in host.tags).union(
            set([self.sanitize_tag(host.zone)])
        )

    def sanitize_tag(self, tag: str):
        forbidden_characters = [
            "-",
            " ",
        ]
        for forbidden_character in forbidden_characters:
            tag = tag.strip().replace(forbidden_character, "_")

        return tag

    def get_inventory(self):
        client = self._get_client()
        filters = self._get_filters()

        instances: List[InstanceServer] = self._get_instances(client, filters)
        elastic_metals: List[BaremetalServer] = self._get_elastic_metal(client, filters)
        apple_silicon: List[ApplesiliconServer] = self._get_apple_sillicon(
            client, filters
        )

        return instances + elastic_metals + apple_silicon

    def _get_instances(self, client: "Client", filters: _Filters) -> List[_Host]:
        api = InstanceV1API(client)

        servers: List[InstanceServer] = []

        for zone in filters.zones:
            for state in filters.state:
                servers.extend(
                    api.list_servers_all(
                        zone=zone,
                        tags=filters.tags if filters.tags else None,
                        state=ServerState(state),
                    )
                )

        results: List[_Host] = []
        for server in servers:
            host = _Host(
                id=server.id,
                tags=["instance", *server.tags],
                zone=server.zone,
                state=str(server.state),
                hostname=server.hostname,
                public_ipv4=[server.public_ip.address] if server.public_ip else [],
                private_ipv4=[server.private_ip.address] if server.private_ip else [],
                public_ipv6=[server.ipv6.address] if server.ipv6 else [],
                public_dns=f"{server.id}.pub.instances.scw.cloud",
                private_dns=f"{server.id}.priv.instances.scw.cloud",
            )
            results.append(host)

        return results

    def _get_elastic_metal(self, client: "Client", filters: _Filters) -> List[_Host]:
        api = BaremetalV1API(client)

        servers: List[BaremetalServer] = []

        for zone in filters.zones:
            try:
                found = api.list_servers_all(
                    zone=zone,
                    tags=filters.tags if filters.tags else None,
                )

                servers.extend(found)
            except ScalewayException:
                pass

        results: List[_Host] = []
        for server in servers:
            host = _Host(
                id=server.id,
                tags=["elastic_metal", *server.tags],
                zone=server.zone,
                state=str(server.status),
                hostname=server.name,
                public_ipv4=[
                    ip.address
                    for ip in server.ips
                    if ip.version == BaremetalIPVersion.I_PV4
                ],
                public_ipv6=[
                    ip.address
                    for ip in server.ips
                    if ip.version == BaremetalIPVersion.I_PV6
                ],
            )

            results.append(host)

        return results

    def _get_apple_sillicon(self, client: "Client", filters: _Filters) -> List[_Host]:
        api = ApplesiliconV1Alpha1API(client)

        servers: List[ApplesiliconServer] = []

        for zone in filters.zones:
            try:
                found = api.list_servers_all(
                    zone=zone,
                )

                servers.extend(found)
            except ScalewayException:
                pass

        results: List[_Host] = []
        for server in servers:
            host = _Host(
                id=server.id,
                tags=["apple_sillicon"],
                zone=server.zone,
                state=str(server.status),
                hostname=server.name,
                public_ipv4=[server.ip],
                private_ipv4=None,
                public_ipv6=None,
            )

            results.append(host)

        return results

    def _get_dedibox(self, client: "Client", filters: _Filters) -> List[_Host]:
        api = DediboxV1API(client)

        servers: List[DediboxServer] = []

        for zone in filters.zones:
            try:
                found = api.list_servers(
                    zone=zone,
                )
                servers.extend(found)
            except ScalewayException:
                pass

        results: List[_Host] = []
        for server in servers:
            public_ipv4 = []
            public_ipv6 = []

            for interface in server.interfaces:
                for ip in interface.ips:
                    if ip.version == DediboxIPVersion.IPV4:
                        public_ipv4.append(ip.address)
                    elif ip.version == DediboxIPVersion.IPV6:
                        public_ipv6.append(ip.address)

            host = _Host(
                id=server.id,
                tags=["dedibox", *server.tags],
                zone=server.zone,
                state=str(server.status),
                hostname=server.name,
                public_ipv4=public_ipv4,
                private_ipv4=None,
                public_ipv6=public_ipv6,
            )
            results.append(host)

            return results

    def _get_host_attribute(self, host: _Host, host_attributes: List[str]) -> str:
        host_as_dict = host.__dict__

        for host_attribute in host_attributes:
            if host_attribute in host_as_dict and host_as_dict[host_attribute]:
                return host_as_dict[host_attribute]

        raise AnsibleError(f"{host.id} has no attribute {host_attributes}")

    def _get_client(self):
        return Client.from_config_file_and_env(
            filepath=self.get_option("config_file") or os.getenv("SCW_CONFIG_FILE"),
            profile_name=self.get_option("profile") or os.getenv("SCW_PROFILE"),
        )

    def _get_filters(self):
        zones = self.get_option("zones")
        tags = self.get_option("tags")
        state = self.get_option("state")

        filters = _Filters()

        if zones:
            filters.zones = zones

        if tags:
            filters.tags = tags

        if state:
            filters.state = state

        return filters
