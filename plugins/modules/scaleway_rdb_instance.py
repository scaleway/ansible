#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


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
    from scaleway import Client, ScalewayException
    from scaleway.rdb.v1 import RdbV1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = RdbV1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_instance(instance_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_instance(**not_none_params)
    resource = api.wait_for_instance(
        instance_id=resource.id, region=module.params["region"]
    )

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = RdbV1API(client)

    id = module.params.pop("id", None)
    name = module.params.pop("name", None)

    if id is not None:
        resource = api.get_instance(instance_id=id, region=module.params["region"])
    elif name is not None:
        resources = api.list_instances_all(name=name, region=module.params["region"])
        if len(resources) == 0:
            module.exit_json(msg="No instance found with name {name}")
        elif len(resources) > 1:
            module.exit_json(msg="More than one instance found with name {name}")
        else:
            resource = resources[0]
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_instance(instance_id=resource.id, region=module.params["region"])

    try:
        api.wait_for_instance(instance_id=resource.id, region=module.params["region"])
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
        instance_id=dict(type="str"),
        engine=dict(
            type="str",
            required=True,
        ),
        user_name=dict(
            type="str",
            required=True,
        ),
        password=dict(
            type="str",
            required=True,
            no_log=True,
        ),
        node_type=dict(
            type="str",
            required=True,
        ),
        is_ha_cluster=dict(
            type="bool",
            required=True,
        ),
        disable_backup=dict(
            type="bool",
            required=True,
        ),
        volume_type=dict(
            type="str",
            required=True,
            choices=["lssd", "bssd"],
        ),
        volume_size=dict(
            type="int",
            required=True,
        ),
        backup_same_region=dict(
            type="bool",
            required=True,
        ),
        region=dict(
            type="str",
            required=False,
            choices=["fr-par", "nl-ams", "pl-waw"],
        ),
        organization_id=dict(
            type="str",
            required=False,
        ),
        project_id=dict(
            type="str",
            required=False,
        ),
        name=dict(
            type="str",
            required=False,
        ),
        tags=dict(
            type="list",
            required=False,
            elements="str",
        ),
        init_settings=dict(
            type="list",
            required=False,
            elements="str",
        ),
        init_endpoints=dict(
            type="list",
            required=False,
            elements="str",
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["instance_id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
