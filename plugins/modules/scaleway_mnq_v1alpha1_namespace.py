#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_mnq_v1alpha1_namespace
short_description: Manage Scaleway mnq_v1alpha1's namespace
description:
    - This module can be used to manage Scaleway mnq_v1alpha1's namespace.
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
    namespace_id:
        description: namespace_id
        type: str
        required: false
    region:
        description: region
        type: str
        required: false
        choices:
            - fr-par
            - nl-ams
            - pl-waw
    name:
        description: name
        type: str
        required: false
    protocol:
        description: protocol
        type: str
        required: false
        choices:
            - unknown
            - nats
            - sqs_sns
    project_id:
        description: project_id
        type: str
        required: false
"""

EXAMPLES = r"""
- name: Create a namespace
  scaleway.scaleway.scaleway_mnq_v1alpha1_namespace:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
"""

RETURN = r"""
---
namespace:
    description: The namespace information
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        name: "aaaaaa"
        endpoint: "aaaaaa"
        protocol: nats
        project_id: 00000000-0000-0000-0000-000000000000
        region: fr-par
        created_at: "aaaaaa"
        updated_at: "aaaaaa"
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
    from scaleway.mnq.v1alpha1 import MnqV1Alpha1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = MnqV1Alpha1API(client)

    resource_id = module.params.pop("namespace_id", None)
    if id is not None:
        resource = api.get_namespace(namespace_id=resource_id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    resource = api.create_namespace(**not_none_params)

    module.exit_json(changed=True, data=resource.__dict__)


def delete(module: AnsibleModule, client: "Client") -> None:
    api = MnqV1Alpha1API(client)

    resource_id = module.params.pop("id", None)

    if resource_id is not None:
        resource = api.get_namespace(
            namespace_id=resource_id,
            region=module.params["region"],
        )
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_namespace(
        namespace_id=resource.id,
        region=resource.region,
    )

    module.exit_json(
        changed=True,
        msg=f"mnq_v1alpha1's namespace {resource.name} ({resource.id}) deleted",
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
        namespace_id=dict(type="str"),
        region=dict(
            type="str",
            required=False,
            choices=["fr-par", "nl-ams", "pl-waw"],
        ),
        name=dict(
            type="str",
            required=False,
        ),
        protocol=dict(
            type="str",
            required=False,
            choices=["unknown", "nats", "sqs_sns"],
        ),
        project_id=dict(
            type="str",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["namespace_id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
