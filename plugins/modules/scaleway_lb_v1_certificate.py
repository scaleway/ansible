#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_lb_v1_certificate
short_description: Manage Scaleway lb_v1's certificate
description:
    - This module can be used to manage Scaleway lb_v1's certificate.
version_added: "2.1.0"
author:
    - Nathanael Demacon (@quantumsheep)
extends_documentation_fragment:
    - scaleway.scaleway.scaleway
    - scaleway.scaleway.scaleway_waitable_resource
requirements:
    - scaleway >= 0.16.0
options:
    state:
        description:
            - Indicate desired state of the target.
            - C(present) will create the resource.
            - C(absent) will delete the resource, if it exists.
        default: present
        choices: ["present", "absent"]
        type: str
    certificate_id:
        description: certificate_id
        type: str
        required: false
    lb_id:
        description: lb_id
        type: str
        required: true
    zone:
        description: zone
        type: str
        required: false
    name:
        description: name
        type: str
        required: false
    letsencrypt:
        description: letsencrypt
        type: dict
        required: false
    custom_certificate:
        description: custom_certificate
        type: dict
        required: false
"""

EXAMPLES = r"""
- name: Create a certificate
  scaleway.scaleway.scaleway_lb_v1_certificate:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
    lb_id: "aaaaaa"
"""

RETURN = r"""
---
certificate:
    description: The certificate information
    returned: when I(state=present)
    type: dict
    sample:
        type_: letsencryt
        id: 00000000-0000-0000-0000-000000000000
        common_name: "aaaaaa"
        subject_alternative_name:
            - aaaaaa
            - bbbbbb
        fingerprint: "aaaaaa"
        not_valid_before: 00000000-0000-0000-0000-000000000000
        not_valid_after: 00000000-0000-0000-0000-000000000000
        status: pending
        lb:
            aaaaaa: bbbbbb
            cccccc: dddddd
        name: "aaaaaa"
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
        status_details: "aaaaaa"
"""

from ansible.module_utils.basic import (
    AnsibleModule,
    missing_required_lib,
)
from ansible_collections.scaleway.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_waitable_resource_argument_spec,
    scaleway_get_client_from_module,
    scaleway_pop_client_params,
    scaleway_pop_waitable_resource_params,
)

try:
    from scaleway import Client
    from scaleway.lb.v1 import LbZonedV1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = LbZonedV1API(client)

    resource_id = module.params.pop("certificate_id", None)
    if id is not None:
        resource = api.get_certificate(certificate_id=resource_id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_certificate(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = LbZonedV1API(client)

    resource_id = module.params.pop("id", None)

    if resource_id is not None:
        resource = api.get_certificate(
            certificate_id=resource_id,
            zone=module.params["zone"],
        )
    elif module.params.get("name", None) is not None:
        resources = api.list_certificates_all(
            name=module.params["name"],
            lb_id=module.params.get("lb_id", None),
            zone=module.params["zone"],
        )
        if len(resources) == 0:
            module.exit_json(msg="No certificate found with name {name}")
        elif len(resources) > 1:
            module.exit_json(msg="More than one certificate found with name {name}")
        else:
            resource = resources[0]
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_certificate(
        certificate_id=resource.id,
        zone=resource.zone,
    )

    module.exit_json(
        changed=True,
        msg=f"lb_v1's certificate {resource.name} ({resource.id}) deleted",
    )


def core(module: AnsibleModule) -> None:
    client = scaleway_get_client_from_module(module)

    state = module.params.pop("state")
    scaleway_pop_client_params(module)
    scaleway_pop_waitable_resource_params(module)

    if state == "present":
        create(module, client)
    elif state == "absent":
        delete(module, client)


def main() -> None:
    argument_spec = scaleway_argument_spec()
    argument_spec.update(scaleway_waitable_resource_argument_spec())
    argument_spec.update(
        state=dict(type="str", default="present", choices=["absent", "present"]),
        certificate_id=dict(type="str"),
        lb_id=dict(
            type="str",
            required=True,
        ),
        zone=dict(
            type="str",
            required=False,
        ),
        name=dict(
            type="str",
            required=False,
        ),
        letsencrypt=dict(
            type="dict",
            required=False,
        ),
        custom_certificate=dict(
            type="dict",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["certificate_id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
