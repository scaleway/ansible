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
    project_id:
        description: project_id
        type: str
        required: false
    revision:
        description: revision
        type: str
        required: false
        default: latest
    tags:
        description: tags
        type: list
        elements: str
        required: false
    description:
        description: description
        type: str
        required: false
    data:
        description: the secret value
        type: str
        required: false
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
from ..module_utils.scaleway_secret import get_secret
from ansible.module_utils.basic import AnsibleModule

HAS_SCALEWAY_SDK = True

try:
    from scaleway import Client
    from scaleway.secret.v1beta1 import SecretV1Beta1API
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(client: "Client", module: AnsibleModule) -> None:
    api = SecretV1Beta1API(client)

    secret_id = module.params.get("secret_id")

    if not secret_id:
        try:
            secret_model = get_secret(
                api,
                name=module.params.get("secret_name"),
            )
            secret_id = secret_model.id
            module.params.pop("secret_name")
        except Exception as e:
            module.fail_json(msg=str(e))

    parameters = {
        key: value for key, value in module.params.items() if value is not None
    }
    parameters["secret_id"] = secret_id

    revision = parameters.pop("revision", None)
    if revision is not None:
        module.warn("revision is ignored when creating a secret version")

    data = module.params.pop("data", None)
    if data is None:
        return module.fail_json(msg="data is required when creating a secret version")

    parameters["data"] = base64.b64encode(data.encode()).decode()

    secret_version = api.create_secret_version(**parameters)

    module.exit_json(
        changed=True,
        msg=f"({parameters.get('secret_id')}) revision {secret_version.revision} has been created",
        data=secret_version.__dict__,
    )


def delete(client: "Client", module: AnsibleModule) -> None:
    api = SecretV1Beta1API(client)

    revision = module.params.get("revision")
    secret_id = module.params.get("secret_id")

    if not secret_id:
        try:
            secret_model = get_secret(
                api,
                name=module.params.get("secret_name"),
            )
            secret_id = secret_model.id
            module.params.pop("secret_name")
        except Exception as e:
            module.fail_json(msg=str(e))

    api.delete_secret_version(secret_id=secret_id, revision=revision)

    module.exit_json(
        changed=True,
        msg=f"secret's version {revision} has been deleted",
    )


def run_module(client: "Client", module: AnsibleModule) -> None:
    state = module.params.pop("state")

    if state == "present":
        create(client, module)
    elif state == "absent":
        delete(client, module)


def main() -> None:
    client, module = build_scaleway_client_and_module(
        dict(
            state=dict(type="str", default="present", choices=["absent", "present"]),
            secret_id=dict(type="str", required=False),
            secret_name=dict(type="str", required=False),
            project_id=dict(type="str", required=False),
            tags=dict(type="list", required=False, elements="str"),
            description=dict(type="str", required=False),
            data=dict(type="str", required=False, no_log=True),
            revision=dict(type="str", required=False, default="latest"),
        ),
        required_one_of=[["secret_id", "secret_name"]],
    )

    run_module(client, module)


if __name__ == "__main__":
    main()
