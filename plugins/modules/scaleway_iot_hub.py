from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_iot_hub
short_description: Manage Scaleway iot's hub
description:
    - This module can be used to manage Scaleway iot's hub.
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
    project_id:
        type: str
        required: false
    product_plan:
        type: str
        required: true
        choices:
            - plan_unknown
            - plan_shared
            - plan_dedicated
            - plan_ha
    disable_events:
        type: bool
        required: false
    events_topic_prefix:
        type: str
        required: false
    twins_graphite_config:
        type: dict
        required: false
"""

RETURN = r"""
---
hub:
    description: The hub information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        name: "aaaaaa"
        status: error
        product_plan: plan_shared
        enabled: true
        device_count: 3
        connected_device_count: 3
        endpoint: "aaaaaa"
        disable_events: true
        events_topic_prefix: "aaaaaa"
        region: fr-par
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
        project_id: 00000000-0000-0000-0000-000000000000
        organization_id: 00000000-0000-0000-0000-000000000000
        enable_device_auto_provisioning: true
        has_custom_ca: true
        twins_graphite_config:
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
from scaleway.iot.v1 import IotV1API


def create(module: AnsibleModule, client: Client) -> None:
    api = IotV1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_hub(hub_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_hub(**module.params)
    resource = api.wait_for_hub(hub_id=resource.id)

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = IotV1API(client)

    id = module.params["id"]
    name = module.params["name"]

    if id is not None:
        resource = api.get_hub(hub_id=id)
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_hub(hub_id=resource.id)

    try:
        api.wait_for_hub(hub_id=resource.id)
    except ScalewayException as e:
        if e.status_code != 404:
            raise e

    module.exit_json(
        changed=True,
        msg=f"iot's hub {resource.name} ({resource.id}) deleted",
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
        region=dict(type="str", required=False, choices=["fr-par", "nl-ams", "pl-waw"]),
        name=dict(type="str", required=False),
        project_id=dict(type="str", required=False),
        product_plan=dict(
            type="str",
            required=True,
            choices=["plan_unknown", "plan_shared", "plan_dedicated", "plan_ha"],
        ),
        disable_events=dict(type="bool", required=False),
        events_topic_prefix=dict(type="str", required=False),
        twins_graphite_config=dict(type="dict", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["id", "name"],),
        supports_check_mode=True,
    )

    core(module)


if __name__ == "__main__":
    main()
