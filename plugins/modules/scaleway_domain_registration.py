#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Scaleway Ansible contributors
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Purchase and manage Scaleway domain registrations."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_domain_registration
short_description: Purchase and manage Scaleway domain registrations
description:
  - Purchase domains and manage their auto-renewal and DNSSEC settings.
  - Purchasing domains incurs charges and requires C(confirm_purchase=true).
  - C(state=absent) disables auto-renewal. It does not cancel a registration,
    transfer ownership, or remove the domain before its expiry, matching the
    Terraform provider's deletion behavior.
  - Owner contact and duration apply only when purchasing a new registration.
    Changing the owner later requires a domain trade outside this module.
version_added: "2.8.0"
author:
  - Scaleway Ansible contributors
extends_documentation_fragment:
  - scaleway.scaleway.scaleway
requirements:
  - scaleway >= 2.10.1
options:
  state:
    description: Desired registration management state.
    type: str
    choices: [present, absent]
    default: present
  domain_names:
    description: Domain names to purchase or manage.
    type: list
    elements: str
    required: true
  duration_in_years:
    description: Registration duration for a new purchase. Cannot change existing registrations.
    type: int
    default: 1
  owner_contact_id:
    description: Existing owner contact ID for a new purchase.
    type: str
  owner_contact:
    description:
      - Owner contact for a new purchase. Use this or C(owner_contact_id).
      - National registries may require C(extension_fr), C(extension_eu), or C(extension_nl).
    type: dict
    suboptions:
      legal_form:
        description: Individual, corporate, association, or other.
        type: str
        required: true
      firstname:
        description: First name.
        type: str
        required: true
      lastname:
        description: Last name.
        type: str
        required: true
      email:
        description: Email address.
        type: str
        required: true
      phone_number:
        description: Phone number.
        type: str
        required: true
      address_line_1:
        description: Street address.
        type: str
        required: true
      zip:
        description: Postal code.
        type: str
        required: true
      city:
        description: City.
        type: str
        required: true
      country:
        description: ISO country code.
        type: str
        required: true
      company_name:
        description: Company name.
        type: str
      email_alt:
        description: Alternative email address.
        type: str
      fax_number:
        description: Fax number.
        type: str
      address_line_2:
        description: Additional street address.
        type: str
      vat_identification_code:
        description: VAT identification code.
        type: str
      company_identification_code:
        description: Company identification code.
        type: str
      lang:
        description: Contact language, for example C(en_us) or C(fr_fr).
        type: str
      resale:
        description: Whether contact is used for resale.
        type: bool
      whois_opt_in:
        description: Whether contact opts into WHOIS publication.
        type: bool
      state:
        description: State or region.
        type: str
      extension_fr:
        description:
          - French registry details. Supply C(mode) and the matching detail dictionary.
          - Supports C(individual_info), C(duns_info), C(association_info),
            C(trademark_info), and C(code_auth_afnic_info).
        type: dict
      extension_eu:
        description: EU registry details with C(european_citizenship).
        type: dict
      extension_nl:
        description: Dutch registry details with C(legal_form) and C(legal_form_registration_number).
        type: dict
  auto_renew:
    description: Enable automatic renewal for managed domains.
    type: bool
    default: false
  dnssec:
    description: Enable DNSSEC for managed domains.
    type: bool
    default: false
  confirm_purchase:
    description:
      - Explicitly authorize a billable purchase if any domain is missing.
      - Check mode reports the purchase plan without requiring confirmation.
    type: bool
    default: false
  wait:
    description:
      - Wait for purchased domains and feature changes to become active.
      - When false after a purchase, rerun the task to apply auto-renewal and DNSSEC.
    type: bool
    default: true
  wait_timeout:
    description: Maximum number of seconds to wait for each asynchronous operation.
    type: int
    default: 3600
"""

EXAMPLES = r"""
- name: Manage DNSSEC for an existing registration without buying anything
  scaleway.scaleway.scaleway_domain_registration:
    domain_names: [example.com]
    dnssec: true
    auto_renew: true
  delegate_to: localhost

- name: Purchase a domain (this incurs a charge)
  scaleway.scaleway.scaleway_domain_registration:
    domain_names: [example.com]
    duration_in_years: 1
    owner_contact_id: "{{ scw_owner_contact_id }}"
    confirm_purchase: true
  delegate_to: localhost

- name: Stop automatic renewal without cancelling domain ownership
  scaleway.scaleway.scaleway_domain_registration:
    domain_names: [example.com]
    state: absent
  delegate_to: localhost
"""

RETURN = r"""
---
registrations:
  description: Registrar domain objects returned by Scaleway, one per existing domain.
  returned: always
  type: list
  elements: dict
