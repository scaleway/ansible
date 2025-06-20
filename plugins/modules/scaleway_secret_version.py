#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_secret_version
short_description: Manage Scaleway secret's secret version
description:
    - This module can be used to manage Scaleway secret's secret version.
version_added: "2.1.0"
author:
    - Nathanael Demacon (@quantumsheep)
requirements:
    - scaleway >= 2.9.0
options:
    state:
        description:
            - Indicate desired state of the target.
            - C(present) will create a new secret's version. If the secret does not exist, it will be created.
            - C(absent) will delete the secret version, if it exists.
        default: present
        choices: ["present", "absent"]
        type: str
    secret_id:
        description: Secret's id associated with the version
        type: str
        required: false
    secret_name:
        description: Secret's name associated with the version
        type: str
        required: false
    revision:
        description: revision
        type: str
        required: false
    description:
        description: description
        type: str
        required: false
    data:
        description: the secret value
        type: str
        required: false
    force_new_version:
        description: force the creation of a new secret version, even if the data is identical to the previous version
        type: bool
        required: false
        default: false
"""

EXAMPLES = r"""
- name: Create a secret
  scaleway.scaleway.scaleway_secret:
    secret_name: "ansible-test-secret"
  register: secret

- name: Create a secret version
  scaleway.scaleway.scaleway_secret_version:
    secret_id: "{{ secret.data.id }}"
    data: "my_secret_data"
"""

RETURN = r"""
---
secret_version:
    description: The secret version data
    returned: when I(state=present)
    type: dict
    sample:
        created_at: "2025-05-14T12:02:50.846327+00:00"
        deleted_at: null
        deletion_requested_at: null
        description: ""
        ephemeral_properties: null
        latest: true
        revision: 1
        secret_id: "c8571246-4bf3-4b62-bfcc-11a79d74fd57"
        status: enabled
        updated_at: "2025-05-14T12:02:50.846327+00:00"
"""

import base64

from ..module_utils.scaleway import (
    build_scaleway_client_and_module,
)
from ..module_utils.scaleway_secret import (
    get_secret,
    build_ansible_diff,
    build_secret_version,
    get_secret_version,
)
from ansible.module_utils.basic import AnsibleModule

HAS_SCALEWAY_SDK = True

try:
    from scaleway import Client
    from scaleway.secret.v1beta1 import SecretV1Beta1API
    from scaleway import ScalewayException
except ImportError:
    HAS_SCALEWAY_SDK = False


def create_secret_version(
    api: "SecretV1Beta1API", module: AnsibleModule, parameters: dict
) -> None:
    try:
        secret_version = api.create_secret_version(**parameters)
        module.exit_json(
            changed=True,
            msg=f"({parameters.get('secret_id')}) revision {secret_version.revision} has been created",
            data=build_secret_version(secret_version.__dict__).__dict__,
        )
    except ScalewayException as scw_exception:
        module.fail_json(msg="Failed to create secret version", exception=scw_exception)


def create_check_mode(
    client: "Client", module: AnsibleModule, parameters: dict
) -> None:
    api = SecretV1Beta1API(client)

    parameters["data"] = base64.b64encode(parameters.get("data").encode()).decode()
    parameters["revision"] = "latest"

    try:
        remote_model = get_secret_version(api, **parameters)
        module.exit_json(
            changed=False,
            data=remote_model.__dict__,
            diff=build_ansible_diff(remote_model, build_secret_version(parameters)),
        )
    except ScalewayException as scw_exception:
        if scw_exception.status_code == 404:
            module.exit_json(
                changed=False,
                diff={"before": {}, "after": build_secret_version(parameters).__dict__},
            )
        module.fail_json(msg="Failed to get secret version", exception=scw_exception)


def create(client: "Client", module: AnsibleModule, parameters: dict) -> None:
    api = SecretV1Beta1API(client)

    if parameters.get("secret_id") is None:
        secret = get_secret(api, name=parameters.pop("secret_name"))
        parameters["secret_id"] = secret.id

    parameters["data"] = base64.b64encode(parameters.get("data").encode()).decode()

    if parameters.pop("force_new_version", False):
        return create_secret_version(api, module, parameters)

    try:
        remote_model = get_secret_version(api, **parameters)
    except ScalewayException as scw_exception:
        if scw_exception.status_code == 404:
            return create_secret_version(api, module, parameters)
        module.fail_json(msg="Failed to get secret version", exception=scw_exception)

    parameters["revision"] = remote_model.revision
    local_model = build_secret_version(parameters)
    ansible_diff = build_ansible_diff(remote_model, local_model)
    diff = remote_model.diff(local_model)

    if len(diff) > 0:
        parameters.pop("revision")
        return create_secret_version(api, module, parameters)
    else:
        module.exit_json(
            changed=False,
            msg="latest secret version data is up to date",
            diff=ansible_diff,
        )


def delete(client: "Client", module: AnsibleModule) -> None:
    api = SecretV1Beta1API(client)

    revision = module.params.get("revision")

    secret_id = module.params.get("secret_id")
    if secret_id is None:
        secret = get_secret(api, name=module.params.get("secret_name"))
        secret_id = secret.id

    try:
        api.delete_secret_version(secret_id=secret_id, revision=revision)
    except ScalewayException as scw_exception:
        if scw_exception.status_code == 404:
            module.exit_json(
                changed=False,
                msg=f"secret's version {revision} not found",
            )

    module.exit_json(
        changed=True,
        msg=f"secret's version {revision} has been deleted",
    )


def run_module(client: "Client", module: AnsibleModule) -> None:
    state = module.params.pop("state")

    parameters = {
        key: value for key, value in module.params.items() if value is not None
    }
    parameters["region"] = client.default_region

    if state == "present":
        if parameters.pop("revision", None) is not None:
            module.warn("revision is ignored when creating a secret version")

        if module.check_mode:
            create_check_mode(client, module, parameters)
        else:
            create(client, module, parameters)
    elif state == "absent":
        delete(client, module)


def main() -> None:
    client, module = build_scaleway_client_and_module(
        dict(
            state=dict(type="str", default="present", choices=["absent", "present"]),
            secret_id=dict(type="str", required=False),
            secret_name=dict(type="str", required=False),
            description=dict(type="str", required=False),
            data=dict(type="str", required=False, no_log=True),
            revision=dict(type="str", required=False),
            force_new_version=dict(type="bool", required=False, default=False),
        ),
        required_one_of=[["secret_id", "secret_name"]],
        required_if=[
            ["state", "present", ["data"]],
            ["state", "absent", ["revision"]],
        ],
        supports_check_mode=True,
    )

    run_module(client, module)


if __name__ == "__main__":
    main()
