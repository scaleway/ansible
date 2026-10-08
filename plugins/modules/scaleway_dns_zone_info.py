#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Scaleway Ansible contributors
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Read one Scaleway DNS zone without changing it."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_dns_zone_info
short_description: Get information about a Scaleway DNS zone
description:
  - Find one DNS zone by its exact domain, subdomain and optional Project ID.
  - Fail if the zone does not exist or if multiple Projects contain a matching zone.
version_added: "2.8.0"
author:
  - Scaleway Ansible contributors
extends_documentation_fragment:
  - scaleway.scaleway.scaleway
requirements:
  - scaleway >= 2.10.1
options:
  domain:
    description: Parent domain, such as C(example.com).
    type: str
    required: true
  subdomain:
    description:
      - Name of the subdomain within C(domain), such as C(test).
      - Use an empty string for the root zone.
    type: str
    default: ""
"""

EXAMPLES = r"""
- name: Read the name servers of a DNS zone
  scaleway.scaleway.scaleway_dns_zone_info:
    domain: example.com
    subdomain: test
    project_id: "{{ scw_project_id }}"
  register: zone_info
  delegate_to: localhost

- name: Show the name servers
  ansible.builtin.debug:
    var: zone_info.dns_zone.ns
"""

RETURN = r"""
---
dns_zone:
  description: DNS zone details, including its full name and name servers.
  returned: success
  type: dict
  contains:
    id:
      description: Fully qualified DNS zone name.
      returned: always
      type: str
    ns:
      description: Current name servers.
      returned: always
      type: list
      elements: str
"""

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.scaleway.scaleway.plugins.module_utils.dns_zone import (
    one_matching_zone,
    zone_name,
    zone_to_dict,
)
from ansible_collections.scaleway.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_get_client_from_module,
)

try:
    from scaleway.domain.v2beta1 import DomainV2Beta1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def run_module(module):
    params = module.params
    domain = params["domain"].rstrip(".").lower()
    subdomain = params["subdomain"].rstrip(".").lower()
    if not domain:
        module.fail_json(msg="domain must be nonempty")
    try:
        client = scaleway_get_client_from_module(module)
        project_id = params["project_id"] or client.default_project_id
        zone = one_matching_zone(
            DomainV2Beta1API(client), domain, subdomain, project_id
        )
        if zone is None:
            module.fail_json(
                msg="DNS zone %s was not found" % zone_name(domain, subdomain)
            )
        module.exit_json(changed=False, dns_zone=zone_to_dict(zone))
    except ValueError as exc:
        module.fail_json(msg=str(exc))
    except Exception as exc:
        module.fail_json(msg="Failed to read DNS zone: %s" % exc)


def main():
    argument_spec = scaleway_argument_spec()
    argument_spec.update(
        domain=dict(type="str", required=True),
        subdomain=dict(type="str", default=""),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))
    run_module(module)


if __name__ == "__main__":
    main()
