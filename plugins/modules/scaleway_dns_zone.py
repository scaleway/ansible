#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Scaleway Ansible contributors
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Create or remove one Scaleway DNS zone."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_dns_zone
short_description: Manage a Scaleway DNS zone
description:
  - Create or delete a DNS zone within a Scaleway Project.
  - An existing zone is found by its exact domain, subdomain and Project ID.
  - Deleting a zone also deletes all DNS records in that zone.
version_added: "2.8.0"
author:
  - Scaleway Ansible contributors
extends_documentation_fragment:
  - scaleway.scaleway.scaleway
requirements:
  - scaleway >= 2.10.1
options:
  state:
    description: Desired state of the DNS zone.
    type: str
    choices: [present, absent]
    default: present
  domain:
    description: Parent domain, such as C(example.com).
    type: str
    required: true
  subdomain:
    description:
      - Name of the subdomain within C(domain), such as C(test).
      - Use an empty string to manage the root zone.
    type: str
    default: ""
  current_subdomain:
    description:
      - Existing subdomain name to rename to C(subdomain).
      - Ansible has no persistent resource identity, so provide this when renaming.
      - Only valid with C(state=present). Omit for ordinary creation and deletion.
    type: str
"""

EXAMPLES = r"""
- name: Ensure a subdomain DNS zone exists
  scaleway.scaleway.scaleway_dns_zone:
    domain: example.com
    subdomain: test
    project_id: "{{ scw_project_id }}"
  delegate_to: localhost

- name: Remove the zone and all its records
  scaleway.scaleway.scaleway_dns_zone:
    domain: example.com
    subdomain: old
    project_id: "{{ scw_project_id }}"
    state: absent
  delegate_to: localhost

- name: Rename an existing subdomain zone
  scaleway.scaleway.scaleway_dns_zone:
    domain: example.com
    current_subdomain: old
    subdomain: new
    project_id: "{{ scw_project_id }}"
  delegate_to: localhost
"""

RETURN = r"""
---
dns_zone:
  description: DNS zone after the operation, or before deletion.
  returned: when the zone exists or check mode plans creation
  type: dict
  contains:
    id:
      description: Fully qualified DNS zone name.
      type: str
      returned: always
    domain:
      description: Parent domain.
      type: str
      returned: always
    subdomain:
      description: Subdomain within the parent domain.
      type: str
      returned: always
    project_id:
      description: Scaleway Project ID.
      type: str
      returned: always
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
    current_subdomain = params["current_subdomain"]
    if current_subdomain is not None:
        current_subdomain = current_subdomain.rstrip(".").lower()
        if params["state"] == "absent":
            module.fail_json(
                msg="current_subdomain can only be used with state=present"
            )

    try:
        client = scaleway_get_client_from_module(module)
        project_id = params["project_id"] or client.default_project_id
        if not project_id:
            module.fail_json(msg="project_id or a default Project ID is required")

        api = DomainV2Beta1API(client)
        desired = params["state"] == "present"
        zone = one_matching_zone(api, domain, subdomain, project_id)
        source = None
        if desired and current_subdomain is not None and current_subdomain != subdomain:
            source = one_matching_zone(api, domain, current_subdomain, project_id)
            if source is not None and zone is not None:
                module.fail_json(
                    msg="Both source and destination DNS zones exist; "
                    "refusing to rename"
                )
            if source is None and zone is None:
                module.fail_json(
                    msg="Source DNS zone does not exist; refusing to create a replacement during rename"
                )

        if desired:
            before = zone_to_dict(source or zone) if (source or zone) else None
            changed = source is not None or zone is None
            if source is not None:
                if module.check_mode:
                    after = dict(
                        before,
                        id=zone_name(domain, subdomain),
                        subdomain=subdomain,
                    )
                else:
                    after = zone_to_dict(
                        api.update_dns_zone(
                            dns_zone=zone_name(domain, current_subdomain),
                            new_dns_zone=subdomain,
                            project_id=project_id,
                        )
                    )
            elif zone is None:
                if module.check_mode:
                    after = {
                        "id": zone_name(domain, subdomain),
                        "domain": domain,
                        "subdomain": subdomain,
                        "project_id": project_id,
                    }
                else:
                    after = zone_to_dict(
                        api.create_dns_zone(
                            domain=domain, subdomain=subdomain, project_id=project_id
                        )
                    )
            else:
                after = before
            result = {"changed": changed, "dns_zone": after}
        else:
            if zone is not None and subdomain == "":
                module.fail_json(
                    msg="Scaleway API does not allow deleting a root DNS zone"
                )
            before = zone_to_dict(zone) if zone is not None else None
            changed = zone is not None
            if changed and not module.check_mode:
                api.delete_dns_zone(
                    dns_zone=zone_name(domain, subdomain), project_id=project_id
                )
            result = {"changed": changed}
            if zone is not None:
                result["dns_zone"] = before
            if changed and not module.check_mode:
                result["deleted"] = zone_name(domain, subdomain)
            after = None

        result["diff"] = {"before": before, "after": after}
        module.exit_json(**result)
    except ValueError as exc:
        module.fail_json(msg=str(exc))
    except Exception as exc:
        module.fail_json(msg=f"Failed to manage DNS zone: {exc}")


def main():
    argument_spec = scaleway_argument_spec()
    argument_spec.update(
        state=dict(type="str", choices=["present", "absent"], default="present"),
        domain=dict(type="str", required=True),
        subdomain=dict(type="str", default=""),
        current_subdomain=dict(type="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))
    run_module(module)


if __name__ == "__main__":
    main()
