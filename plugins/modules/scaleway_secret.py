#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_secret
short_description: Manage Scaleway secret's secret
description:
    - This module can be used to manage Scaleway secret's secret.
version_added: "2.1.0"
author:
    - Nathanael Demacon (@quantumsheep)
requirements:
    - scaleway >= 2.9.0
options:
    state:
        description:
            - Indicate desired state of the target.
            - C(present) will create the resource.
            - C(absent) will delete the resource, if it exists.
        default: present
        choices: ["present", "absent"]
        type: str
    secret_id:
        description: secret_id
        type: str
        required: false
    secret_name:
        description: name
        type: str
        required: false
    project_id:
        description: project_id
        type: str
        required: false
    tags:
        description: tags
        type: list
        elements: str
        required: false
    description:
        description: description
        type: str
        required: false
    protected:
        description: Protected secrets can be read and modified but they cannot be deleted
        type: bool
        required: false
        default: false
"""

EXAMPLES = r"""
- name: Create a secret
  scaleway.scaleway.scaleway_secret:
    secret_name: "test_secret"
    protected: true
    project_id: "6867048b-fe12-4e96-835e-41c79a39604b"
    tags:
      - tag1
      - tag2
    description: "test description"
"""

RETURN = r"""
---
secret:
    description: The secret information
    returned: when I(state=present)
    type: dict
    sample:
        created_at: "2025-05-14T12:02:50.136043+00:00"
        deletion_requested_at: null
        description: "test description"
        ephemeral_policy: null
        id: "c8571246-4bf3-4b62-bfcc-11a79d74fd57"
        managed: false
        name: "ansible-test-secret"
        path: "/"
        project_id: "6867048b-fe12-4e96-835e-41c79a39604b"
        protected: false
        region: fr-par
        status: ready
        tags: ["tag1", "tag2"]
        type_: opaque
        updated_at: "2025-05-14T12:02:50.136043+00:00"
        used_by: []
        version_count: 0
"""

from ansible_collections.scaleway.scaleway.plugins.module_utils.scaleway import (
    build_scaleway_client_and_module,
)
from ansible_collections.scaleway.scaleway.plugins.module_utils.scaleway_secret import (
    get_secret_id,
)
from ansible.module_utils.basic import AnsibleModule

HAS_SCALEWAY_SDK = True
try:
    from scaleway.secret.v1beta1 import SecretV1Beta1API
    from scaleway import Client
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(client: "Client", module: AnsibleModule) -> None:
    api = SecretV1Beta1API(client)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }

    if not_none_params.get("secret_id"):
        module.exit_json(changed=False, msg="Secret's update is not supported")

    if not_none_params.get("project_id") is None:
        not_none_params["project_id"] = client.default_project_id

    not_none_params["region"] = client.default_region
    not_none_params["name"] = not_none_params.pop("secret_name")

    try:
        resource = api.create_secret(**not_none_params)
    except Exception as e:
        module.fail_json(msg="Failed to create secret", exception=e)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(client: "Client", module: AnsibleModule) -> None:
    api = SecretV1Beta1API(client)

    try:
        secret_id = get_secret_id(api, module.params)
    except Exception as e:
        module.fail_json(msg="Failed to get secret id", exception=e)

    try:
        api.delete_secret(secret_id=secret_id)
    except Exception as e:
        module.fail_json(msg="Failed to delete secret", exception=e)

    module.exit_json(
        changed=True,
        msg=f"Secret's secret {secret_id} deleted",
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
            protected=dict(type="bool", required=False, default=False),
        ),
        required_one_of=[["secret_id", "secret_name"]],
    )

    run_module(client, module)


if __name__ == "__main__":
    main()
