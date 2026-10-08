#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Scaleway Ansible contributors
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

"""List Scaleway DNS zones across selected domains and projects."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_dns_zones_info
short_description: List Scaleway DNS zones across domains and projects
description:
  - Return every page of Scaleway DNS zones matching domain, Project and time filters.
  - Use C(domains=['*']) to query all domains visible to the API key.
  - Use C(project_ids=['*']) to query all Projects visible to the API key.
version_added: "2.8.0"
author:
  - Scaleway Ansible contributors
extends_documentation_fragment:
  - scaleway.scaleway.scaleway
requirements:
  - scaleway >= 2.10.1
options:
  domains:
    description:
      - Parent domains to query, such as C(example.com).
      - Use C(['*']) alone to query every domain.
    type: list
    elements: str
    required: true
  project_ids:
    description:
      - Project IDs to query. If omitted, use C(project_id) or the default Project.
      - Use C(['*']) alone to query all accessible Projects.
    type: list
    elements: str
  dns_zones:
    description: Optional fully qualified DNS zone names to include.
    type: list
    elements: str
  created_after:
    description: Include zones created after this RFC3339 timestamp.
    type: str
  created_before:
    description: Include zones created before this RFC3339 timestamp.
    type: str
  updated_after:
    description: Include zones updated after this RFC3339 timestamp.
    type: str
  updated_before:
    description: Include zones updated before this RFC3339 timestamp.
    type: str
"""

EXAMPLES = r"""
- name: List every DNS zone for a domain in a Project
  scaleway.scaleway.scaleway_dns_zones_info:
    domains:
      - example.com
    project_id: "{{ scw_project_id }}"
  register: zones_info
  delegate_to: localhost

- name: Show DNS zone names
  ansible.builtin.debug:
    msg: "{{ zones_info.dns_zones | map(attribute='id') | list }}"

- name: List all accessible zones
  scaleway.scaleway.scaleway_dns_zones_info:
    domains: ['*']
    project_ids: ['*']
  delegate_to: localhost
"""

RETURN = r"""
---
dns_zones:
  description: DNS zones returned for the parent domain across all API pages.
  returned: success
  type: list
  elements: dict
  contains:
    id:
      description: Fully qualified DNS zone name.
      returned: always
      type: str
    project_id:
      description: Scaleway Project ID.
      returned: always
      type: str
"""

from datetime import datetime

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.scaleway.scaleway.plugins.module_utils.dns_zone import (
    _canonical_name,
    zone_name,
    zone_to_dict,
)
from ansible_collections.scaleway.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_get_client_from_module,
)

try:
    from scaleway.account.v3 import AccountV3ProjectAPI
    from scaleway.domain.v2beta1 import DomainV2Beta1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def _exclusive_wildcard(values, name):
    if not values or "*" in values and values != ["*"]:
        raise ValueError("%s must be nonempty and '*' must appear alone" % name)
    if any(not value for value in values):
        raise ValueError("%s cannot contain an empty string" % name)


def _timestamp(value, name):
    if value is None:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("%s must be an RFC3339 timestamp" % name)
    if result.tzinfo is None:
        raise ValueError("%s must include a timezone" % name)
    return result


def list_zones(api, domains, project_ids, dns_zones, dates):
    """Fetch every domain/Project combination and remove overlapping results."""
    by_identity = {}
    zone_filter = {_canonical_name(name) for name in dns_zones} if dns_zones else None
    for project_id in project_ids:
        for domain in domains:
            zones = api.list_dns_zones_all(
                domain="" if domain == "*" else domain,
                project_id=project_id,
                dns_zones=dns_zones or None,
                **dates,
            )
            for zone in zones:
                if domain != "*" and _canonical_name(zone.domain) != domain:
                    continue
                if project_id is not None and zone.project_id != project_id:
                    continue
                name = _canonical_name(zone_name(zone.domain, zone.subdomain))
                if zone_filter is not None and name not in zone_filter:
                    continue
                by_identity[(zone.project_id, name)] = zone_to_dict(zone)
    return sorted(
        by_identity.values(), key=lambda zone: (zone["id"], zone["project_id"])
    )


def run_module(module):
    params = module.params
    try:
        domains = [value.rstrip(".").lower() for value in params["domains"]]
        _exclusive_wildcard(domains, "domains")
        if params["project_ids"] is not None:
            _exclusive_wildcard(params["project_ids"], "project_ids")

        dates = {
            name: _timestamp(params[name], name)
            for name in (
                "created_after",
                "created_before",
                "updated_after",
                "updated_before",
            )
        }
        client = scaleway_get_client_from_module(module)
        project_ids = params["project_ids"]
        if project_ids == ["*"]:
            # Resolve each project explicitly, as Terraform's list resource does.
            # Otherwise the DNS SDK applies the client's default Project.
            if not params["organization_id"]:
                client.default_organization_id = None
            project_ids = sorted(
                {
                    project.id
                    for project in AccountV3ProjectAPI(client).list_projects_all(
                        organization_id=params["organization_id"]
                    )
                }
            )
        elif project_ids is None:
            project_ids = [params["project_id"] or client.default_project_id]
        api = DomainV2Beta1API(client)
        module.exit_json(
            changed=False,
            dns_zones=list_zones(api, domains, project_ids, params["dns_zones"], dates),
        )
    except ValueError as exc:
        module.fail_json(msg=str(exc))
    except Exception as exc:
        module.fail_json(msg="Failed to list DNS zones: %s" % exc)


def main():
    argument_spec = scaleway_argument_spec()
    argument_spec.update(
        domains=dict(type="list", elements="str", required=True),
        project_ids=dict(type="list", elements="str"),
        dns_zones=dict(type="list", elements="str"),
        created_after=dict(type="str"),
        created_before=dict(type="str"),
        updated_after=dict(type="str"),
        updated_before=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[["project_id", "project_ids"]],
        supports_check_mode=True,
    )
    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))
    run_module(module)


if __name__ == "__main__":
    main()
