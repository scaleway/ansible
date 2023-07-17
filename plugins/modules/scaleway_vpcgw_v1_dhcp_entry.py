#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_vpcgw_v1_dhcp_entry
short_description: Manage Scaleway vpcgw_v1's dhcp_entry
description:
    - This module can be used to manage Scaleway vpcgw_v1's dhcp_entry.
version_added: "2.1.0"
author:
    - Nathanael Demacon (@quantumsheep)
extends_documentation_fragment:
    - scaleway.scaleway.scaleway
    - scaleway.scaleway.scaleway_waitable_resource
requirements:
    - scaleway >= 0.6.0
options:
    state:
        description:
            - Indicate desired state of the target.
            - C(present) will create the resource.
            - C(absent) will delete the resource, if it exists.
        default: present
        choices: ["present", "absent"]
        type: str
    id:
        description: id
        type: str
        required: false
    gateway_network_id:
        description: gateway_network_id
        type: str
        required: true
    mac_address:
        description: mac_address
        type: str
        required: true
    ip_address:
        description: ip_address
        type: str
        required: true
    zone:
        description: zone
        type: str
        required: false
"""

EXAMPLES = r"""
- name: Create a dhcp_entry
  scaleway.scaleway.scaleway_vpcgw_v1_dhcp_entry:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
    gateway_network_id: "aaaaaa"
    mac_address: "aaaaaa"
    ip_address: "aaaaaa"
"""

RETURN = r"""
---
dhcp_entry:
    description: The dhcp_entry information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
        gateway_network_id: 00000000-0000-0000-0000-000000000000
        mac_address: "aaaaaa"
        ip_address: "aaaaaa"
        hostname: "aaaaaa"
        type_: reservation
        zone: "aaaaaa"
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
    from scaleway.vpcgw.v1 import VpcgwV1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = VpcgwV1API(client)

    resource_id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_dhcp_entry(dhcp_entry_id=resource_id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_dhcp_entry(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = VpcgwV1API(client)

    resource_id = module.params.pop("id", None)

    if resource_id is not None:
        resource = api.get_dhcp_entry(
            dhcp_entry_id=resource_id,
            zone=module.params["zone"],
        )
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_dhcp_entry(
        dhcp_entry_id=resource.id,
        zone=resource.zone,
    )

    module.exit_json(
        changed=True,
        msg=f"vpcgw_v1's dhcp_entry {resource.id} deleted",
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
        dhcp_entry_id=dict(type="str"),
        gateway_network_id=dict(
            type="str",
            required=True,
        ),
        mac_address=dict(
            type="str",
            required=True,
        ),
        ip_address=dict(
            type="str",
            required=True,
        ),
        zone=dict(
            type="str",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
