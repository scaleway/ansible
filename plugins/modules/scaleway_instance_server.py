#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_instance_server
short_description: Manage Scaleway Instance servers using volume IDs
version_added: "1.0.0"
author: Scaleway (@scaleway)
description:
  - Create or delete Scaleway Instance servers using predefined volumes.
  - Allows specifying attached volumes by ID, custom boot types, public IPs, tags, and more.

options:
  state:
    description:
      - Desired state of the server.
      - Use C(present) to create or ensure the server exists.
      - Use C(absent) to delete an existing server.
    choices: [present, absent]
    type: str
    default: present

  instance_id:
    description:
      - ID of the existing instance to use or manage.
    type: str

  security_group_id:
    description:
      - ID of the security group to attach to the server.
    type: str
    required: true

  zone:
    description:
      - Scaleway zone where the server will be created.
    type: str

  commercial_type:
    description:
      - Server type (e.g., DEV1-S, GP1-M).
    type: str
    required: true

  name:
    description:
      - Name of the server to create.
    type: str

  dynamic_ip_required:
    description:
      - Whether to automatically allocate a public IP.
    type: bool
    default: false

  routed_ip_enabled:
    description:
      - Enable routed IP.
    type: bool
    default: false

  image:
    description:
      - Image ID to use for the server. Not used if volumes are provided.
    type: str

  volumes_id:
    description:
      - List of volume IDs to attach to the instance.
    type: list
    elements: str

  enable_ipv6:
    description:
      - Whether to enable IPv6.
    type: bool
    default: false

  protected:
    description:
      - Prevents the server from being deleted.
    type: bool
    default: false

  public_ip:
    description:
      - Public IP address to assign.
    type: str

  public_ips:
    description:
      - List of public IPs to assign.
    type: list
    elements: str

  boot_type:
    description:
      - Boot method used for the server.
    choices: [local, bootscript, rescue]
    type: str

  tags:
    description:
      - List of tags associated with the server.
    type: list
    elements: str

  placement_group:
    description:
      - Placement group ID for the server.
    type: str

  admin_password_encryption_ssh_key_id:
    description:
      - SSH key ID used to encrypt the admin password.
    type: str

  project:
    description:
      - Project ID in which the server will be created.
    type: str

  organization:
    description:
      - Organization ID in which the server will be created.
    type: str
"""

EXAMPLES = r"""
# Create a server with volume attachments
- name: Create a Scaleway Instance with volumes
  scaleway.scaleway.scaleway_instance_server:
    state: present
    name: my-instance
    commercial_type: DEV1-S
    security_group_id: XXXXX
    zone: fr-par-1
    volumes_id:
      - XXXXXXX
      - XXXXXXX
    tags:
      - demo
    enable_ipv6: true
    dynamic_ip_required: true
"""

RETURN = r"""
---
server:
    description: Details about the Scaleway instance server
    returned: when state == "present"
    type: dict
    sample:
        server:
            id: 11111111-aaaa-bbbb-cccc-222222222222
            name: my-instance
            commercial_type: DEV1-S
            creation_date: '2024-01-01T12:00:00Z'
            dynamic_ip_required: false
            enable_ipv6: true
            image:
                id: 33333333-aaaa-bbbb-cccc-444444444444
                name: Ubuntu 22.04
            zone: fr-par-1
            state: running
            public_ip:
                id: 12345678-aaaa-bbbb-cccc-87654321abcd
                address: 203.0.113.42
            private_ip: 192.168.0.1
            security_group:
                id: sg-abcdef12
            tags:
              - web
              - production
"""

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.scaleway.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec, scaleway_waitable_resource_argument_spec,
    scaleway_get_client_from_module, scaleway_pop_client_params,
    scaleway_pop_waitable_resource_params, object_to_dict
)

try:
    from scaleway import Client
    from scaleway.instance.v1 import InstanceV1API, VolumeServerTemplate
    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False

def create(module: AnsibleModule, client: "Client") -> None:
    api = InstanceV1API(client)

    id = module.params.get("id", None)
    if id is not None:
        resource = api.get_server(server_id=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    # volumes_id = module.params.pop("volumes_id", None)
    not_none_params = {key: value for key, value in module.params.items() if value is not None}
    # volumes = {}
    # if volumes_id is not None:
    #     if not isinstance(volumes_id, list):
    #         module.fail_json(msg="volumes_id must be a list of volume IDs")
    #     for i, volume_id in enumerate(volumes_id):
    #         volume = api.get_volume(volume_id=volume_id)
    #         volumes[str(i)] = VolumeServerTemplate(id=volume.volume.id, volume_type=volume.volume.volume_type, size=volume.volume.id, name=volume.volume.name, project=volume.volume.project, organization=volume.volume.organization)
    #         not_none_params["volumes"] = volumes

    resource = api._create_server(**not_none_params)

    module.exit_json(changed=True, data=object_to_dict(resource))



def delete(module: AnsibleModule, client: "Client") -> None:
    api = InstanceV1API(client)

    server_id = module.params.get("server_id", None)
    if not server_id:
        module.fail_json(msg="server_id is required to delete a server")

    try:
        resource = api.get_server(server_id=server_id)
    except Exception as e:
        module.fail_json(msg=f"Error retrieving instance to delete: {str(e)}")

    if module.check_mode:
        module.exit_json(changed=True)

    try:
        api.delete_server(server_id=resource.id, zone=module.params["zone"])
        module.exit_json(changed=True, msg=f"Instance {server_id} deleted successfully")
    except Exception as e:
        module.fail_json(msg=f"Error deleting instance: {str(e)}")


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
        state=dict(
            type="str",
            default="present",
            choices=["absent", "present"]
        ),
        server_id=dict(
            type="str"
        ),
        security_group_id=dict(
            type="str",
            required=False
        ),
        zone=dict(
            type="str",
            required=False
        ),
        commercial_type=dict(
            type="str",
            required=True
        ),
        name=dict(
            type="str",
            required=False
        ),
        dynamic_ip_required=dict(
            type="bool",
            required=False,
            default=False
        ),
        routed_ip_enabled=dict(
            type="bool",
            required=False,
        ),
        image=dict(
            type="str",
            required=False
        ),
        volumes_id=dict(
            type="list",
            required=False
        ),
        enable_ipv6=dict(
            type="bool",
            required=False,
            default=False
        ),
        public_ip=dict(
            type="str",
            required=False
        ),
        public_ips=dict(
            type="list",
            required=False
        ),
        boot_type=dict(
            type="str",
            required=False,
            choices=["local", "bootscript", "rescue"]
        ),
        tags=dict(
            type="list",
            elements="str",
            required=False
        ),
        placement_group=dict(
            type="str",
            required=False
        ),
        admin_password_encryption_ssh_key_id=dict(
            type="str",
            required=False
        ),
        project=dict(
            type="str",
            required=False
        ),
        organization=dict(
            type="str",
            required=False
        ),
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
