#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_secret_v1alpha1_secret
short_description: Manage Scaleway secret_v1alpha1's secret
description:
    - This module can be used to manage Scaleway secret_v1alpha1's secret.
version_added: "2.1.0"
author:
    - Nathanael Demacon (@quantumsheep)
extends_documentation_fragment:
    - scaleway.scaleway.scaleway
    - scaleway.scaleway.scaleway_waitable_resource
requirements:
    - scaleway >= 0.6.0
options:
    state:
        description:
            - Indicate desired state of the target.
            - C(present) will create the resource.
            - C(absent) will delete the resource, if it exists.
        default: present
        choices: ["present", "absent"]
        type: str
    id:
        description: id
        type: str
        required: false
    name:
        description: name
        type: str
        required: true
    type_:
        description: type_
        type: str
        required: true
        choices:
            - unknown_secret_type
            - opaque
            - network_edge_certificate
    region:
        description: region
        type: str
        required: false
        choices:
            - fr-par
            - nl-ams
            - pl-waw
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
"""

EXAMPLES = r"""
- name: Create a secret
  scaleway.scaleway.scaleway_secret_v1alpha1_secret:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
    name: "aaaaaa"
    type_: "aaaaaa"
"""

RETURN = r"""
---
secret:
    description: The secret information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        project_id: 00000000-0000-0000-0000-000000000000
        name: "aaaaaa"
        status: ready
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
        tags:
            - aaaaaa
            - bbbbbb
        version_count: 3
        description: "aaaaaa"
        is_managed: true
        type_: opaque
        region: fr-par
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
    from scaleway.secret.v1alpha1 import SecretV1Alpha1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = SecretV1Alpha1API(client)

    resource_id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_secret(secret_id=resource_id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_secret(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = SecretV1Alpha1API(client)

    resource_id = module.params.pop("id", None)

    if resource_id is not None:
        resource = api.get_secret(
            secret_id=resource_id,
            region=module.params["region"],
        )
    elif module.params.get("name", None) is not None:
        resources = api.list_secrets_all(
            name=module.params["name"],
            region=module.params["region"],
        )
        if len(resources) == 0:
            module.exit_json(msg="No secret found with name {name}")
        elif len(resources) > 1:
            module.exit_json(msg="More than one secret found with name {name}")
        else:
            resource = resources[0]
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_secret(
        secret_id=resource.id,
        region=resource.region,
    )

    module.exit_json(
        changed=True,
        msg=f"secret_v1alpha1's secret {resource.name} ({resource.id}) deleted",
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
        secret_id=dict(type="str", no_log=True),
        name=dict(
            type="str",
            required=True,
        ),
        type_=dict(
            type="str",
            required=True,
            choices=["unknown_secret_type", "opaque", "network_edge_certificate"],
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
        ),
        description=dict(
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
