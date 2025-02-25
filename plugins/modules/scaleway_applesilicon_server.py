#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_applesilicon_server
short_description: Manage Scaleway applesilicon's server
description:
    - This module can be used to manage Scaleway applesilicon's server.
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
    server_id:
        description: server_id
        type: str
        required: false
    type_:
        description: type_
        type: str
        required: true
    zone:
        description: zone
        type: str
        required: false
    name:
        description: name
        type: str
        required: false
    enable_vpc:
        description: Whether or not to enable VPC access
        type: bool
        required: true
    project_id:
        description: project_id
        type: str
        required: true
"""

EXAMPLES = r"""
- name: Create a server
  scaleway.scaleway.scaleway_applesilicon_server:
    access_key: "{{ scw_access_key }}"
    secret_key: "{{ scw_secret_key }}"
    project_id: "{{ scw_project_id }}"
    type_: "M2-M"
    enable_vpc: false
"""

RETURN = r"""
---
id:
    description: The unique identifier of the server.
    returned: always
    type: str
    sample: "00000000-0000-0000-0000-000000000000"

type_:
    description: The type of the server, such as the instance class or size.
    returned: always
    type: str
    sample: "M2-M"

name:
    description: The name of the server.
    returned: always
    type: str
    sample: "my-applesilicon-server"

project_id:
    description: The unique identifier of the project to which the server belongs.
    returned: always
    type: str
    sample: "00000000-0000-0000-0000-000000000000"

organization_id:
    description: The unique identifier of the organization under which the server resides.
    returned: always
    type: str
    sample: "00000000-0000-0000-0000-000000000000"

ip:
    description: The IP address assigned to the server.
    returned: always
    type: str
    sample: "192.168.1.100"

vnc_url:
    description: The VNC URL for accessing the server's console (if applicable).
    returned: always
    type: str
    sample: "vnc://192.168.1.100:5900"

status:
    description: The current status of the server (e.g., "starting", "running", "stopped").
    returned: always
    type: str
    sample: "starting"

os:
    description: The initially installed OS, this does not necessarily reflect the current OS version
    returned: always
    type: dict
    sample: {
                "compatible_server_types": [
                    "M1-M",
                    "M2-M",
                    "M2-L",
                    "M4-S"
                ],
                "family": "Sequoia",
                "id": "367b9c18-d57f-4c9a-bcea-9e1fda66fc70",
                "image_url": "https://scw-apple-silicon.s3.fr-par.scw.cloud/scw-console/os/macos-sequoia.png",
                "is_beta": false,
                "label": "macOS Sequoia 15.2",
                "name": "macos-sequoia-15.2",
                "version": "15.2",
                "xcode_version": "16"
            }

created_at:
    description: The UTC timestamp of when the server was created.
    returned: always
    type: str
    sample: "2025-02-24T12:00:00Z"

updated_at:
    description: The UTC timestamp of the last update to the server.
    returned: always
    type: str
    sample: "2025-02-24T12:30:00Z"

deletable_at:
    description: The UTC timestamp of when the server can be deleted (if applicable).
    returned: always
    type: str
    sample: "2025-12-24T12:00:00Z"

zone:
    description: The zone where the server is located (e.g., "fr-par-1" for Paris).
    returned: always
    type: str
    sample: "fr-par-1"

enable_vpc:
    description: Whether the server is part of a Virtual Private Cloud (VPC).
    returned: always
    type: bool
    sample: false
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
    object_to_dict,
)

try:
    from scaleway import Client, ScalewayException
    from scaleway.applesilicon.v1alpha1 import ApplesiliconV1Alpha1API

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def create(module: AnsibleModule, client: "Client") -> None:
    api = ApplesiliconV1Alpha1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_server(server_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    not_none_params = {
        key: value for key, value in module.params.items() if value is not None
    }
    not_none_params["project_id"] = client.default_project_id
    resource = api.create_server(**not_none_params)
    resource = api.wait_for_server(
        server_id=resource.id,
        zone=resource.zone
    )

    module.exit_json(changed=True, data=object_to_dict(resource))


def delete(module: AnsibleModule, client: "Client") -> None:
    api = ApplesiliconV1Alpha1API(client)

    id = module.params.pop("id", None)
    name = module.params.pop("name", None)

    if id is not None:
        resource = api.get_server(server_id=id, zone=module.params["zone"])
    elif name is not None:
        resources = api.list_servers_all(zone=module.params["zone"])
        final_resources = []
        for resource in resources:
            if resource.name == name:
                final_resources.append(resource)
        if len(final_resources) == 0:
            module.exit_json(msg="No server found with name {name}")
        elif len(final_resources) > 1:
            module.exit_json(msg="More than one server found with name {name}")
        else:
            resource = final_resources[0]
    else:
        module.fail_json(msg="id is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_server(server_id=resource.id, zone=module.params["zone"])

    try:
        api.wait_for_server(server_id=resource.id, zone=module.params["zone"])
    except ScalewayException as e:
        if e.status_code != 403:
            raise e

    module.exit_json(
        changed=True,
        msg=f"applesilicon's server {resource.name} ({resource.id}) deleted",
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
        server_id=dict(type="str"),
        type_=dict(
            type="str",
            required=True,
        ),
        zone=dict(
            type="str",
            required=False,
        ),
        name=dict(
            type="str",
            required=False,
        ),
        project_id=dict(
            type="str",
            required=True,
        ),
        enable_vpc=dict(
            type="bool",
            required=True,
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=(["server_id", "name"],),
        supports_check_mode=True,
    )

    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))

    core(module)


if __name__ == "__main__":
    main()
