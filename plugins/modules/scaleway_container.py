#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Scaleway Serverless container management module
#
# Copyright: (c), Nathanael Demacon (@quantumsheep)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_container

short_description: Create, update and delete Scaleway containers
description:
    - This module can be used to create, update and delete Scaleway containers.

version_added: "2.1.0"

author:
    - Nathanael Demacon (@quantumsheep)

extends_documentation_fragment:
    - quantumsheep.scaleway.scaleway
    - quantumsheep.scaleway.scaleway_waitable_resource

requirements:
    - scaleway >= 0.5.0

options:
    state:
        description:
            - Indicate desired state of the target.
            - C(present) will create the resource.
            - C(absent) will delete the resource, if it exists.
        default: present
        choices: ["present", "absent", "active", "inactive"]
        type: str
    region:
        description:
            - The region you want to target.
        type: str
        required: true
        choices:
            - fr-par
            - nl-ams
            - pl-waw
    namespace_id:
        type: str
        required: true
    id:
        type: str
        required: false
    name:
        type: str
        required: false
    environment_variables:
        type: dict
        required: false
    min_scale:
        type: int
        required: false
    max_scale:
        type: int
        required: false
    memory_limit:
        type: int
        required: false
    timeout:
        type: int
        required: false
    privacy:
        type: str
        required: false
        choices:
            - unknown_privacy
            - public
            - private
        default: private
    description:
        type: str
        required: false
    registry_image:
        type: str
        required: false
    max_concurrency:
        type: int
        required: false
    protocol:
        type: str
        required: false
        choices:
            - unknown_protocol
            - http1
            - h2c
        default: http1
    port:
        type: int
        required: false
    secret_environment_variables:
        type: dict
        required: false
    http_option:
        type: str
        required: false
        choices:
            - unknown_http_option
            - enabled
            - redirected
        default: enabled
"""

EXAMPLES = r"""
- name: Create a container
  community.general.scaleway_container:
    namespace_id: '{{ scw_container_namespace }}'
    state: present
    region: fr-par
    name: my-awesome-container
    registry_image: rg.fr-par.scw.cloud/my-awesome-namespace/my-awesome-image:latest
    environment_variables:
      MY_VAR: my_value
    secret_environment_variables:
      MY_SECRET_VAR: my_secret_value
  register: container_creation_task

- name: Make sure container is deleted
  community.general.scaleway_container:
    namespace_id: '{{ scw_container_namespace }}'
    state: absent
    region: fr-par
    name: my-awesome-container
"""

RETURN = r"""
container:
  description: The container information.
  returned: when I(state=present)
  type: dict
  sample:
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.quantumsheep.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_waitable_resource_argument_spec,
    scaleway_get_client_from_module,
    scaleway_pop_client_params,
    scaleway_pop_waitable_resource_params,
)

from scaleway import ALL_REGIONS, Client, ScalewayException
from scaleway.container.v1beta1 import ContainerV1Beta1API


def create(module: AnsibleModule, client: Client) -> None:
    api = ContainerV1Beta1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        container = api.get_container(container_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=container)

    if module.check_mode:
        module.exit_json(changed=True)

    container = api.create_container(**module.params)
    container = api.wait_for_container(container_id=container.id)

    module.exit_json(changed=True, data=container)


def delete(module: AnsibleModule, client: Client) -> None:
    api = ContainerV1Beta1API(client)

    id = module.params["id"]
    name = module.params["name"]

    if id is not None:
        container = api.get_container(container_id=id)
    elif name is not None:
        containers = api.list_containers_all(
            namespace_id=module.params["namespace_id"],
            name=name,
        )
        if len(containers) == 0:
            module.exit_json(changed=False, msg="Container not found")

        container = containers[0]

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_container(container_id=container.id)

    try:
        api.wait_for_container(container_id=container.id)
    except ScalewayException as e:
        if e.status_code != 404:
            raise e

    module.exit_json(
        changed=True,
        msg=f"Container {container.name} ({container.id}) deleted",
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
    # From DOCUMENTATION
    argument_spec.update(
        state=dict(type="str", default="present", choices=["absent", "present"]),
        region=dict(type="str", required=True, choices=ALL_REGIONS),
        namespace_id=dict(type="str", required=True),
        id=dict(type="str"),
        name=dict(type="str"),
        environment_variables=dict(type="dict"),
        min_scale=dict(type="int"),
        max_scale=dict(type="int"),
        memory_limit=dict(type="int"),
        timeout=dict(type="str"),
        privacy=dict(
            type="str",
            choices=["unknown_privacy", "public", "private"],
            default="public",
        ),
        description=dict(type="str"),
        registry_image=dict(type="str"),
        max_concurrency=dict(type="int"),
        protocol=dict(
            type="str", choices=["unknown_protocol", "http1", "h2c"], default="http1"
        ),
        port=dict(type="int"),
        secret_environment_variables=dict(type="dict"),
        http_option=dict(
            type="str",
            choices=["unknown_http_option", "enabled", "redirected"],
            default="enabled",
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["id", "name"],),
        supports_check_mode=True,
    )

    core(module)


if __name__ == "__main__":
    main()
