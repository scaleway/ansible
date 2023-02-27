from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_k8s_cluster
short_description: Manage Scaleway k8s's cluster
description:
    - This module can be used to manage Scaleway k8s's cluster.
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
    type_:
        type: str
        required: true
    description:
        type: str
        required: true
    version:
        type: str
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
    cni:
        type: str
        required: true
        choices:
            - unknown_cni
            - cilium
            - calico
            - weave
            - flannel
            - kilo
    enable_dashboard:
        type: bool
        required: false
    ingress:
        type: str
        required: false
        choices:
            - unknown_ingress
            - none
            - nginx
            - traefik
            - traefik2
    pools:
        type: list
        required: false
    autoscaler_config:
        type: dict
        required: false
    auto_upgrade:
        type: dict
        required: false
    feature_gates:
        type: list
        required: false
    admission_plugins:
        type: list
        required: false
    open_id_connect_config:
        type: dict
        required: false
    apiserver_cert_sans:
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
        type_: "aaaaaa"
        name: "aaaaaa"
        status: creating
        version: "aaaaaa"
        region: fr-par
        organization_id: 00000000-0000-0000-0000-000000000000
        project_id: 00000000-0000-0000-0000-000000000000
        tags:
            - aaaaaa
            - bbbbbb
        cni: cilium
        description: "aaaaaa"
        cluster_url: "aaaaaa"
        dns_wildcard: "aaaaaa"
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
        autoscaler_config:
            aaaaaa: bbbbbb
            cccccc: dddddd
        dashboard_enabled: true
        ingress: none
        auto_upgrade:
            aaaaaa: bbbbbb
            cccccc: dddddd
        upgrade_available: true
        feature_gates:
            - aaaaaa
            - bbbbbb
        admission_plugins:
            - aaaaaa
            - bbbbbb
        open_id_connect_config: 00000000-0000-0000-0000-000000000000
        apiserver_cert_sans:
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
from scaleway.k8s.v1 import K8SV1API


def create(module: AnsibleModule, client: Client) -> None:
    api = K8SV1API(client)

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
    api = K8SV1API(client)

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
        msg=f"k8s's cluster {resource.name} ({resource.id}) deleted",
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
        type_=dict(type="str", required=True),
        description=dict(type="str", required=True),
        version=dict(type="str", required=True),
        region=dict(type="str", required=False, choices=["fr-par", "nl-ams", "pl-waw"]),
        organization_id=dict(type="str", required=False),
        project_id=dict(type="str", required=False),
        name=dict(type="str", required=False),
        tags=dict(type="list", required=False),
        cni=dict(
            type="str",
            required=True,
            choices=["unknown_cni", "cilium", "calico", "weave", "flannel", "kilo"],
        ),
        enable_dashboard=dict(type="bool", required=False),
        ingress=dict(
            type="str",
            required=False,
            choices=["unknown_ingress", "none", "nginx", "traefik", "traefik2"],
        ),
        pools=dict(type="list", required=False),
        autoscaler_config=dict(type="dict", required=False),
        auto_upgrade=dict(type="dict", required=False),
        feature_gates=dict(type="list", required=False),
        admission_plugins=dict(type="list", required=False),
        open_id_connect_config=dict(type="dict", required=False),
        apiserver_cert_sans=dict(type="list", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["id", "name"],),
        supports_check_mode=True,
    )

    core(module)


if __name__ == "__main__":
    main()
