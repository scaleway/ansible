#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_instance_v1_ip
short_description: Manage Scaleway instance_v1's ip
description:
    - This module can be used to manage Scaleway instance_v1's ip.
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
    ip:
        description: ip
        type: str
        required: false
    type_:
        description: type_
        type: str
        required: true
        choices:
            - unknown_iptype
            - nat
            - routed_ipv4
            - routed_ipv6
    zone:
        description: zone
        type: str
        required: false
    organization:
        description: organization
        type: str
        required: false
    project:
        description: project
        type: str
        required: false
    tags:
        description: tags
        type: list
        elements: str
        required: false
    server:
        description: server
        type: str
        required: false
"""

EXAMPLES = r"""
- name: Create a ip
  scaleway.scaleway.scaleway_instance_v1_ip:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
    type_: "aaaaaa"
"""

RETURN = r"""
---
ip:
    description: The ip information
    returned: when I(state=present)
    type: dict
    sample:
        ip:
            aaaaaa: bbbbbb
            cccccc: dddddd
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
    from scaleway.instance.v1 import InstanceV1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = InstanceV1API(client)

    resource_id = module.params.pop("ip", None)
    if id is not None:
        resource = api.get_ip(ip=resource_id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_ip(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = InstanceV1API(client)

    resource_id = module.params.pop("ip", None)

    if resource_id is not None:
        resource = api.get_ip(
            ip=resource_id,
            zone=module.params["zone"],
        )
    elif module.params.get("name", None) is not None:
        resources = api.list_ips_all(
            name=module.params["name"],
            zone=module.params["zone"],
        )
        if len(resources) == 0:
            module.exit_json(msg="No ip found with name {name}")
        elif len(resources) > 1:
            module.exit_json(msg="More than one ip found with name {name}")
        else:
            resource = resources[0]
    else:
        module.fail_json(msg="ip is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_ip(
        ip=resource.id,
        zone=resource.zone,
    )

    module.exit_json(
        changed=True,
        msg=f"instance_v1's ip {resource.ip} deleted",
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
        ip=dict(type="str"),
        type_=dict(
            type="str",
            required=True,
            choices=["unknown_iptype", "nat", "routed_ipv4", "routed_ipv6"],
        ),
        zone=dict(
            type="str",
            required=False,
        ),
        organization=dict(
            type="str",
            required=False,
        ),
        project=dict(
            type="str",
            required=False,
        ),
        tags=dict(
            type="list",
            required=False,
            elements="str",
        ),
        server=dict(
            type="str",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
