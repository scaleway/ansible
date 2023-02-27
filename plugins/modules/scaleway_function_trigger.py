from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_function_trigger
short_description: Manage Scaleway function's trigger
description:
    - This module can be used to manage Scaleway function's trigger.
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
    name:
        type: str
        required: true
    description:
        type: str
        required: true
    function_id:
        type: str
        required: true
    type_:
        type: str
        required: true
        choices:
            - unknown_trigger_type
            - nats
            - sqs
    region:
        type: str
        required: false
        choices:
            - fr-par
            - nl-ams
            - pl-waw
    nats_failure_handling_policy:
        type: dict
        required: false
    sqs_failure_handling_policy:
        type: dict
        required: false
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
        type_: nats
        status: ready
        error_message: "aaaaaa"
        function_id: 00000000-0000-0000-0000-000000000000
        nats_failure_handling_policy:
            aaaaaa: bbbbbb
            cccccc: dddddd
        sqs_failure_handling_policy:
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
from scaleway.function.v1beta1 import FunctionV1Beta1API


def create(module: AnsibleModule, client: Client) -> None:
    api = FunctionV1Beta1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_trigger(trigger_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_trigger(**module.params)
    resource = api.wait_for_trigger(trigger_id=resource.id)

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = FunctionV1Beta1API(client)

    id = module.params["id"]
    name = module.params["name"]

    if id is not None:
        resource = api.get_trigger(trigger_id=id)
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_trigger(trigger_id=resource.id)

    try:
        api.wait_for_trigger(trigger_id=resource.id)
    except ScalewayException as e:
        if e.status_code != 404:
            raise e

    module.exit_json(
        changed=True,
        msg=f"function's trigger {resource.name} ({resource.id}) deleted",
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
        name=dict(type="str", required=True),
        description=dict(type="str", required=True),
        function_id=dict(type="str", required=True),
        type_=dict(
            type="str", required=True, choices=["unknown_trigger_type", "nats", "sqs"]
        ),
        region=dict(type="str", required=False, choices=["fr-par", "nl-ams", "pl-waw"]),
        nats_failure_handling_policy=dict(type="dict", required=False),
        sqs_failure_handling_policy=dict(type="dict", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["id", "name"],),
        supports_check_mode=True,
    )

    core(module)


if __name__ == "__main__":
    main()
