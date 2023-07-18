#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_rdb_v1_read_replica
short_description: Manage Scaleway rdb_v1's read_replica
description:
    - This module can be used to manage Scaleway rdb_v1's read_replica.
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
    read_replica_id:
        description: read_replica_id
        type: str
        required: false
    instance_id:
        description: instance_id
        type: str
        required: true
    region:
        description: region
        type: str
        required: false
        choices:
            - fr-par
            - nl-ams
            - pl-waw
    endpoint_spec:
        description: endpoint_spec
        type: list
        elements: str
        required: false
    same_zone:
        description: same_zone
        type: bool
        required: false
"""

EXAMPLES = r"""
- name: Create a read_replica
  scaleway.scaleway.scaleway_rdb_v1_read_replica:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
    instance_id: "aaaaaa"
"""

RETURN = r"""
---
read_replica:
    description: The read_replica information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        endpoints:
            - aaaaaa
            - bbbbbb
        status: provisioning
        region: fr-par
        same_zone: true
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
    from scaleway.rdb.v1 import RdbV1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = RdbV1API(client)

    resource_id = module.params.pop("read_replica_id", None)
    if id is not None:
        resource = api.get_read_replica(read_replica_id=resource_id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_read_replica(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = RdbV1API(client)

    resource_id = module.params.pop("id", None)

    if resource_id is not None:
        resource = api.get_read_replica(
            read_replica_id=resource_id,
            region=module.params["region"],
        )
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_read_replica(
        read_replica_id=resource.id,
        region=resource.region,
    )

    module.exit_json(
        changed=True,
        msg=f"rdb_v1's read_replica {resource.id} deleted",
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
        read_replica_id=dict(type="str"),
        instance_id=dict(
            type="str",
            required=True,
        ),
        region=dict(
            type="str",
            required=False,
            choices=["fr-par", "nl-ams", "pl-waw"],
        ),
        endpoint_spec=dict(
            type="list",
            required=False,
            elements="str",
        ),
        same_zone=dict(
            type="bool",
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
