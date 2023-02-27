#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_k8s_pool
short_description: Manage Scaleway k8s's pool
description:
    - This module can be used to manage Scaleway k8s's pool.
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
    cluster_id:
        type: str
        required: true
    node_type:
        type: str
        required: true
    autoscaling:
        type: bool
        required: true
    size:
        type: int
        required: true
    container_runtime:
        type: str
        required: true
        choices:
            - unknown_runtime
            - docker
            - containerd
            - crio
    autohealing:
        type: bool
        required: true
    root_volume_type:
        type: str
        required: true
        choices:
            - default_volume_type
            - l_ssd
            - b_ssd
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
    placement_group_id:
        type: str
        required: false
    min_size:
        type: int
        required: false
    max_size:
        type: int
        required: false
    tags:
        type: list
        required: false
    kubelet_args:
        type: dict
        required: false
    upgrade_policy:
        type: dict
        required: false
    zone:
        type: str
        required: false
    root_volume_size:
        type: int
        required: false
"""

RETURN = r"""
---
pool:
    description: The pool information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        cluster_id: 00000000-0000-0000-0000-000000000000
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
        name: "aaaaaa"
        status: ready
        version: "aaaaaa"
        node_type: "aaaaaa"
        autoscaling: true
        size: 3
        min_size: 3
        max_size: 3
        container_runtime: docker
        autohealing: true
        tags:
            - aaaaaa
            - bbbbbb
        placement_group_id: 00000000-0000-0000-0000-000000000000
        kubelet_args:
            aaaaaa: bbbbbb
            cccccc: dddddd
        upgrade_policy:
            aaaaaa: bbbbbb
            cccccc: dddddd
        zone: "aaaaaa"
        root_volume_type: default_volume_type
        root_volume_size: 3
        region: fr-par
"""

from ansible.module_utils.basic import (
    AnsibleModule,
    missing_required_lib,
)
from ansible_collections.quantumsheep.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_waitable_resource_argument_spec,
    scaleway_get_client_from_module,
    scaleway_pop_client_params,
    scaleway_pop_waitable_resource_params,
)

try:
    from scaleway import Client, ScalewayException

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False

from scaleway.k8s.v1 import K8SV1API


def create(module: AnsibleModule, client: Client) -> None:
    api = K8SV1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_pool(pool_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_pool(**module.params)
    resource = api.wait_for_pool(pool_id=resource.id, region=module.params["region"])

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = K8SV1API(client)

    id = module.params["id"]
    name = module.params["name"]

    if id is not None:
        resource = api.get_pool(pool_id=id, region=module.params["region"])
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
        id=dict(type="str"),
        cluster_id=dict(type="str", required=True),
        node_type=dict(type="str", required=True),
        autoscaling=dict(type="bool", required=True),
        size=dict(type="int", required=True),
        container_runtime=dict(
            type="str",
            required=True,
            choices=["unknown_runtime", "docker", "containerd", "crio"],
        ),
        autohealing=dict(type="bool", required=True),
        root_volume_type=dict(
            type="str", required=True, choices=["default_volume_type", "l_ssd", "b_ssd"]
        ),
        region=dict(type="str", required=False, choices=["fr-par", "nl-ams", "pl-waw"]),
        name=dict(type="str", required=False),
        placement_group_id=dict(type="str", required=False),
        min_size=dict(type="int", required=False),
        max_size=dict(type="int", required=False),
        tags=dict(type="list", required=False),
        kubelet_args=dict(type="dict", required=False),
        upgrade_policy=dict(type="dict", required=False),
        zone=dict(type="str", required=False),
        root_volume_size=dict(type="int", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
