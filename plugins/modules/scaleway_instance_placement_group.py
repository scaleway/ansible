from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_instance_placement_group
short_description: Manage Scaleway instance's placement_group
description:
    - This module can be used to manage Scaleway instance's placement_group.
version_added: "2.1.0"
author:
    - Nathanael Demacon (@quantumsheep)
extends_documentation_fragment:
    - quantumsheep.scaleway.scaleway
    - quantumsheep.scaleway.scaleway_waitable_resource
requirements:
    - scaleway >= 0.5.0
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
        required: false
        type: str
    policy_mode:
        type: str
        required: true
        choices:
            - optional
            - enforced
    policy_type:
        type: str
        required: true
        choices:
            - max_availability
            - low_latency
    zone:
        type: str
        required: false
    name:
        type: str
        required: false
    organization:
        type: str
        required: false
    project:
        type: str
        required: false
    tags:
        type: list
        required: false
"""

RETURN = r"""
---
placement_group:
    description: The placement_group information
    returned: when I(state=present)
    type: dict
    sample:
        placement_group:
            aaaaaa: bbbbbb
            cccccc: dddddd
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
from scaleway.instance.v1 import InstanceV1API


def create(module: AnsibleModule, client: Client) -> None:
    api = InstanceV1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_placement_group(placement_group_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_placement_group(**module.params)

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = InstanceV1API(client)

    id = module.params["id"]
    name = module.params["name"]

    if id is not None:
        resource = api.get_placement_group(placement_group_id=id)
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_placement_group(placement_group_id=resource.id)

    module.exit_json(
        changed=True,
        msg=f"instance's placement_group {resource.name} ({resource.id}) deleted",
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
    # From DOCUMENTATION
    argument_spec.update(
        state=dict(type="str", default="present", choices=["absent", "present"]),
        id=dict(type="str"),
        policy_mode=dict(type="str", required=True, choices=["optional", "enforced"]),
        policy_type=dict(
            type="str", required=True, choices=["max_availability", "low_latency"]
        ),
        zone=dict(type="str", required=False),
        name=dict(type="str", required=False),
        organization=dict(type="str", required=False),
        project=dict(type="str", required=False),
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