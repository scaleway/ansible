#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_lb_v1_frontend
short_description: Manage Scaleway lb_v1's frontend
description:
    - This module can be used to manage Scaleway lb_v1's frontend.
version_added: "2.1.0"
author:
    - Nathanael Demacon (@quantumsheep)
extends_documentation_fragment:
    - scaleway.scaleway.scaleway
    - scaleway.scaleway.scaleway_waitable_resource
requirements:
    - scaleway >= 0.6.0
options:
    state:
        description:
            - Indicate desired state of the target.
            - C(present) will create the resource.
            - C(absent) will delete the resource, if it exists.
        default: present
        choices: ["present", "absent"]
        type: str
    id:
        description: id
        type: str
        required: false
    lb_id:
        description: lb_id
        type: str
        required: true
    inbound_port:
        description: inbound_port
        type: int
        required: true
    backend_id:
        description: backend_id
        type: str
        required: true
    enable_http3:
        description: enable_http3
        type: bool
        required: true
    zone:
        description: zone
        type: str
        required: false
    name:
        description: name
        type: str
        required: false
    timeout_client:
        description: timeout_client
        type: str
        required: false
    certificate_id:
        description: certificate_id
        type: str
        required: false
    certificate_ids:
        description: certificate_ids
        type: list
        elements: str
        required: false
"""

EXAMPLES = r"""
- name: Create a frontend
  scaleway.scaleway.scaleway_lb_v1_frontend:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
    lb_id: "aaaaaa"
    inbound_port: "aaaaaa"
    backend_id: "aaaaaa"
    enable_http3: true
"""

RETURN = r"""
---
frontend:
    description: The frontend information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        name: "aaaaaa"
        inbound_port: 3
        backend:
            aaaaaa: bbbbbb
            cccccc: dddddd
        lb:
            aaaaaa: bbbbbb
            cccccc: dddddd
        timeout_client: "aaaaaa"
        certificate:
            aaaaaa: bbbbbb
            cccccc: dddddd
        certificate_ids: 00000000-0000-0000-0000-000000000000
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
        enable_http3: true
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

    resource_id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_frontend(frontend_id=resource_id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_frontend(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = LbZonedV1API(client)

    resource_id = module.params.pop("id", None)

    if resource_id is not None:
        resource = api.get_frontend(
            frontend_id=resource_id,
            zone=module.params["zone"],
        )
    elif module.params.get("name", None) is not None:
        resources = api.list_frontends_all(
            name=module.params["name"],
            lb_id=module.params.get("lb_id", None),
            zone=module.params["zone"],
        )
        if len(resources) == 0:
            module.exit_json(msg="No frontend found with name {name}")
        elif len(resources) > 1:
            module.exit_json(msg="More than one frontend found with name {name}")
        else:
            resource = resources[0]
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_frontend(
        frontend_id=resource.id,
        zone=resource.zone,
    )

    module.exit_json(
        changed=True,
        msg=f"lb_v1's frontend {resource.name} ({resource.id}) deleted",
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
        frontend_id=dict(type="str"),
        lb_id=dict(
            type="str",
            required=True,
        ),
        inbound_port=dict(
            type="int",
            required=True,
        ),
        backend_id=dict(
            type="str",
            required=True,
        ),
        enable_http3=dict(
            type="bool",
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
        timeout_client=dict(
            type="str",
            required=False,
        ),
        certificate_id=dict(
            type="str",
            required=False,
        ),
        certificate_ids=dict(
            type="list",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["frontend_id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
