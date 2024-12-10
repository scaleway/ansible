# -*- coding: utf-8 -*-

# Copyright: (c), Ansible Project
# Copyright: (c), Nathanael Demacon (@quantumsheep)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


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
    from scaleway.instance.v1 import InstanceV1API
    from scaleway.instance.v1 import Server as InstanceServer
    from scaleway.instance.v1 import ServerState

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


@dataclass
class _Host:
    id: str
    tags: List[str]
    zone: "Zone"
    state: str

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

        instances = self._get_instances(client, filters)
        elastic_metals = self._get_elastic_metal(client, filters)

        return instances + elastic_metals

    def _get_instances(self, client: "Client", filters: _Filters) -> List[_Host]:
        api = InstanceV1API(client)

        servers: List[InstanceServer] = []

        for zone in filters.zones:
            servers.extend(
                api.list_servers_all(
                    zone=zone,
                    tags=filters.tags if filters.tags else None,
                    state=ServerState.RUNNING,
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
                public_ipv4=server.public_ip.address if server.public_ip else None,
                private_ipv4=server.private_ip,
                public_ipv6=server.ipv6.address if server.ipv6 else None,
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
                tags=["apple_sillicon"],
                zone=server.zone,
                state=str(server.status),
                hostname=server.name,
                public_ipv4=server.ip,
                private_ipv4=None,
                public_ipv6=None,
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

        filters = _Filters()

        if zones:
            filters.zones = zones

        if tags:
            filters.tags = tags

        return filters
