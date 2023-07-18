#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_iot_v1_network
short_description: Manage Scaleway iot_v1's network
description:
    - This module can be used to manage Scaleway iot_v1's network.
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
    network_id:
        description: network_id
        type: str
        required: false
    hub_id:
        description: hub_id
        type: str
        required: true
    topic_prefix:
        description: topic_prefix
        type: str
        required: true
    region:
        description: region
        type: str
        required: false
        choices:
            - fr-par
            - nl-ams
            - pl-waw
    name:
        description: name
        type: str
        required: false
    type_:
        description: type_
        type: str
        required: false
        choices:
            - unknown
            - sigfox
            - rest
"""

EXAMPLES = r"""
- name: Create a network
  scaleway.scaleway.scaleway_iot_v1_network:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
    hub_id: "aaaaaa"
    topic_prefix: "aaaaaa"
"""

RETURN = r"""
---
network:
    description: The network information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        name: "aaaaaa"
        type_: sigfox
        endpoint: "aaaaaa"
        hub_id: 00000000-0000-0000-0000-000000000000
        created_at: "aaaaaa"
        topic_prefix: "aaaaaa"
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
    from scaleway.iot.v1 import IotV1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = IotV1API(client)

    resource_id = module.params.pop("network_id", None)
    if id is not None:
        resource = api.get_network(network_id=resource_id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_network(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = IotV1API(client)

    resource_id = module.params.pop("id", None)

    if resource_id is not None:
        resource = api.get_network(
            network_id=resource_id,
            region=module.params["region"],
        )
    elif module.params.get("name", None) is not None:
        resources = api.list_networks_all(
            name=module.params["name"],
            region=module.params["region"],
        )
        if len(resources) == 0:
            module.exit_json(msg="No network found with name {name}")
        elif len(resources) > 1:
            module.exit_json(msg="More than one network found with name {name}")
        else:
            resource = resources[0]
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_network(
        network_id=resource.id,
        region=resource.region,
    )

    module.exit_json(
        changed=True,
        msg=f"iot_v1's network {resource.name} ({resource.id}) deleted",
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
        network_id=dict(type="str"),
        hub_id=dict(
            type="str",
            required=True,
        ),
        topic_prefix=dict(
            type="str",
            required=True,
        ),
        region=dict(
            type="str",
            required=False,
            choices=["fr-par", "nl-ams", "pl-waw"],
        ),
        name=dict(
            type="str",
            required=False,
        ),
        type_=dict(
            type="str",
            required=False,
            choices=["unknown", "sigfox", "rest"],
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["network_id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