planned_actions:
  description: Purchases and feature changes performed or planned in check mode.
  returned: always
  type: list
  elements: dict
task_id:
  description: Task ID of a new purchase order.
  returned: when a purchase is made
  type: str
"""

import time

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.scaleway.scaleway.plugins.module_utils.dns_registration import (
    build_contact,
    find_registration_task,
    get_domain_or_none,
    to_dict,
)
from ansible_collections.scaleway.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_get_client_from_module,
)

try:
    from scaleway.domain.v2beta1 import DomainV2Beta1RegistrarAPI

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def _status(value):
    return getattr(value, "value", value)


def _feature_enabled(value):
    return _status(value) in ("enabled", "enabling")


def _dnssec_status(domain):
    dnssec = getattr(domain, "dnssec", None)
    return _status(dnssec.status) if dnssec else "disabled"


def _feature_actions(domain, auto_renew, dnssec):
    actions = []
    if _feature_enabled(domain.auto_renew_status) != auto_renew:
        actions.append(
            {
                "domain": domain.domain,
                "action": "enable_auto_renew" if auto_renew else "disable_auto_renew",
            }
        )
    if _feature_enabled(_dnssec_status(domain)) != dnssec:
        actions.append(
            {
                "domain": domain.domain,
                "action": "enable_dnssec" if dnssec else "disable_dnssec",
            }
        )
    return actions


def _wait_for(api, domain, condition, timeout):
    deadline = time.monotonic() + timeout
    while True:
        current = get_domain_or_none(api, domain)
        if current is not None and condition(current):
            return current
        if time.monotonic() >= deadline:
            raise TimeoutError(f"timed out waiting for domain {domain}")
        time.sleep(min(5, max(0, deadline - time.monotonic())))


def _apply_action(api, action):
    domain = action["domain"]
    operation = action["action"]
    methods = {
        "enable_auto_renew": api.enable_domain_auto_renew,
        "disable_auto_renew": api.disable_domain_auto_renew,
        "enable_dnssec": api.enable_domain_dnssec,
        "disable_dnssec": api.disable_domain_dnssec,
    }
    return methods[operation](domain=domain)


def _normalized_names(names):
    result = [name.strip().lower().rstrip(".") for name in names]
    if not result or any(not name for name in result):
        raise ValueError("domain_names must contain at least one nonempty domain")
    if len(set(result)) != len(result):
        raise ValueError("domain_names contains a duplicate domain")
    return result


def run(module, api, default_project_id=None):
    params = module.params
    result = None
    mutated = False
    try:
        names = _normalized_names(params["domain_names"])
        if params["duration_in_years"] < 1:
            raise ValueError("duration_in_years must be positive")
        if params["wait_timeout"] < 1:
            raise ValueError("wait_timeout must be positive")

        project_id = params["project_id"] or default_project_id
        if not project_id:
            raise ValueError(
                "project_id or a default project in the Scaleway profile is required"
            )
        existing = {}
        for name in names:
            registration = get_domain_or_none(api, name)
            if (
                registration is not None
                and project_id
                and registration.project_id != project_id
            ):
                raise ValueError(
                    f"domain {name} belongs to project {registration.project_id}, not {project_id}"
                )
            existing[name] = registration

        missing = [name for name in names if existing[name] is None]
        pending_tasks = {}
        if params["state"] == "present":
            for name in missing:
                task = find_registration_task(api, name, project_id, pending_only=True)
                if task is not None:
                    pending_tasks[name] = task
        to_purchase = [name for name in missing if name not in pending_tasks]
        actions = []
        if params["state"] == "present":
            for name, task in pending_tasks.items():
                actions.append(
                    {
                        "action": "wait_for_registration",
                        "domain": name,
                        "task_id": task.id,
                    }
                )
            if to_purchase:
                actions.append(
                    {
                        "action": "purchase",
                        "domains": to_purchase,
                        "duration_in_years": params["duration_in_years"],
                    }
                )
            for name in names:
                if existing[name] is not None:
                    actions.extend(
                        _feature_actions(
                            existing[name], params["auto_renew"], params["dnssec"]
                        )
                    )
        else:
            for name in names:
                if existing[name] is not None and _feature_enabled(
                    existing[name].auto_renew_status
                ):
                    actions.append({"domain": name, "action": "disable_auto_renew"})

        result = dict(
            changed=bool(actions),
            registrations=[
                to_dict(existing[name]) for name in names if existing[name] is not None
            ],
            planned_actions=actions,
        )
        if module.check_mode or not actions:
            module.exit_json(**result)

        if to_purchase and params["state"] == "present":
            if not params["confirm_purchase"]:
                raise ValueError(
                    "purchasing {} incurs charges; set confirm_purchase=true to authorize it".format(
                        ", ".join(to_purchase)
                    )
                )
            if bool(params["owner_contact_id"]) == bool(params["owner_contact"]):
                raise ValueError(
                    "a new purchase requires exactly one of owner_contact_id or owner_contact"
                )
            kwargs = dict(
                domains=to_purchase, duration_in_years=params["duration_in_years"]
            )
            kwargs["project_id"] = project_id
            if params["owner_contact_id"]:
                kwargs["owner_contact_id"] = params["owner_contact_id"]
            else:
                kwargs["owner_contact"] = build_contact(params["owner_contact"])
            order = api.buy_domains(**kwargs)
            mutated = True
            result["task_id"] = order.task_id

        if missing and params["state"] == "present":
            if params["wait"]:
                for name in missing:
                    existing[name] = _wait_for(
                        api,
                        name,
                        lambda domain: (
                            _status(domain.status)
                            not in ("creating", "checking", "status_unknown")
                        ),
                        params["wait_timeout"],
                    )
                    if _status(existing[name].status) != "active":
                        raise RuntimeError(
                            f"registration of {name} ended with status {_status(existing[name].status)}"
                        )
                    actions.extend(
                        _feature_actions(
                            existing[name], params["auto_renew"], params["dnssec"]
                        )
                    )
            else:
                result["pending"] = True

        for action in actions:
            if action["action"] in ("purchase", "wait_for_registration"):
                continue
            if existing[action["domain"]] is None:
                continue
            _apply_action(api, action)
            mutated = True
            if params["wait"]:
                wanted = action["action"].startswith("enable")
                if action["action"].endswith("dnssec"):
                    _wait_for(
                        api,
                        action["domain"],
                        lambda domain, wanted=wanted: (
                            (_dnssec_status(domain) == "enabled") == wanted
                            and _dnssec_status(domain) in ("enabled", "disabled")
                        ),
                        params["wait_timeout"],
                    )
                else:
                    _wait_for(
                        api,
                        action["domain"],
                        lambda domain, wanted=wanted: (
                            (_status(domain.auto_renew_status) == "enabled") == wanted
                            and _status(domain.auto_renew_status)
                            in ("enabled", "disabled")
                        ),
                        params["wait_timeout"],
                    )

        if params["wait"] or params["state"] == "absent":
            result["registrations"] = [
                to_dict(registration)
                for name in names
                if (registration := get_domain_or_none(api, name)) is not None
            ]
        result["planned_actions"] = actions
        module.exit_json(**result)
    except (ValueError, TimeoutError, RuntimeError) as error:
        details = {"changed": mutated}
        if result is not None:
            details["planned_actions"] = result["planned_actions"]
            if "task_id" in result:
                details["task_id"] = result["task_id"]
        module.fail_json(msg=str(error), **details)
    except Exception as error:
        details = {"changed": mutated}
        if result is not None:
            details["planned_actions"] = result["planned_actions"]
            if "task_id" in result:
                details["task_id"] = result["task_id"]
        module.fail_json(msg=f"Scaleway registrar request failed: {error}", **details)


def main():
    argument_spec = scaleway_argument_spec()
    contact_options = {
        key: dict(type="str", required=True)
        for key in (
            "legal_form",
            "firstname",
            "lastname",
            "email",
            "phone_number",
            "address_line_1",
            "zip",
            "city",
            "country",
        )
    }
    contact_options.update(
        {
            key: dict(type="str")
            for key in (
                "company_name",
                "email_alt",
                "fax_number",
                "address_line_2",
                "vat_identification_code",
                "company_identification_code",
                "lang",
                "state",
            )
        }
    )
    contact_options.update(
        resale=dict(type="bool"),
        whois_opt_in=dict(type="bool"),
        extension_fr=dict(type="dict"),
        extension_eu=dict(type="dict"),
        extension_nl=dict(type="dict"),
    )
    argument_spec.update(
        state=dict(type="str", choices=["present", "absent"], default="present"),
        domain_names=dict(type="list", elements="str", required=True),
        duration_in_years=dict(type="int", default=1),
        owner_contact_id=dict(type="str"),
        owner_contact=dict(type="dict", options=contact_options, no_log=True),
        auto_renew=dict(type="bool", default=False),
        dnssec=dict(type="bool", default=False),
        confirm_purchase=dict(type="bool", default=False),
        wait=dict(type="bool", default=True),
        wait_timeout=dict(type="int", default=3600),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[("owner_contact_id", "owner_contact")],
        supports_check_mode=True,
    )
    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))
    client = scaleway_get_client_from_module(module)
    run(module, DomainV2Beta1RegistrarAPI(client), client.default_project_id)


if __name__ == "__main__":
    main()
