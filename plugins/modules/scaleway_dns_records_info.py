#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Scaleway Ansible contributors
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""List Scaleway DNS records across selected projects and zones."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_dns_records_info
short_description: List Scaleway DNS records across zones and projects
description:
  - List DNS records from one or more zones and projects.
  - C(dns_zones=['*']) or C(dns_zones=['all']) discovers all zones in each selected project.
  - C(project_ids=['*']) discovers all projects visible to the API credentials.
  - The module reads every page of zone and record results and never changes records.
version_added: "2.8.0"
author:
  - Scaleway Ansible contributors
extends_documentation_fragment:
  - scaleway.scaleway.scaleway
requirements:
  - scaleway >= 2.10.1
options:
  dns_zones:
    description:
      - DNS zones to query, for example C(['example.com', 'dev.example.com']).
      - Use a single C(*) or C(all) entry for every zone in the selected projects.
    type: list
    elements: str
    required: true
  project_ids:
    description:
      - Project IDs to query. Defaults to the C(project_id) or configured default project.
      - Use a single C(*) entry for all projects visible to the API credentials.
      - Cannot be combined with C(project_id).
    type: list
    elements: str
  name:
    description:
      - Optional record name relative to each zone. An empty string selects its apex.
      - Omit to return every name.
    type: str
  record_type:
    description: Optional DNS record type such as C(A), C(TXT), or C(MX).
    type: str
"""

EXAMPLES = r"""
- name: List all A records in two DNS zones
  scaleway.scaleway.scaleway_dns_records_info:
    dns_zones:
      - example.com
      - dev.example.com
    record_type: A
  register: addresses
  delegate_to: localhost

- name: List all records in a project
  scaleway.scaleway.scaleway_dns_records_info:
    project_ids:
      - 11111111-1111-1111-1111-111111111111
    dns_zones:
      - '*'
  register: records
  delegate_to: localhost
"""

RETURN = r"""
---
records:
  description: Records from all selected zones and projects, sorted deterministically.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 11111111-1111-1111-1111-111111111111
      dns_zone: example.com
      project_id: 22222222-2222-2222-2222-222222222222
      name: www
      type: A
      data: 192.0.2.10
      ttl: 300
total_count:
  description: Number of records returned.
  returned: always
  type: int
"""

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.scaleway.scaleway.plugins.module_utils.dns_records import (
    normalize_dns_zone,
    normalize_record_name,
    record_to_dict,
)
from ansible_collections.scaleway.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_get_client_from_module,
)

try:
    from scaleway.account.v3 import AccountV3ProjectAPI
    from scaleway.domain.v2beta1 import DomainV2Beta1API
    from scaleway.domain.v2beta1.types import RecordType

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def _validate_filters(params):
    zones = params["dns_zones"]
    projects = params["project_ids"]
    if not zones or any(not zone.strip() for zone in zones):
        raise ValueError("dns_zones must contain at least one nonempty zone")
    if any(not normalize_dns_zone(zone) for zone in zones):
        raise ValueError("dns_zones must not contain an empty normalized zone")
    if any(zone in ("*", "all") for zone in zones) and len(zones) != 1:
        raise ValueError("* or all must be the only entry in dns_zones")
    if projects is not None:
        if params["project_id"] is not None:
            raise ValueError("project_ids cannot be combined with project_id")
        if not projects or any(not project.strip() for project in projects):
            raise ValueError("project_ids must contain at least one nonempty ID")
        if "*" in projects and len(projects) != 1:
            raise ValueError("* must be the only entry in project_ids")
    record_type = params["record_type"]
    if record_type is not None:
        record_type = record_type.upper()
        if record_type not in RecordType.__members__ or record_type == "UNKNOWN":
            raise ValueError(f"unsupported DNS record type: {record_type}")
    return record_type


def _projects_to_query(client, account_api, params):
    requested = params["project_ids"]
    if requested == ["*"]:
        organization_id = params["organization_id"]
        if not organization_id:
            client.default_organization_id = None
        projects = account_api.list_projects_all(organization_id=organization_id)
        return sorted({project.id for project in projects})
    if requested is not None:
        return list(dict.fromkeys(requested))
    project_id = params["project_id"] or client.default_project_id
    if not project_id:
        raise ValueError(
            "set project_id or project_ids, or configure a default project"
        )
    return [project_id]


def _zones_to_query(api, project_id, requested):
    if requested in (["*"], ["all"]):
        # The generated SDK types domain as required; None omits the API filter.
        zones = api.list_dns_zones_all(domain=None, project_id=project_id)
        return sorted(
            {
                normalize_dns_zone(
                    f"{zone.subdomain}.{zone.domain}" if zone.subdomain else zone.domain
                )
                for zone in zones
            }
        )
    return list(dict.fromkeys(normalize_dns_zone(zone) for zone in requested))


def list_records(api, project_ids, dns_zones, name=None, record_type=None):
    """Read all result pages, filter exactly, and deduplicate overlapping zones."""
    results = {}
    for project_id in project_ids:
        for zone in _zones_to_query(api, project_id, dns_zones):
            selected_name = (
                normalize_record_name(name, zone) if name is not None else None
            )
            query = dict(dns_zone=zone, project_id=project_id, name=selected_name)
            if record_type is not None:
                query["type_"] = RecordType[record_type]
            # The generated SDK marks name as mandatory; None omits the name
            # filter and lets the API return every record in the zone.
            for record in api.list_dns_zone_records_all(**query):
                if (
                    selected_name is not None
                    and normalize_record_name(record.name, zone) != selected_name
                ):
                    continue
                if (
                    record_type is not None
                    and getattr(record.type_, "name", str(record.type_)).upper()
                    != record_type
                ):
                    continue
                key = (project_id, zone, record.id)
                results[key] = record_to_dict(record, zone, project_id)
    return sorted(
        results.values(),
        key=lambda item: (
            item["project_id"],
            item["dns_zone"],
            item["type"],
            item["name"],
            item["data"],
            item["id"],
        ),
    )


def run_module(module):
    try:
        record_type = _validate_filters(module.params)
    except ValueError as exc:
        module.fail_json(msg=str(exc))
        return

    try:
        client = scaleway_get_client_from_module(module)
        account_api = AccountV3ProjectAPI(client)
        domain_api = DomainV2Beta1API(client)
        project_ids = _projects_to_query(client, account_api, module.params)
        records = list_records(
            domain_api,
            project_ids,
            module.params["dns_zones"],
            name=module.params["name"],
            record_type=record_type,
        )
    except ValueError as exc:
        module.fail_json(msg=str(exc))
        return
    except Exception as exc:
        module.fail_json(msg=f"Failed to list DNS records: {exc}")
        return
    module.exit_json(changed=False, records=records, total_count=len(records))


def main():
    argument_spec = scaleway_argument_spec()
    argument_spec.update(
        dns_zones=dict(type="list", elements="str", required=True),
        project_ids=dict(type="list", elements="str"),
        name=dict(type="str"),
        record_type=dict(type="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))
    run_module(module)


if __name__ == "__main__":
    main()
