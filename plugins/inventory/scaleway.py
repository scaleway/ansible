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
    - scaleway >= 0.6.0
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
            - État du serveur d'instance
        type: list
        elements: str
        default: [running]
    hostnames:
        description: List of preference about what to use as an hostname.
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
            - ""
            - "If the variable is not found, the host will be ignored."
        type: dict
"""

EXAMPLES = r"""
plugin: scaleway.scaleway.scaleway
access_key: <your access key>
secret_key: <your secret key>
api_url: https://api.scaleway.com
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


from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import List, Optional

from ansible.errors import AnsibleError
from ansible.module_utils.basic import missing_required_lib
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable

try:
    from scaleway_core.bridge import Zone
    from scaleway import Client, ScalewayException
    from scaleway.applesilicon.v1alpha1 import ApplesiliconV1Alpha1API
    from scaleway.applesilicon.v1alpha1 import Server as ApplesiliconServer
    from scaleway.baremetal.v1 import BaremetalV1API, IPVersion
    from scaleway.baremetal.v1 import Server as BaremetalServer
    from scaleway.instance.v1 import InstanceV1API, ServerState
    from scaleway.instance.v1 import Server as InstanceServer
    from scaleway.dedibox.v1 import DediboxV1API, IPVersion
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
    public_ipv4: Optional[str]
    private_ipv4: Optional[str]
    public_ipv6: Optional[str]

    # Instances-only
    public_dns: Optional[str] = None
    private_dns: Optional[str] = None


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
                results = self._cache[cache_key]
            except KeyError:
                update_cache = True

        if not use_cache or update_cache:
            results = self.get_inventory()

        if update_cache:
            self._cache[cache_key] = results

        self.populate(results)

    def populate(self, results: List[_Host]):
        hostnames = self.get_option("hostnames")
        variables = self.get_option("variables") or {}

        for result in results:
            groups = self.get_host_groups(result)

            try:
                hostname = self._get_hostname(result, hostnames)
            except AnsibleError as e:
                self.display.warning(f"Skipping host {result.id}: {e}")
                continue

            self.inventory.add_host(host=hostname)

            should_skip = False
            for variable, source in variables.items():
                value = getattr(result, source, None)
                if not value:
                    self.display.warning(
                        f"Skipping host {result.id}: "
                        f"Field {source} is not available."
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
        return set(host.tags).union(set([host.zone.replace("-", "_")]))

    def get_inventory(self):
        client = self._get_client()
        filters = self._get_filters()

        instances: List[InstanceServer] = self._get_instances(client, filters)
        elastic_metals: List[BaremetalServer] = self._get_elastic_metal(client, filters)
        apple_silicon: List[ApplesiliconServer] = self._get_apple_sillicon(client, filters)

        return instances + elastic_metals + apple_silicon

    def _get_instances(self, client: "Client", filters: _Filters) -> List[_Host]:
        api = InstanceV1API(client)

        servers: List[InstanceServer] = []

        for zone in filters.zones:
            for state in filters.state:
                servers.extend(api.list_servers_all(
                    zone=zone,
                    tags=filters.tags if filters.tags else None,
                    state=state,
                ))

        results: List[_Host] = []
        for server in servers:
            host = _Host(
                id=server.id,
                tags=["instance", *server.tags],
                zone=server.zone,
                state=str(server.state),
                hostname=server.hostname,
                public_ipv4=server.public_ip.address if server.public_ip else None,
                private_ipv4=server.private_ip if server.private_ip else None,
                public_ipv6=server.ipv6 if server.ipv6 else None,
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
            public_ipv4s = filter(lambda ip: ip.version == IPVersion.IPV4, server.ips)
            public_ipv6s = filter(lambda ip: ip.version == IPVersion.IPV6, server.ips)

            public_ipv4 = next(public_ipv4s, None)
            public_ipv6 = next(public_ipv6s, None)

            host = _Host(
                id=server.id,
                tags=["elastic_metal", *server.tags],
                zone=server.zone,
                state=str(server.status),
                hostname=server.name,
                public_ipv4=public_ipv4.address if public_ipv4 else None,
                private_ipv4=None,
                public_ipv6=public_ipv6.address if public_ipv6 else None,
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
                tags=["apple_sillicon", *server.tags],
                zone=server.zone,
                state=str(server.status),
                hostname=server.name,
                public_ipv4=server.ip,
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
            public_ipv4 = filter(lambda ip: ip.version == IPVersion.IPV4, server.interfaces.ips)
            public_ipv6 = filter(lambda ip: ip.version == IPVersion.IPV6, server.interfaces.ips)
            public_ipv4 = next(public_ipv4, None)
            public_ipv6 = next(public_ipv6, None)

            host = _Host(
                id=server.id,
                tags=["dedibox", *server.tags],
                zone=server.zone,
                state=str(server.status),
                hostname=server.name,
                public_ipv4=public_ipv4.address if public_ipv4 else None,
                private_ipv4=None,
                public_ipv6=public_ipv6.address if public_ipv6 else None,
            )
            results.append(host)

            return results

    def _get_hostname(self, host: _Host, hostnames: List[str]) -> str:
        as_dict = host.__dict__

        for hostname in hostnames:
            if hostname in as_dict and as_dict[hostname]:
                return as_dict[hostname]

        raise AnsibleError(f"No hostname found for {host.id} in {hostnames}")

    def _get_client(self):
        config_file = self.get_option("config_file")
        profile = self.get_option("profile")
        access_key = self.get_option("access_key")
        secret_key = self.get_option("secret_key")
        organization_id = self.get_option("organization_id")
        project_id = self.get_option("project_id")
        api_url = self.get_option("api_url")
        api_allow_insecure = self.get_option("api_allow_insecure")
        user_agent = self.get_option("user_agent")

        if profile:
            client = Client.from_config_file(
                filepath=config_file if config_file else None,
                profile_name=profile,
            )
        else:
            client = Client()

        if access_key:
            client.access_key = access_key

        if secret_key:
            client.secret_key = secret_key

        if organization_id:
            client.default_organization_id = organization_id

        if project_id:
            client.default_project_id = project_id

        if api_url:
            client.api_url = api_url

        if api_allow_insecure:
            client.api_allow_insecure = api_allow_insecure

        if user_agent:
            client.user_agent = user_agent

        return client

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
