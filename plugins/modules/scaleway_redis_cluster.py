from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_redis_cluster
short_description: Manage Scaleway redis's cluster
description:
    - This module can be used to manage Scaleway redis's cluster.
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
    version:
        type: str
        required: true
    node_type:
        type: str
        required: true
    user_name:
        type: str
        required: true
    password:
        type: str
        required: true
    tls_enabled:
        type: bool
        required: true
    zone:
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
    cluster_size:
        type: int
        required: false
    acl_rules:
        type: list
        required: false
    endpoints:
        type: list
        required: false
    cluster_settings:
        type: list
        required: false
"""

RETURN = r"""
---
cluster:
    description: The cluster information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        name: "aaaaaa"
        project_id: 00000000-0000-0000-0000-000000000000
        status: ready
        version: "aaaaaa"
        endpoints:
            - aaaaaa
            - bbbbbb
        tags:
            - aaaaaa
            - bbbbbb
        node_type: "aaaaaa"
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
        tls_enabled: true
        cluster_settings:
            - aaaaaa
            - bbbbbb
        acl_rules:
            - aaaaaa
            - bbbbbb
        cluster_size: 3
        zone: "aaaaaa"
        user_name: "aaaaaa"
        upgradable_versions:
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
from scaleway.redis.v1 import RedisV1API


def create(module: AnsibleModule, client: Client) -> None:
    api = RedisV1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_cluster(cluster_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_cluster(**module.params)
    resource = api.wait_for_cluster(cluster_id=resource.id)

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = RedisV1API(client)

    id = module.params["id"]
    name = module.params["name"]

    if id is not None:
        resource = api.get_cluster(cluster_id=id)
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_cluster(cluster_id=resource.id)

    try:
        api.wait_for_cluster(cluster_id=resource.id)
    except ScalewayException as e:
        if e.status_code != 404:
            raise e

    module.exit_json(
        changed=True,
        msg=f"redis's cluster {resource.name} ({resource.id}) deleted",
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
        version=dict(type="str", required=True),
        node_type=dict(type="str", required=True),
        user_name=dict(type="str", required=True),
        password=dict(type="str", required=True),
        tls_enabled=dict(type="bool", required=True),
        zone=dict(type="str", required=False),
        project_id=dict(type="str", required=False),
        name=dict(type="str", required=False),
        tags=dict(type="list", required=False),
        cluster_size=dict(type="int", required=False),
        acl_rules=dict(type="list", required=False),
        endpoints=dict(type="list", required=False),
        cluster_settings=dict(type="list", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["id", "name"],),
        supports_check_mode=True,
    )

    core(module)


if __name__ == "__main__":
    main()
