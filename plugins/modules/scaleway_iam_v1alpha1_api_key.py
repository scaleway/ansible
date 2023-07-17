#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_iam_v1alpha1_api_key
short_description: Manage Scaleway iam_v1alpha1's api_key
description:
    - This module can be used to manage Scaleway iam_v1alpha1's api_key.
version_added: "2.1.0"
author:
    - Nathanael Demacon (@quantumsheep)
extends_documentation_fragment:
    - scaleway.scaleway.scaleway
    - scaleway.scaleway.scaleway_waitable_resource
requirements:
    - scaleway >= 0.16.0
options:
    state:
        description:
            - Indicate desired state of the target.
            - C(present) will create the resource.
            - C(absent) will delete the resource, if it exists.
        default: present
        choices: ["present", "absent"]
        type: str
    access_key:
        description: access_key
        type: str
        required: false
    description:
        description: description
        type: str
        required: true
    application_id:
        description: application_id
        type: str
        required: false
    user_id:
        description: user_id
        type: str
        required: false
    expires_at:
        description: expires_at
        type: str
        required: false
    default_project_id:
        description: default_project_id
        type: str
        required: false
"""

EXAMPLES = r"""
- name: Create a api_key
  scaleway.scaleway.scaleway_iam_v1alpha1_api_key:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
    description: "aaaaaa"
"""

RETURN = r"""
---
api_key:
    description: The api_key information
    returned: when I(state=present)
    type: dict
    sample:
        access_key: "aaaaaa"
        secret_key: "aaaaaa"
        application_id: 00000000-0000-0000-0000-000000000000
        user_id: 00000000-0000-0000-0000-000000000000
        description: "aaaaaa"
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
        expires_at: "aaaaaa"
        default_project_id: 00000000-0000-0000-0000-000000000000
        editable: true
        creation_ip: "aaaaaa"
"""

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

    resource_id = module.params.pop("access_key", None)
    if id is not None:
        resource = api.get_api_key(access_key=resource_id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_api_key(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = IamV1Alpha1API(client)

    resource_id = module.params.pop("application_id", None)

    if resource_id is not None:
        resource = api.get_api_key(
            access_key=resource_id,
        )
    else:
        module.fail_json(msg="application_id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_api_key(
        access_key=resource.id,
    )

    module.exit_json(
        changed=True,
        msg=f"iam_v1alpha1's api_key {resource.application_id} deleted",
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
        access_key=dict(type="str", no_log=True),
        description=dict(
            type="str",
            required=True,
        ),
        application_id=dict(
            type="str",
            required=False,
        ),
        user_id=dict(
            type="str",
            required=False,
        ),
        expires_at=dict(
            type="str",
            required=False,
        ),
        default_project_id=dict(
            type="str",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
