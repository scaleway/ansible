#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_lb
short_description: Manage Scaleway lb's lb
description:
    - This module can be used to manage Scaleway lb's lb.
version_added: "2.1.0"
author:
    - Nathanael Demacon (@quantumsheep)
extends_documentation_fragment:
    - quantumsheep.scaleway.scaleway
    - quantumsheep.scaleway.scaleway_waitable_resource
requirements:
    - scaleway >= 0.6.0
options:
    state:
        description:
            - Indicate desired state of the target.
            - C(present) will create the resource.
            - C(absent) will delete the resource, if it exists.
        default: present
        choices: ["present", "absent", "]
        type: str
    id:
        type: str
        required: false
    description:
        type: str
        required: true
    type_:
        type: str
        required: true
    ssl_compatibility_level:
        type: str
        required: true
        choices:
            - ssl_compatibility_level_unknown
            - ssl_compatibility_level_intermediate
            - ssl_compatibility_level_modern
            - ssl_compatibility_level_old
    region:
        type: str
        required: false
        choices:
            - fr-par
            - nl-ams
            - pl-waw
    organization_id:
        type: str
        required: false
    project_id:
        type: str
        required: false
    name:
        type: str
        required: false
    ip_id:
        type: str
        required: false
    tags:
        type: list
        required: false
"""

RETURN = r"""
---
lb:
    description: The lb information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        name: "aaaaaa"
        description: "aaaaaa"
        status: ready
        instances:
            - aaaaaa
            - bbbbbb
        organization_id: 00000000-0000-0000-0000-000000000000
        project_id: 00000000-0000-0000-0000-000000000000
        ip:
            - aaaaaa
            - bbbbbb
        tags:
            - aaaaaa
            - bbbbbb
        frontend_count: 3
        backend_count: 3
        type_: "aaaaaa"
        subscriber:
            aaaaaa: bbbbbb
            cccccc: dddddd
        ssl_compatibility_level: ssl_compatibility_level_intermediate
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
        private_network_count: 3
        route_count: 3
        region: fr-par
        zone: "aaaaaa"
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.quantumsheep.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_waitable_resource_argument_spec,
    scaleway_get_client_from_module,
    scaleway_pop_client_params,
    scaleway_pop_waitable_resource_params,
)

from scaleway import Client, ScalewayException
from scaleway.lb.v1 import LbV1API


def create(module: AnsibleModule, client: Client) -> None:
    api = LbV1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_lb(lb_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_lb(**module.params)
    resource = api.wait_for_lb(lb_id=resource.id, region=module.params["region"])

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = LbV1API(client)

    id = module.params["id"]
    name = module.params["name"]

    if id is not None:
        resource = api.get_lb(lb_id=id, region=module.params["region"])
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_lb(lb_id=resource.id, region=module.params["region"])

    try:
        api.wait_for_lb(lb_id=resource.id, region=module.params["region"])
    except ScalewayException as e:
        if e.status_code != 404:
            raise e

    module.exit_json(
        changed=True,
        msg=f"lb's lb {resource.name} ({resource.id}) deleted",
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
        id=dict(type="str"),
        description=dict(type="str", required=True),
        type_=dict(type="str", required=True),
        ssl_compatibility_level=dict(
            type="str",
            required=True,
            choices=[
                "ssl_compatibility_level_unknown",
                "ssl_compatibility_level_intermediate",
                "ssl_compatibility_level_modern",
                "ssl_compatibility_level_old",
            ],
        ),
        region=dict(type="str", required=False, choices=["fr-par", "nl-ams", "pl-waw"]),
        organization_id=dict(type="str", required=False),
        project_id=dict(type="str", required=False),
        name=dict(type="str", required=False),
        ip_id=dict(type="str", required=False),
        tags=dict(type="list", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["id", "name"],),
        supports_check_mode=True,
    )

    core(module)


if __name__ == "__main__":
    main()
