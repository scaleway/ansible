#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_lb_acl
short_description: Manage Scaleway lb's acl
description:
    - This module can be used to manage Scaleway lb's acl.
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
    frontend_id:
        type: str
        required: true
    action:
        type: dict
        required: true
    index:
        type: int
        required: true
    description:
        type: str
        required: true
    region:
        type: str
        required: false
        choices:
            - fr-par
            - nl-ams
            - pl-waw
    name:
        type: str
        required: false
    match:
        type: dict
        required: false
"""

RETURN = r"""
---
acl:
    description: The acl information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        name: "aaaaaa"
        match:
            aaaaaa: bbbbbb
            cccccc: dddddd
        action:
            aaaaaa: bbbbbb
            cccccc: dddddd
        frontend:
            aaaaaa: bbbbbb
            cccccc: dddddd
        index: 3
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
        description: "aaaaaa"
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
        resource = api.get_acl(acl_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_acl(**module.params)

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = LbV1API(client)

    id = module.params["id"]
    name = module.params["name"]

    if id is not None:
        resource = api.get_acl(acl_id=id, region=module.params["region"])
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_acl(acl_id=resource.id, region=module.params["region"])

    module.exit_json(
        changed=True,
        msg=f"lb's acl {resource.name} ({resource.id}) deleted",
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
        frontend_id=dict(type="str", required=True),
        action=dict(type="dict", required=True),
        index=dict(type="int", required=True),
        description=dict(type="str", required=True),
        region=dict(type="str", required=False, choices=["fr-par", "nl-ams", "pl-waw"]),
        name=dict(type="str", required=False),
        match=dict(type="dict", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["id", "name"],),
        supports_check_mode=True,
    )

    core(module)


if __name__ == "__main__":
    main()
