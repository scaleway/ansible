#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


import base64

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
    from scaleway.secret.v1alpha1 import SecretV1Alpha1API
    from scaleway_core.api import ScalewayException

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = SecretV1Alpha1API(client)
    region = module.params.pop("region", None)
    project_id = module.params.pop("project_id", None)
    name = module.params.pop("name", None)
    id = module.params.pop("id", None)

    data = module.params.pop("data", None).encode()
    if data is not None:
        data = base64.b64encode(data).decode()

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }

    if id is not None:
        secret = api.get_secret(secret_id=id)
        secret_version = api.create_secret_version(
            secret_id=id,
            region=region,
            data=data,
            **not_none_params,
        )

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=secret)
    elif name is not None:
        try:
            secret = api.get_secret_by_name(secret_name=name, region=region)
        except ScalewayException as exc:
            if exc.status_code == 404:
                secret = api.create_secret(
                    name=name, project_id=project_id, region=region
                )
            else:
                raise exc
        secret_version = api.create_secret_version(
            secret_id=secret.id,
            region=region,
            data=data,
            **not_none_params,
        )
    if module.check_mode:
        module.exit_json(changed=True)

    module.exit_json(
        changed=True,
        msg=f"secret {secret.name} ({secret.id}) revision {secret_version.revision}]\
                           has been created",
        data=secret.__dict__,
    )


def delete(module: AnsibleModule, client: "Client") -> None:
    api = SecretV1Alpha1API(client)

    id = module.params.pop("id", None)
    name = module.params.pop("name", None)
    region = module.params.pop("region", None)
    revision = module.params.pop("revision", None)

    if id is not None:
        secret = api.get_secret(secret_id=id, region=region)
    elif name is not None:
        secret = api.get_secret_by_name(secret_name=name, region=region)
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.destroy_secret_version(secret_id=secret.id, region=region, revision=revision)

    module.exit_json(
        changed=True,
        msg=f"secret's  {secret.name} ({secret.id}) revision {revision} has been deleted",
    )


def access(module: AnsibleModule, client: "Client") -> None:
    api = SecretV1Alpha1API(client)

    id = module.params.pop("id", None)
    name = module.params.pop("name", None)
    region = module.params.pop("region", None)
    revision = module.params.pop("revision", None)
    if id is not None:
        secret = api.get_secret(secret_id=id, region=region)

        if module.check_mode:
            module.exit_json(changed=False)
    else:
        secret = api.get_secret_by_name(secret_name=name, region=region)

    revision = "latest_enabled" if revision is None else revision
    secret_version = api.access_secret_version(
        secret_id=secret.id, revision=revision, region=region
    )
    data = base64.b64decode(secret_version.data)
    if module.check_mode:
        module.exit_json(changed=True)
    module.exit_json(changed=True, data=data)


def enable(module: AnsibleModule, client: "Client") -> None:
    api = SecretV1Alpha1API(client)
    region = module.params.pop("region", None)
    name = module.params.pop("name", None)
    id = module.params.pop("id", None)
    revision = module.params.pop("revision", None)

    if id is not None:
        secret = api.get_secret(secret_id=id)
    elif name is not None:
        secret = api.get_secret_by_name(secret_name=name, region=region)
    api.enable_secret_version(secret_id=secret.id, region=region, revision=revision)
    if module.check_mode:
        module.exit_json(changed=True)

    module.exit_json(
        changed=True,
        msg=f"secret's secret {secret.name} ({secret.id}) revision {revision} has been disabled",
        data=secret.__dict__,
    )


def disable(module: AnsibleModule, client: "Client") -> None:
    api = SecretV1Alpha1API(client)

    id = module.params.pop("id", None)
    name = module.params.pop("name", None)
    region = module.params.pop("region", None)
    revision = module.params.pop("revision", None)

    if id is not None:
        secret = api.get_secret(secret_id=id, region=region)
    elif name is not None:
        secret = api.get_secret_by_name(secret_name=name, region=region)
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.disable_secret_version(secret_id=secret.id, region=region, revision=revision)

    module.exit_json(
        changed=True,
        msg=f"secret's secret {secret.name} ({secret.id}) revision {revision} has been disabled",
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
    elif state == "enable":
        enable(module, client)
    elif state == "disable":
        disable(module, client)
    elif state == "access":
        access(module, client)


def main() -> None:
    argument_spec = scaleway_argument_spec()
    argument_spec.update(scaleway_waitable_resource_argument_spec())
    argument_spec.update(
        state=dict(
            type="str",
            default="present",
            choices=["absent", "present", "enable", "disable", "access"],
        ),
        secret_id=dict(type="str", no_log=True),
        name=dict(
            type="str",
            required=True,
        ),
        region=dict(
            type="str",
            required=False,
            choices=["fr-par", "nl-ams", "pl-waw"],
        ),
        project_id=dict(
            type="str",
            required=False,
        ),
        tags=dict(
            type="list",
            required=False,
            elements="str",
        ),
        description=dict(
            type="str",
            required=False,
        ),
        destroy_previous=dict(type="bool", required=False),
        disable_previous=dict(type="bool", required=False),
        data=dict(
            type="str",
            required=False,
            #  no_log=True
        ),
        revision=dict(
            type="str",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["secret_id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
