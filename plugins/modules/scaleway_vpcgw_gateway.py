#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_vpcgw_gateway
short_description: Manage Scaleway vpcgw's gateway
description:
    - This module can be used to manage Scaleway vpcgw's gateway.
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
    type_:
        type: str
        required: true
    enable_smtp:
        type: bool
        required: true
    enable_bastion:
        type: bool
        required: true
    zone:
        type: str
        required: false
    project_id:
        type: str
        required: false
    name:
        type: str
        required: false
    tags:
        type: list
        required: false
    upstream_dns_servers:
        type: list
        required: false
    ip_id:
        type: str
        required: false
    bastion_port:
        type: int
        required: false
"""

RETURN = r"""
---
gateway:
    description: The gateway information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        organization_id: 00000000-0000-0000-0000-000000000000
        project_id: 00000000-0000-0000-0000-000000000000
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
        type_:
            aaaaaa: bbbbbb
            cccccc: dddddd
        status: stopped
        name: "aaaaaa"
        tags:
            - aaaaaa
            - bbbbbb
        ip:
            aaaaaa: bbbbbb
            cccccc: dddddd
        gateway_networks:
            - aaaaaa
            - bbbbbb
        upstream_dns_servers:
            - aaaaaa
            - bbbbbb
        version: "aaaaaa"
        can_upgrade_to: "aaaaaa"
        bastion_enabled: true
        bastion_port: 3
        smtp_enabled: true
        zone: "aaaaaa"
"""

from ansible.module_utils.basic import (
    AnsibleModule,
    missing_required_lib,
)
from ansible_collections.quantumsheep.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_waitable_resource_argument_spec,
    scaleway_get_client_from_module,
    scaleway_pop_client_params,
    scaleway_pop_waitable_resource_params,
)

try:
    from scaleway import Client, ScalewayException

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False

from scaleway.vpcgw.v1 import VpcgwV1API


def create(module: AnsibleModule, client: Client) -> None:
    api = VpcgwV1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_gateway(gateway_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_gateway(**module.params)
    resource = api.wait_for_gateway(
        gateway_id=resource.id, region=module.params["region"]
    )

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = VpcgwV1API(client)

    id = module.params["id"]
    name = module.params["name"]

    if id is not None:
        resource = api.get_gateway(gateway_id=id, region=module.params["region"])
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_gateway(gateway_id=resource.id, region=module.params["region"])

    try:
        api.wait_for_gateway(gateway_id=resource.id, region=module.params["region"])
    except ScalewayException as e:
        if e.status_code != 404:
            raise e

    module.exit_json(
        changed=True,
        msg=f"vpcgw's gateway {resource.name} ({resource.id}) deleted",
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
        type_=dict(type="str", required=True),
        enable_smtp=dict(type="bool", required=True),
        enable_bastion=dict(type="bool", required=True),
        zone=dict(type="str", required=False),
        project_id=dict(type="str", required=False),
        name=dict(type="str", required=False),
        tags=dict(type="list", required=False),
        upstream_dns_servers=dict(type="list", required=False),
        ip_id=dict(type="str", required=False),
        bastion_port=dict(type="int", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
