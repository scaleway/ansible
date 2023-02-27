from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_instance_snapshot
short_description: Manage Scaleway instance's snapshot
description:
    - This module can be used to manage Scaleway instance's snapshot.
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
    volume_type:
        type: str
        required: true
        choices:
            - unknown_volume_type
            - l_ssd
            - b_ssd
            - unified
    zone:
        type: str
        required: false
    name:
        type: str
        required: false
    volume_id:
        type: str
        required: false
    tags:
        type: list
        required: false
    organization:
        type: str
        required: false
    project:
        type: str
        required: false
    bucket:
        type: str
        required: false
    key:
        type: str
        required: false
    size:
        type: int
        required: false
"""

RETURN = r"""
---
snapshot:
    description: The snapshot information
    returned: when I(state=present)
    type: dict
    sample:
        snapshot:
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
        resource = api.get_snapshot(snapshot_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_snapshot(**module.params)

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = InstanceV1API(client)

    snapshot = module.params["snapshot"]

    if snapshot is not None:
        resource = api.get_snapshot(snapshot_id=snapshot)
    else:
        module.fail_json(msg="snapshot is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_snapshot(snapshot_id=resource.snapshot)

    module.exit_json(
        changed=True,
        msg=f"instance's snapshot {resource.snapshot} deleted",
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
        volume_type=dict(
            type="str",
            required=True,
            choices=["unknown_volume_type", "l_ssd", "b_ssd", "unified"],
        ),
        zone=dict(type="str", required=False),
        name=dict(type="str", required=False),
        volume_id=dict(type="str", required=False),
        tags=dict(type="list", required=False),
        organization=dict(type="str", required=False),
        project=dict(type="str", required=False),
        bucket=dict(type="str", required=False),
        key=dict(type="str", required=False),
        size=dict(type="int", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    core(module)


if __name__ == "__main__":
    main()
