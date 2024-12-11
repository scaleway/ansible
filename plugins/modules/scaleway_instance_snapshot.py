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
    from scaleway.instance.v1 import InstanceV1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = InstanceV1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_snapshot(snapshot_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_snapshot(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = InstanceV1API(client)

    snapshot = module.params.pop("snapshot", None)

    if snapshot is not None:
        resource = api.get_snapshot(
            snapshot_id=snapshot, region=module.params["region"]
        )
    else:
        module.fail_json(msg="snapshot is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_snapshot(snapshot_id=resource.snapshot, region=module.params["region"])

    module.exit_json(
        changed=True,
        msg=f"instance's snapshot {resource.snapshot} deleted",
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
        snapshot_id=dict(type="str"),
        volume_type=dict(
            type="str",
            required=True,
            choices=["unknown_volume_type", "l_ssd", "b_ssd", "unified"],
        ),
        zone=dict(
            type="str",
            required=False,
        ),
        name=dict(
            type="str",
            required=False,
        ),
        volume_id=dict(
            type="str",
            required=False,
        ),
        tags=dict(
            type="list",
            required=False,
            elements="str",
        ),
        organization=dict(
            type="str",
            required=False,
        ),
        project=dict(
            type="str",
            required=False,
        ),
        bucket=dict(
            type="str",
            required=False,
        ),
        key=dict(
            type="str",
            required=False,
            no_log=True,
        ),
        size=dict(
            type="int",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["snapshot_id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
