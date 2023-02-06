from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_iot_device
short_description: Manage Scaleway iot's device
description:
    - This module can be used to manage Scaleway iot's device.
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
    hub_id:
        type: str
        required: true
    allow_insecure:
        type: bool
        required: true
    allow_multiple_connections:
        type: bool
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
    message_filters:
        type: dict
        required: false
    description:
        type: str
        required: false
"""

RETURN = r"""
---
device:
    description: The device information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        name: "aaaaaa"
        description: "aaaaaa"
        status: error
        hub_id: 00000000-0000-0000-0000-000000000000
        last_activity_at: "aaaaaa"
        is_connected: true
        allow_insecure: true
        allow_multiple_connections: true
        message_filters:
            aaaaaa: bbbbbb
            cccccc: dddddd
        has_custom_certificate: true
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
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
from scaleway.iot.v1 import IotV1API


def create(module: AnsibleModule, client: Client) -> None:
    api = IotV1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_device(device_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_device(**module.params)

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = IotV1API(client)

    id = module.params["id"]
    name = module.params["name"]

    if id is not None:
        resource = api.get_device(device_id=id)
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_device(device_id=resource.id)

    module.exit_json(
        changed=True,
        msg=f"iot's device {resource.name} ({resource.id}) deleted",
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
        hub_id=dict(type="str", required=True),
        allow_insecure=dict(type="bool", required=True),
        allow_multiple_connections=dict(type="bool", required=True),
        region=dict(type="str", required=False, choices=["fr-par", "nl-ams", "pl-waw"]),
        name=dict(type="str", required=False),
        message_filters=dict(type="dict", required=False),
        description=dict(type="str", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["id", "name"],),
        supports_check_mode=True,
    )

    core(module)


if __name__ == "__main__":
    main()
