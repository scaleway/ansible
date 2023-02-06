from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_flexibleip_flexible_ip
short_description: Manage Scaleway flexibleip's flexible_ip
description:
    - This module can be used to manage Scaleway flexibleip's flexible_ip.
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
    description:
        type: str
        required: true
    is_ipv6:
        type: bool
        required: true
    zone:
        type: str
        required: false
    project_id:
        type: str
        required: false
    tags:
        type: list
        required: false
    server_id:
        type: str
        required: false
    reverse:
        type: str
        required: false
"""

RETURN = r"""
---
flexible_ip:
    description: The flexible_ip information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        organization_id: 00000000-0000-0000-0000-000000000000
        project_id: 00000000-0000-0000-0000-000000000000
        description: "aaaaaa"
        tags:
            - aaaaaa
            - bbbbbb
        updated_at: "aaaaaa"
        created_at: "aaaaaa"
        status: ready
        ip_address: "aaaaaa"
        mac_address:
            aaaaaa: bbbbbb
            cccccc: dddddd
        server_id: 00000000-0000-0000-0000-000000000000
        reverse: "aaaaaa"
        zone: "aaaaaa"
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
from scaleway.flexibleip.v1alpha1 import FlexibleipV1Alpha1API


def create(module: AnsibleModule, client: Client) -> None:
    api = FlexibleipV1Alpha1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_flexible_ip(flexible_ip_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_flexible_ip(**module.params)
    resource = api.wait_for_flexible_ip(flexible_ip_id=resource.id)

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = FlexibleipV1Alpha1API(client)

    id = module.params["id"]
    name = module.params["name"]

    if id is not None:
        resource = api.get_flexible_ip(flexible_ip_id=id)
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_flexible_ip(flexible_ip_id=resource.id)

    try:
        api.wait_for_flexible_ip(flexible_ip_id=resource.id)
    except ScalewayException as e:
        if e.status_code != 404:
            raise e

    module.exit_json(
        changed=True,
        msg=f"flexibleip's flexible_ip {resource.name} ({resource.id}) deleted",
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
        description=dict(type="str", required=True),
        is_ipv6=dict(type="bool", required=True),
        zone=dict(type="str", required=False),
        project_id=dict(type="str", required=False),
        tags=dict(type="list", required=False),
        server_id=dict(type="str", required=False),
        reverse=dict(type="str", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    core(module)


if __name__ == "__main__":
    main()