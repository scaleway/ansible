#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import base64
from scaleway_core.api import ScalewayException
__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_secret
short_description: Manage Scaleway secret's secret version
description:
    - This module can be used to manage Scaleway secret's secret version.
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
            - C(present) will create a new secret's version. If the secret does not exist, it will be created.
            - C(absent) will delete the secret version, if it exists.
            - C(disable) will disable the secret version, if it exists.
            - C(enable) will enable the secret version, if it exists.
            - C(access) will access the secret version, if it exists.
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
    data:
        description: the secret value
        type: str
        required: false                   
"""

EXAMPLES = r"""
- name: Create a  version of the secret and disable the previous version
    scaleway.scaleway.scaleway_secret_version:
      access_key:  "{{ scw_access_key }}"
      secret_key:  "{{ scw_secret_key }}"
      project_id: "{{ scw_project_id }}"
      region: "{{ scw_region }}"
      name: "aaaaaa"
      state: "present"
      disable_previous: true
      data: "{{ data }}"
      
  - name: access the latest version of the secret
    scaleway.scaleway.scaleway_secret_access:
      access_key:  "{{ scw_access_key }}"
      secret_key:  "{{ scw_secret_key }}"
      project_id: "{{ scw_project_id }}"
      region: "{{ scw_region }}"
      name: "aaaaaa"
    register: data       
"""

RETURN = r"""
---
secret_version:
    description: The secret version data
    returned: when I(state=present)
    type: dict
    sample:
        id: 00000000-0000-0000-0000-000000000000
        project_id: 00000000-0000-0000-0000-000000000000
        name: "aaaaaa"
        status: ready
        created_at: "1970-01-01T00:00:00.000000+00:00"
        updated_at: "1970-01-01T00:00:00.000000+00:00"
        tags:
            - aaaaaa
            - bbbbbb
        region: fr-par
        version_count: 3
        description: "foobar"
        
secret_data:
    description: The value of secret version data
    returned: when I(state=access)
    type: dict
    sample:
        data: "my_secret_data"
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
    region = module.params.pop("region", None)
    project_id = module.params.pop("project_id", None)
    name = module.params.pop("name", None)
    disable_previous = module.params.pop("disable_previous", None)  
    id = module.params.pop("id", None)
    data = module.params.pop("data", None).encode()
    
    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    if data is not None:
        data = base64.b64encode(data).decode()
    if id is not None:
        secret = api.get_secret(secret_id=id)
        secret_version = api.create_secret_version(secret_id=id,
                                                   data=data,
                                                   disable_previous=disable_previous,
                                                   region=region)
        
        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=secret)
    elif name is not None:
        try:
            secret = api.get_secret_by_name(secret_name =name, region=region)
        except ScalewayException as exc:
            if exc.status_code == 404:
                secret = api.create_secret(name=name,
                                           project_id=project_id,
                                           region=region)
            else:
                raise exc    
                
        secret_version = api.create_secret_version(secret_id=secret.id,
                                         data=data,
                                         disable_previous=disable_previous,
                                         region=region)
    if module.check_mode:
        module.exit_json(changed=True)

    
    module.exit_json(changed=True,
                     msg=f"secret {secret.name} ({secret.id}) revision { secret_version.revision } has been created",
                     data=secret.__dict__)


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

    api.destroy_secret_version(secret_id=secret.id, region=region,revision=revision)
    
    module.exit_json(
        changed=True,
        msg=f"secret's  {secret.name} ({secret.id}) revision{ revision } has been deleted",
    )


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
    else:
        secret = api.get_secret_by_name(secret_name=name, region=region)
        
    revision  = 'latest_enabled' if revision is None else revision
    secret_version = api.access_secret_version(secret_id=secret.id, revision=revision,region=region)
    data = base64.b64decode(secret_version.data)
    if module.check_mode:
        module.exit_json(changed=True)
    module.exit_json(changed=True, data=data)


def enable(module: AnsibleModule, client: "Client") -> None:
    api = SecretV1Alpha1API(client)
    region = module.params.pop("region", None)
    project_id = module.params.pop("project_id", None)
    name = module.params.pop("name", None)
    id = module.params.pop("id", None)
    revision = module.params.pop("revision", None)
    
    if id is not None:
        secret = api.get_secret(secret_id=id)
    elif name is not None:
         secret = api.get_secret_by_name(secret_name =name, region=region)
    api.enable_secret_version(secret_id=secret.id, region=region,revision=revision)            
    if module.check_mode:
        module.exit_json(changed=True)

    # resource = api.create_secret(**not_none_params)
    
    module.exit_json(changed=True,
                     msg=f"secret's secret {secret.name} ({secret.id}) revision {revision } has been disabled",
                     data=secret.__dict__)

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

    api.disable_secret_version(secret_id=secret.id, region=region,revision=revision)
    
    module.exit_json(
        changed=True,
        msg=f"secret's secret {secret.name} ({secret.id}) revision { revision } has been disabled",
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
        state=dict(type="str", default="present", choices=["absent", "present", "enable", "disable", "access"]),
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
        destroy_previous=dict(
            type='bool',
            required=False
        ),
        disable_previous=dict(
            type='bool',
            required=False
        ),
        data=dict(
            type='str',
            required=False,
            #  no_log=True
        ),
        revision=dict(
            type='str',
            required=False,
        )
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
