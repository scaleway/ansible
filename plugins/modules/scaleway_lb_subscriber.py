from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_lb_subscriber
short_description: Manage Scaleway lb's subscriber
description:
    - This module can be used to manage Scaleway lb's subscriber.
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
    name:
        type: str
        required: true
    region:
        type: str
        required: false
        choices:
            - fr-par
            - nl-ams
            - pl-waw
    email_config:
        type: dict
        required: false
    webhook_config:
        type: dict
        required: false
    organization_id:
        type: str
        required: false
    project_id:
        type: str
        required: false
"""

RETURN = r"""
---
subscriber:
    description: The subscriber information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        name: "aaaaaa"
        email_config:
            aaaaaa: bbbbbb
            cccccc: dddddd
        webhook_config:
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
from scaleway.lb.v1 import LbV1API


def create(module: AnsibleModule, client: Client) -> None:
    api = LbV1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_subscriber(subscriber_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_subscriber(**module.params)

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = LbV1API(client)

    id = module.params["id"]
    name = module.params["name"]

    if id is not None:
        resource = api.get_subscriber(subscriber_id=id)
    elif name is not None:
        resources = api.list_subscribers_all(
            namespace_id=module.params["namespace_id"],
            name=name,
        )
        if len(resources) == 0:
            module.exit_json(changed=False, msg="subscriber not found")

        resource = resources[0]

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_subscriber(subscriber_id=resource.id)

    module.exit_json(
        changed=True,
        msg=f"lb's subscriber {resource.name} ({resource.id}) deleted",
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
        name=dict(type="str", required=True),
        region=dict(type="str", required=False, choices=["fr-par", "nl-ams", "pl-waw"]),
        email_config=dict(type="dict", required=False),
        webhook_config=dict(type="dict", required=False),
        organization_id=dict(type="str", required=False),
        project_id=dict(type="str", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["id", "name"],),
        supports_check_mode=True,
    )

    core(module)


if __name__ == "__main__":
    main()
