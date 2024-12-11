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
    from scaleway.iam.v1alpha1 import IamV1Alpha1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = IamV1Alpha1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_ssh_key(ssh_key_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_ssh_key(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = IamV1Alpha1API(client)

    id = module.params.pop("id", None)
    name = module.params.pop("name", None)

    if id is not None:
        resource = api.get_ssh_key(ssh_key_id=id, region=module.params["region"])
    elif name is not None:
        resources = api.list_ssh_keys_all(name=name, region=module.params["region"])
        if len(resources) == 0:
            module.exit_json(msg="No ssh_key found with name {name}")
        elif len(resources) > 1:
            module.exit_json(msg="More than one ssh_key found with name {name}")
        else:
            resource = resources[0]
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_ssh_key(ssh_key_id=resource.id, region=module.params["region"])

    module.exit_json(
        changed=True,
        msg=f"iam's ssh_key {resource.name} ({resource.id}) deleted",
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
        ssh_key_id=dict(type="str", no_log=True),
        public_key=dict(
            type="str",
            required=True,
            no_log=True,
        ),
        name=dict(
            type="str",
            required=False,
        ),
        project_id=dict(
            type="str",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["ssh_key_id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
