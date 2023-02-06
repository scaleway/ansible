from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_vpcgw_dhcp
short_description: Manage Scaleway vpcgw's dhcp
description:
    - This module can be used to manage Scaleway vpcgw's dhcp.
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
    subnet:
        type: str
        required: true
    zone:
        type: str
        required: false
    project_id:
        type: str
        required: false
    address:
        type: str
        required: false
    pool_low:
        type: str
        required: false
    pool_high:
        type: str
        required: false
    enable_dynamic:
        type: bool
        required: false
    valid_lifetime:
        type: str
        required: false
    renew_timer:
        type: str
        required: false
    rebind_timer:
        type: str
        required: false
    push_default_route:
        type: bool
        required: false
    push_dns_server:
        type: bool
        required: false
    dns_servers_override:
        type: list
        required: false
    dns_search:
        type: list
        required: false
    dns_local_name:
        type: str
        required: false
"""

RETURN = r"""
---
dhcp:
    description: The dhcp information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        organization_id: 00000000-0000-0000-0000-000000000000
        project_id: 00000000-0000-0000-0000-000000000000
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
        subnet: "aaaaaa"
        address: "aaaaaa"
        pool_low: "aaaaaa"
        pool_high: "aaaaaa"
        enable_dynamic: true
        valid_lifetime: 00000000-0000-0000-0000-000000000000
        renew_timer: "aaaaaa"
        rebind_timer: "aaaaaa"
        push_default_route: true
        push_dns_server: true
        dns_servers_override:
            - aaaaaa
            - bbbbbb
        dns_search:
            - aaaaaa
            - bbbbbb
        dns_local_name: "aaaaaa"
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
from scaleway.vpcgw.v1 import VpcgwV1API


def create(module: AnsibleModule, client: Client) -> None:
    api = VpcgwV1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_dhcp(dhcp_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_dhcp(**module.params)

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = VpcgwV1API(client)

    id = module.params["id"]
    name = module.params["name"]

    if id is not None:
        resource = api.get_dhcp(dhcp_id=id)
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_dhcp(dhcp_id=resource.id)

    module.exit_json(
        changed=True,
        msg=f"vpcgw's dhcp {resource.name} ({resource.id}) deleted",
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
        subnet=dict(type="str", required=True),
        zone=dict(type="str", required=False),
        project_id=dict(type="str", required=False),
        address=dict(type="str", required=False),
        pool_low=dict(type="str", required=False),
        pool_high=dict(type="str", required=False),
        enable_dynamic=dict(type="bool", required=False),
        valid_lifetime=dict(type="str", required=False),
        renew_timer=dict(type="str", required=False),
        rebind_timer=dict(type="str", required=False),
        push_default_route=dict(type="bool", required=False),
        push_dns_server=dict(type="bool", required=False),
        dns_servers_override=dict(type="list", required=False),
        dns_search=dict(type="list", required=False),
        dns_local_name=dict(type="str", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    core(module)


if __name__ == "__main__":
    main()
