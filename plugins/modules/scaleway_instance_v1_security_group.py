#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_instance_v1_security_group
short_description: Manage Scaleway instance_v1's security_group
description:
    - This module can be used to manage Scaleway instance_v1's security_group.
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
    security_group_id:
        description: security_group_id
        type: str
        required: false
    description:
        description: description
        type: str
        required: true
    stateful:
        description: stateful
        type: bool
        required: true
    inbound_default_policy:
        description: inbound_default_policy
        type: str
        required: true
        choices:
            - accept
            - drop
    outbound_default_policy:
        description: outbound_default_policy
        type: str
        required: true
        choices:
            - accept
            - drop
    zone:
        description: zone
        type: str
        required: false
    name:
        description: name
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
    organization_default:
        description: organization_default
        type: bool
        required: false
    project_default:
        description: project_default
        type: bool
        required: false
    enable_default_security:
        description: enable_default_security
        type: bool
        required: false
"""

EXAMPLES = r"""
- name: Create a security_group
  scaleway.scaleway.scaleway_instance_v1_security_group:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
    description: "aaaaaa"
    stateful: true
    inbound_default_policy: "aaaaaa"
    outbound_default_policy: "aaaaaa"
"""

RETURN = r"""
---
security_group:
    description: The security_group information
    returned: when I(state=present)
    type: dict
    sample:
        security_group:
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

    resource_id = module.params.pop("security_group_id", None)
    if id is not None:
        resource = api.get_security_group(security_group_id=resource_id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_security_group(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = InstanceV1API(client)

    resource_id = module.params.pop("security_group", None)

    if resource_id is not None:
        resource = api.get_security_group(
            security_group_id=resource_id,
            zone=module.params["zone"],
        )
    elif module.params.get("name", None) is not None:
        resources = api.list_security_groups_all(
            name=module.params["name"],
            zone=module.params["zone"],
        )
        if len(resources) == 0:
            module.exit_json(msg="No security_group found with name {name}")
        elif len(resources) > 1:
            module.exit_json(msg="More than one security_group found with name {name}")
        else:
            resource = resources[0]
    else:
        module.fail_json(msg="security_group is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_security_group(
        security_group_id=resource.id,
        zone=resource.zone,
    )

    module.exit_json(
        changed=True,
        msg=f"instance_v1's security_group {resource.security_group} deleted",
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
        security_group_id=dict(type="str"),
        description=dict(
            type="str",
            required=True,
        ),
        stateful=dict(
            type="bool",
            required=True,
        ),
        inbound_default_policy=dict(
            type="str",
            required=True,
            choices=["accept", "drop"],
        ),
        outbound_default_policy=dict(
            type="str",
            required=True,
            choices=["accept", "drop"],
        ),
        zone=dict(
            type="str",
            required=False,
        ),
        name=dict(
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
        ),
        organization_default=dict(
            type="bool",
            required=False,
        ),
        project_default=dict(
            type="bool",
            required=False,
        ),
        enable_default_security=dict(
            type="bool",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["security_group_id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
