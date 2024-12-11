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
    from scaleway import Client
    from scaleway.lb.v1 import LbV1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = LbV1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_backend(backend_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_backend(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = LbV1API(client)

    id = module.params.pop("id", None)
    name = module.params.pop("name", None)

    if id is not None:
        resource = api.get_backend(backend_id=id, region=module.params["region"])
    elif name is not None:
        resources = api.list_backends_all(name=name, region=module.params["region"])
        if len(resources) == 0:
            module.exit_json(msg="No backend found with name {name}")
        elif len(resources) > 1:
            module.exit_json(msg="More than one backend found with name {name}")
        else:
            resource = resources[0]
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_backend(backend_id=resource.id, region=module.params["region"])

    module.exit_json(
        changed=True,
        msg=f"lb's backend {resource.name} ({resource.id}) deleted",
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
        backend_id=dict(type="str"),
        lb_id=dict(
            type="str",
            required=True,
        ),
        forward_port=dict(
            type="int",
            required=True,
        ),
        sticky_sessions_cookie_name=dict(
            type="str",
            required=True,
        ),
        health_check=dict(
            type="dict",
            required=True,
        ),
        server_ip=dict(
            type="list",
            required=True,
            elements="str",
        ),
        on_marked_down_action=dict(
            type="str",
            required=True,
            choices=["on_marked_down_action_none", "shutdown_sessions"],
        ),
        proxy_protocol=dict(
            type="str",
            required=True,
            choices=[
                "proxy_protocol_unknown",
                "proxy_protocol_none",
                "proxy_protocol_v1",
                "proxy_protocol_v2",
                "proxy_protocol_v2_ssl",
                "proxy_protocol_v2_ssl_cn",
            ],
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
        forward_protocol=dict(
            type="str",
            required=True,
            choices=["tcp", "http"],
        ),
        forward_port_algorithm=dict(
            type="str",
            required=True,
            choices=["roundrobin", "leastconn", "first"],
        ),
        sticky_sessions=dict(
            type="str",
            required=True,
            choices=["none", "cookie", "table"],
        ),
        send_proxy_v2=dict(
            type="bool",
            required=False,
        ),
        timeout_server=dict(
            type="str",
            required=False,
        ),
        timeout_connect=dict(
            type="str",
            required=False,
        ),
        timeout_tunnel=dict(
            type="str",
            required=False,
        ),
        failover_host=dict(
            type="str",
            required=False,
        ),
        ssl_bridging=dict(
            type="bool",
            required=False,
        ),
        ignore_ssl_server_verify=dict(
            type="bool",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["backend_id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
