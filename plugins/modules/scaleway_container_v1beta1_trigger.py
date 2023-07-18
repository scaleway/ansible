#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_container_v1beta1_trigger
short_description: Manage Scaleway container_v1beta1's trigger
description:
    - This module can be used to manage Scaleway container_v1beta1's trigger.
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
    trigger_id:
        description: trigger_id
        type: str
        required: false
    name:
        description: name
        type: str
        required: true
    container_id:
        description: container_id
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
    description:
        description: description
        type: str
        required: false
    scw_sqs_config:
        description: scw_sqs_config
        type: dict
        required: false
    sqs_config:
        description: sqs_config
        type: dict
        required: false
    scw_nats_config:
        description: scw_nats_config
        type: dict
        required: false
"""

EXAMPLES = r"""
- name: Create a trigger
  scaleway.scaleway.scaleway_container_v1beta1_trigger:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
    name: "aaaaaa"
    container_id: "aaaaaa"
"""

RETURN = r"""
---
trigger:
    description: The trigger information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        name: "aaaaaa"
        description: "aaaaaa"
        input_type: sqs
        status: ready
        error_message: "aaaaaa"
        container_id: 00000000-0000-0000-0000-000000000000
        scw_sqs_config:
            aaaaaa: bbbbbb
            cccccc: dddddd
        sqs_config:
            aaaaaa: bbbbbb
            cccccc: dddddd
        scw_nats_config:
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
    from scaleway.container.v1beta1 import ContainerV1Beta1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = ContainerV1Beta1API(client)

    resource_id = module.params.pop("trigger_id", None)
    if id is not None:
        resource = api.get_trigger(trigger_id=resource_id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_trigger(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = ContainerV1Beta1API(client)

    resource_id = module.params.pop("id", None)

    if resource_id is not None:
        resource = api.get_trigger(
            trigger_id=resource_id,
            region=module.params["region"],
        )
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_trigger(
        trigger_id=resource.id,
        region=resource.region,
    )

    module.exit_json(
        changed=True,
        msg=f"container_v1beta1's trigger {resource.name} ({resource.id}) deleted",
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
        trigger_id=dict(type="str"),
        name=dict(
            type="str",
            required=True,
        ),
        container_id=dict(
            type="str",
            required=True,
        ),
        region=dict(
            type="str",
            required=False,
            choices=["fr-par", "nl-ams", "pl-waw"],
        ),
        description=dict(
            type="str",
            required=False,
        ),
        scw_sqs_config=dict(
            type="dict",
            required=False,
        ),
        sqs_config=dict(
            type="dict",
            required=False,
        ),
        scw_nats_config=dict(
            type="dict",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["trigger_id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
