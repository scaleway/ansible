#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_rdb_database
short_description: Manage Scaleway rdb's database
description:
    - This module can be used to manage Scaleway rdb's database.
version_added: "2.6.0"
author:
    - Guillaume Rodriguez (@guillaume-ro-fr)
extends_documentation_fragment:
    - scaleway.scaleway.scaleway
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
    instance_id:
        description: instance_id
        type: str
        required: true
    name:
        description: name
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
"""

EXAMPLES = r"""
- name: Create a database
  scaleway.scaleway.scaleway_rdb_database:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
    instance_id: 00000000-0000-0000-0000-000000000000
    name: "aaaaaa"
    region: fr-par
"""

RETURN = r"""
---
instance:
    description: The database information
    returned: when I(state=present)
    type: dict
    sample:
        name: "aaaaaa"
        owner: "bbbbbb"
        managed: true
        size: 1000
"""

from ansible.module_utils.basic import (
    AnsibleModule,
    missing_required_lib,
)
from ansible_collections.scaleway.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_get_client_from_module,
    scaleway_pop_client_params,
)

try:
    from scaleway import Client, ScalewayException
    from scaleway.rdb.v1 import RdbV1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = RdbV1API(client)

    resources = api.list_databases(name=module.params["name"], instance_id=module.params["instance_id"], region=module.params["region"])

    if resources.total_count > 0:
        if module.check_mode:
            module.exit_json(changed=False)

        resource = resources.databases[0]

        module.exit_json(changed=False, data=resource.__dict__)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_database(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = RdbV1API(client)

    name = module.params["name"]

    resources = api.list_databases(name=name, instance_id=module.params["instance_id"], region=module.params["region"])
    if resources.total_count == 0:
        module.exit_json(msg="No database found with name {name}")
    elif resources.total_count > 1:
        module.exit_json(msg="More than one database found with name {name}")
    else:
        resource = resources.databases[0]

    if module.check_mode:
        module.exit_json(changed=True)

    try:
        api.delete_database(name=name, instance_id=module.params["instance_id"], region=module.params["region"])
    except ScalewayException as e:
        if e.status_code != 404:
            raise e

    module.exit_json(
        changed=True,
        msg=f"rdb's database {resource.name} ({resource.instance_id}) deleted",
    )


def core(module: AnsibleModule) -> None:
    client = scaleway_get_client_from_module(module)

    state = module.params.pop("state")
    scaleway_pop_client_params(module)

    if state == "present":
        create(module, client)
    elif state == "absent":
        delete(module, client)


def main() -> None:
    argument_spec = scaleway_argument_spec()
    argument_spec.update(
        state=dict(type="str", default="present", choices=["absent", "present"]),
        instance_id=dict(
            type="str",
            required=True,
        ),
        name=dict(
            type="str",
            required=True,
        ),
        region=dict(
            type="str",
            required=False,
            choices=["fr-par", "nl-ams", "pl-waw"],
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
