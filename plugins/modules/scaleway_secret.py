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
    name:
        description: name
        type: str
        required: true
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
    name: "test_secret"
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

from ..module_utils.scaleway import (
    build_scaleway_client_and_module,
)

from ..module_utils.scaleway_secret import (
    update_secret,
    get_secret,
    is_duplicate,
    build_diff,
    build_secret,
    SecretNotFound,
)


from ansible.module_utils.basic import AnsibleModule

HAS_SCALEWAY_SDK = True
try:
    from scaleway.secret.v1beta1 import SecretV1Beta1API
    from scaleway import Client, ScalewayException
except ImportError:
    HAS_SCALEWAY_SDK = False


def create_or_update_check(
    client: "Client", module: AnsibleModule, parameters: dict
) -> None:
    api = SecretV1Beta1API(client)

    try:
        changed, _, current_model = update_secret(api, parameters, check_mode=True)  # pylint: disable=disallowed-name
        module.exit_json(
            changed=changed,
            data=current_model.__dict__,
            diff=build_diff(current_model, parameters),
        )
    except SecretNotFound:
        module.exit_json(
            changed=False,
            data=build_secret(parameters).__dict__,
            diff={
                "before": {},
                "after": build_secret(parameters).__dict__,
            },
        )


def create_or_update(client: "Client", module: AnsibleModule, parameters: dict) -> None:
    api = SecretV1Beta1API(client)

    try:
        resource = api.create_secret(**parameters)
    except ScalewayException as scw_exception:
        if is_duplicate(scw_exception):
            try:
                changed, updated_model, current_model = update_secret(api, parameters)
                module.exit_json(
                    changed=changed,
                    data=updated_model.__dict__,
                    diff=build_diff(current_model, parameters),
                )
            except Exception as e:
                module.fail_json(msg="Failed to update secret", exception=e)
        else:
            module.fail_json(msg="Failed to create secret", exception=scw_exception)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(client: "Client", module: AnsibleModule) -> None:
    api = SecretV1Beta1API(client)

    try:
        secret = get_secret(api, name=module.params["name"])
    except Exception as e:
        module.fail_json(
            msg=f"Failed to get secret {module.params['name']}", exception=e
        )

    try:
        api.delete_secret(secret_id=secret.id)
    except Exception as e:
        module.fail_json(msg=f"Failed to delete secret {secret.name}", exception=e)

    module.exit_json(
        changed=True,
        msg=f"Secret's secret {secret.id} deleted",
        data=secret.__dict__,
    )


def run_module(client: "Client", module: AnsibleModule) -> None:
    state = module.params.pop("state")

    if state == "present":
        parameters = {
            key: value for key, value in module.params.items() if value is not None
        }
        if parameters.get("project_id") is None:
            parameters["project_id"] = client.default_project_id
        parameters["region"] = client.default_region

        if module.check_mode:
            create_or_update_check(client, module, parameters)
        else:
            create_or_update(client, module, parameters)
    elif state == "absent":
        delete(client, module)


def main() -> None:
    client, module = build_scaleway_client_and_module(
        dict(
            state=dict(type="str", default="present", choices=["absent", "present"]),
            name=dict(type="str", required=True),
            project_id=dict(type="str", required=False),
            tags=dict(type="list", required=False, elements="str"),
            description=dict(type="str", required=False),
            protected=dict(type="bool", required=False, default=False),
        ),
        supports_check_mode=True,
    )

    run_module(client, module)


if __name__ == "__main__":
    main()
