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
    from scaleway.k8s.v1 import K8SV1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = K8SV1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_pool(pool_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_pool(**not_none_params)
    resource = api.wait_for_pool(pool_id=resource.id, region=module.params["region"])

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = K8SV1API(client)

    id = module.params.pop("id", None)
    name = module.params.pop("name", None)

    if id is not None:
        resource = api.get_pool(pool_id=id, region=module.params["region"])
    elif name is not None:
        resources = api.list_pools_all(name=name, region=module.params["region"])
        if len(resources) == 0:
            module.exit_json(msg="No pool found with name {name}")
        elif len(resources) > 1:
            module.exit_json(msg="More than one pool found with name {name}")
        else:
            resource = resources[0]
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_pool(pool_id=resource.id, region=module.params["region"])

    try:
        api.wait_for_pool(pool_id=resource.id, region=module.params["region"])
    except ScalewayException as e:
        if e.status_code != 404:
            raise e

    module.exit_json(
        changed=True,
        msg=f"k8s's pool {resource.name} ({resource.id}) deleted",
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
        pool_id=dict(type="str"),
        cluster_id=dict(
            type="str",
            required=True,
        ),
        node_type=dict(
            type="str",
            required=True,
        ),
        autoscaling=dict(
            type="bool",
            required=True,
        ),
        size=dict(
            type="int",
            required=True,
        ),
        container_runtime=dict(
            type="str",
            required=True,
            choices=["unknown_runtime", "docker", "containerd", "crio"],
        ),
        autohealing=dict(
            type="bool",
            required=True,
        ),
        root_volume_type=dict(
            type="str",
            required=True,
            choices=["default_volume_type", "l_ssd", "b_ssd"],
        ),
        region=dict(
            type="str",
            required=False,
            choices=["fr-par", "nl-ams", "pl-waw"],
        ),
        name=dict(
            type="str",
            required=False,
        ),
        placement_group_id=dict(
            type="str",
            required=False,
        ),
        min_size=dict(
            type="int",
            required=False,
        ),
        max_size=dict(
            type="int",
            required=False,
        ),
        tags=dict(
            type="list",
            required=False,
            elements="str",
        ),
        kubelet_args=dict(
            type="dict",
            required=False,
        ),
        upgrade_policy=dict(
            type="dict",
            required=False,
        ),
        zone=dict(
            type="str",
            required=False,
        ),
        root_volume_size=dict(
            type="int",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["pool_id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
