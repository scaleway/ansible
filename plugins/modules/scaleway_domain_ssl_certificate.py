from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_domain_ssl_certificate
short_description: Manage Scaleway domain's ssl_certificate
description:
    - This module can be used to manage Scaleway domain's ssl_certificate.
version_added: "2.1.0"
author:
    - Nathanael Demacon (@quantumsheep)
extends_documentation_fragment:
    - quantumsheep.scaleway.scaleway
    - quantumsheep.scaleway.scaleway_waitable_resource
requirements:
    - scaleway >= 0.6.0
options:
    state:
        description:
            - Indicate desired state of the target.
            - C(present) will create the resource.
            - C(absent) will delete the resource, if it exists.
        default: present
        choices: ["present", "absent", "]
        type: str
    id:
        type: str
        required: false
    dns_zone:
        type: str
        required: true
    alternative_dns_zones:
        type: list
        required: false
"""

RETURN = r"""
---
ssl_certificate:
    description: The ssl_certificate information
    returned: when I(state=present)
    type: dict
    sample:
        dns_zone: "aaaaaa"
        alternative_dns_zones:
            - aaaaaa
            - bbbbbb
        status: new
        private_key: "aaaaaa"
        certificate_chain: "aaaaaa"
        created_at: "aaaaaa"
        expired_at: "aaaaaa"
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.quantumsheep.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_waitable_resource_argument_spec,
    scaleway_get_client_from_module,
    scaleway_pop_client_params,
    scaleway_pop_waitable_resource_params,
)

from scaleway import Client, ScalewayException
from scaleway.domain.v2beta1 import DomainV2Beta1API


def create(module: AnsibleModule, client: Client) -> None:
    api = DomainV2Beta1API(client)

    id = module.params.pop("id", None)
    if id is not None:
        resource = api.get_ssl_certificate(dns_zone=id)

        if module.check_mode:
            module.exit_json(changed=False)

        module.exit_json(changed=False, data=resource)

    if module.check_mode:
        module.exit_json(changed=True)

    resource = api.create_ssl_certificate(**module.params)
    resource = api.wait_for_ssl_certificate(dns_zone=resource.dns_zone)

    module.exit_json(changed=True, data=resource)


def delete(module: AnsibleModule, client: Client) -> None:
    api = DomainV2Beta1API(client)

    dns_zone = module.params["dns_zone"]

    if dns_zone is not None:
        resource = api.get_ssl_certificate(dns_zone=dns_zone)
    else:
        module.fail_json(msg="dns_zone is required")

    if module.check_mode:
        module.exit_json(changed=True)

    api.delete_ssl_certificate(dns_zone=resource.dns_zone)

    try:
        api.wait_for_ssl_certificate(dns_zone=resource.dns_zone)
    except ScalewayException as e:
        if e.status_code != 404:
            raise e

    module.exit_json(
        changed=True,
        msg=f"domain's ssl_certificate {resource.dns_zone} deleted",
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
        id=dict(type="str"),
        dns_zone=dict(type="str", required=True),
        alternative_dns_zones=dict(type="list", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    core(module)


if __name__ == "__main__":
    main()
