from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_rdb_instance
short_description: Manage Scaleway rdb's instance
description:
    - This module can be used to manage Scaleway rdb's instance.
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
        type: str
        required: false
    engine:
        type: str
        required: true
    user_name:
        type: str
        required: true
    password:
        type: str
        required: true
    node_type:
        type: str
        required: true
    is_ha_cluster:
        type: bool
        required: true
    disable_backup:
        type: bool
        required: true
    volume_type:
        type: str
        required: true
        choices:
            - lssd
            - bssd
    volume_size:
        type: int
        required: true
    backup_same_region:
        type: bool
        required: true
    region:
        type: str
        required: false
        choices:
            - fr-par
            - nl-ams
            - pl-waw
    organization_id:
        type: str
        required: false
    project_id:
        type: str
        required: false
    name:
        type: str
        required: false
    tags:
        type: list
        required: false
    init_settings:
        type: list
        required: false
    init_endpoints:
        type: list
        required: false
"""

RETURN = r"""
---
instance:
    description: The instance information
    returned: when I(state=present)
    type: dict
    sample:
        created_at: "aaaaaa"
        volume:
            aaaaaa: bbbbbb
            cccccc: dddddd
        region: fr-par
        id: 00000000-0000-0000-0000-000000000000
        name: "aaaaaa"
        organization_id: 00000000-0000-0000-0000-000000000000
        project_id: 00000000-0000-0000-0000-000000000000
        status: ready
        engine: "aaaaaa"
        upgradable_version:
            - aaaaaa
            - bbbbbb
        endpoint:
            aaaaaa: bbbbbb
            cccccc: dddddd
        tags:
            - aaaaaa
            - bbbbbb
        settings:
            - aaaaaa
            - bbbbbb
        backup_schedule:
            aaaaaa: bbbbbb
            cccccc: dddddd
        is_ha_cluster: true
        read_replicas:
            - aaaaaa
            - bbbbbb
        node_type: "aaaaaa"
        init_settings:
            - aaaaaa
            - bbbbbb
        endpoints:
            - aaaaaa
            - bbbbbb
        logs_policy:
            aaaaaa: bbbbbb
            cccccc: dddddd
        backup_same_region: true
        maintenances:
            - aaaaaa
            - bbbbbb
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
from scaleway.rdb.v1 import RdbV1API


def create(module: AnsibleModule, client: Client) -> None:
    api = RdbV1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_instance(instance_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_instance(**module.params)
    resource = api.wait_for_instance(instance_id=resource.id)

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = RdbV1API(client)

    id = module.params["id"]
    name = module.params["name"]

    if id is not None:
        resource = api.get_instance(instance_id=id)
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_instance(instance_id=resource.id)

    try:
        api.wait_for_instance(instance_id=resource.id)
    except ScalewayException as e:
        if e.status_code != 404:
            raise e

    module.exit_json(
        changed=True,
        msg=f"rdb's instance {resource.name} ({resource.id}) deleted",
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
        engine=dict(type="str", required=True),
        user_name=dict(type="str", required=True),
        password=dict(type="str", required=True),
        node_type=dict(type="str", required=True),
        is_ha_cluster=dict(type="bool", required=True),
        disable_backup=dict(type="bool", required=True),
        volume_type=dict(type="str", required=True, choices=["lssd", "bssd"]),
        volume_size=dict(type="int", required=True),
        backup_same_region=dict(type="bool", required=True),
        region=dict(type="str", required=False, choices=["fr-par", "nl-ams", "pl-waw"]),
        organization_id=dict(type="str", required=False),
        project_id=dict(type="str", required=False),
        name=dict(type="str", required=False),
        tags=dict(type="list", required=False),
        init_settings=dict(type="list", required=False),
        init_endpoints=dict(type="list", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["id", "name"],),
        supports_check_mode=True,
    )

    core(module)


if __name__ == "__main__":
    main()
