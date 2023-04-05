#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import base64
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
    secret_id:
        description: secret_id
        type: str
        required: false
    name:
        description: name
        type: str
        required: true
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
  scaleway.scaleway.scaleway_secret:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
    name: "aaaaaa"
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
        region: fr-par
        version_count: 3
        description: "aaaaaa"
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


def access(module: AnsibleModule, client: "Client") -> None:
    api = SecretV1Alpha1API(client)

    id = module.params.pop("id", None)
    name = module.params.pop("name", None)
    region = module.params.pop("region", None)
    revision = module.params.pop("revision", None)
    if id is not None:
        secret = api.get_secret(secret_id=id,region=region)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=secret)
    else:
        secret = api.get_secret_by_name(secret_name=name, region=region)
        
    revision  = 'latest_enabled' if revision is None else revision
    secret_version = api.access_secret_version(secret_id=secret.id, revision=revision,region=region)   
    data = base64.b64decode(secret_version.data)
    if module.check_mode:
        module.exit_json(changed=True)


    module.exit_json(changed=True, data=data)



def core(module: AnsibleModule) -> None:
    client = scaleway_get_client_from_module(module)

    scaleway_pop_client_params(module)
    scaleway_pop_waitable_resource_params(module)

    access(module, client)


def main() -> None:
    argument_spec = scaleway_argument_spec()
    argument_spec.update(scaleway_waitable_resource_argument_spec())
    argument_spec.update(
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
        disable_previous=dict(
            type="bool",
            required=False,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["secret_id", "name"],),
        mutually_exclusive = [('secret_id','secret_name'),
                              ('destroy_previous_version','disable_previous_version')],
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
