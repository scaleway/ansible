#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Scaleway Ansible contributors
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Read an existing Scaleway domain registration."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_domain_registration_info
short_description: Read a Scaleway domain registration
description:
  - Read a managed domain, its owner and DNSSEC information, and its registration task when available.
  - Scaleway archives old registration tasks. In that case C(task_id) is null
    and C(domain_names) contains only the queried domain.
version_added: "2.8.0"
author:
  - Scaleway Ansible contributors
extends_documentation_fragment:
  - scaleway.scaleway.scaleway
requirements:
  - scaleway >= 2.10.1
options:
  domain_name:
    description: Registered domain name to look up.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Inspect an existing registration
  scaleway.scaleway.scaleway_domain_registration_info:
    domain_name: example.com
  register: registration
  delegate_to: localhost
"""

RETURN = r"""
---
registration:
  description: Registrar domain object, including contacts and DNSSEC data.
  returned: always
  type: dict
domain_names:
  description: Domain names associated with the registration task when available.
  returned: always
  type: list
  elements: str
task_id:
  description: Registration task ID, or null if Scaleway has archived it.
  returned: always
  type: str
"""

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.scaleway.scaleway.plugins.module_utils.dns_registration import (
    find_registration_task,
    get_domain_or_none,
    to_dict,
)
from ansible_collections.scaleway.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_get_client_from_module,
)

try:
    from scaleway.domain.v2beta1 import DomainV2Beta1RegistrarAPI

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def read_registration(api, domain_name, project_id=None):
    name = domain_name.strip().lower().rstrip(".")
    if not name:
        raise ValueError("domain_name must not be empty")
    registration = get_domain_or_none(api, name)
    if registration is None:
        raise ValueError(f"domain registration {name} was not found")
    if project_id and registration.project_id != project_id:
        raise ValueError(
            f"domain {name} belongs to project {registration.project_id}, not {project_id}"
        )
    task = find_registration_task(api, name, project_id=project_id)
    domain_names = (
        [value.strip() for value in (task.domain or "").split(",") if value.strip()]
        if task
        else [name]
    )
    return dict(
        changed=False,
        registration=to_dict(registration),
        domain_names=domain_names,
        task_id=task.id if task else None,
        project_id=registration.project_id,
    )


def main():
    argument_spec = scaleway_argument_spec()
    argument_spec.update(domain_name=dict(type="str", required=True))
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))
    try:
        client = scaleway_get_client_from_module(module)
        api = DomainV2Beta1RegistrarAPI(client)
        project_id = module.params["project_id"] or client.default_project_id
        module.exit_json(
            **read_registration(api, module.params["domain_name"], project_id)
        )
    except Exception as error:
        module.fail_json(msg=f"Scaleway registrar request failed: {error}")


if __name__ == "__main__":
    main()
