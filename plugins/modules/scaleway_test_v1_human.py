#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_test_v1_human
short_description: Manage Scaleway test_v1's human
description:
    - This module can be used to manage Scaleway test_v1's human.
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
    human_id:
        description: human_id
        type: str
        required: false
    height:
        description: height
        type: float
        required: true
    shoe_size:
        description: shoe_size
        type: float
        required: true
    altitude_in_meter:
        description: altitude_in_meter
        type: int
        required: true
    altitude_in_millimeter:
        description: altitude_in_millimeter
        type: int
        required: true
    fingers_count:
        description: fingers_count
        type: int
        required: true
    hair_count:
        description: hair_count
        type: int
        required: true
    is_happy:
        description: is_happy
        type: bool
        required: true
    eyes_color:
        description: eyes_color
        type: str
        required: true
        choices:
            - unknown
            - amber
            - blue
            - brown
            - gray
            - green
            - hazel
            - red
            - violet
    name:
        description: name
        type: str
        required: true
    organization_id:
        description: organization_id
        type: str
        required: false
    project_id:
        description: project_id
        type: str
        required: false
"""

EXAMPLES = r"""
- name: Create a human
  scaleway.scaleway.scaleway_test_v1_human:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
    height: "aaaaaa"
    shoe_size: "aaaaaa"
    altitude_in_meter: "aaaaaa"
    altitude_in_millimeter: "aaaaaa"
    fingers_count: "aaaaaa"
    hair_count: "aaaaaa"
    is_happy: true
    eyes_color: "aaaaaa"
    name: "aaaaaa"
"""

RETURN = r"""
---
human:
    description: The human information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        organization_id: 00000000-0000-0000-0000-000000000000
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
        height: 3.14
        shoe_size: 3.14
        altitude_in_meter: 3
        altitude_in_millimeter: 3
        fingers_count: 3
        hair_count: 3
        is_happy: true
        eyes_color: amber
        status: stopped
        name: "aaaaaa"
        project_id: 00000000-0000-0000-0000-000000000000
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
    from scaleway.test.v1 import TestV1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = TestV1API(client)

    resource_id = module.params.pop("human_id", None)
    if id is not None:
        resource = api.get_human(human_id=resource_id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_human(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = TestV1API(client)

    resource_id = module.params.pop("id", None)

    if resource_id is not None:
        resource = api.get_human(
            human_id=resource_id,
        )
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_human(
        human_id=resource.id,
    )

    module.exit_json(
        changed=True,
        msg=f"test_v1's human {resource.name} ({resource.id}) deleted",
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
        human_id=dict(type="str"),
        height=dict(
            type="float",
            required=True,
        ),
        shoe_size=dict(
            type="float",
            required=True,
        ),
        altitude_in_meter=dict(
            type="int",
            required=True,
        ),
        altitude_in_millimeter=dict(
            type="int",
            required=True,
        ),
        fingers_count=dict(
            type="int",
            required=True,
        ),
        hair_count=dict(
            type="int",
            required=True,
        ),
        is_happy=dict(
            type="bool",
            required=True,
        ),
        eyes_color=dict(
            type="str",
            required=True,
            choices=["unknown", "amber", "blue", "brown", "gray", "green", "hazel", "red", "violet"],
        ),
        name=dict(
            type="str",
            required=True,
        ),
        organization_id=dict(
            type="str",
            required=False,
        ),
        project_id=dict(
            type="str",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["human_id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
