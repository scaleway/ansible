#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Scaleway Ansible contributors
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Manage all records with one name and type in a Scaleway DNS zone."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_dns_record_set
short_description: Manage a set of Scaleway DNS records
description:
  - Manage all records with one name and type in an existing Scaleway DNS zone.
  - Only records matching both C(name) and C(record_type) are changed.
  - This module supports ordinary DNS records. It refuses to replace records with
    geo-IP, HTTP service, weighted, or view configurations.
version_added: "2.8.0"
author:
  - Scaleway Ansible contributors
extends_documentation_fragment:
  - scaleway.scaleway.scaleway
requirements:
  - scaleway >= 2.10.1
options:
  state:
    description:
      - Whether the record set should match C(records) or be removed.
    type: str
    choices: [present, absent]
    default: present
  dns_zone:
    description:
      - Name of an existing DNS zone, such as C(example.com).
      - This module never creates a DNS zone.
    type: str
    required: true
  name:
    description:
      - Record name relative to the DNS zone, such as C(www).
      - Use an empty string for records at the zone apex.
    type: str
    required: true
  record_type:
    description:
      - DNS record type, such as C(A), C(AAAA), C(TXT), or C(MX).
    type: str
    required: true
  records:
    description:
      - Complete desired list of records with this name and type.
      - Required and nonempty when C(state=present). Omit for C(state=absent).
    type: list
    elements: dict
    suboptions:
      data:
        description: DNS record value.
        type: str
        required: true
      ttl:
        description: Time to live in seconds.
        type: int
        default: 300
      priority:
        description: Priority for record types such as C(MX).
        type: int
      comment:
        description: Optional comment stored by Scaleway.
        type: str
"""

EXAMPLES = r"""
- name: Point www at two IPv4 addresses
  scaleway.scaleway.scaleway_dns_record_set:
    dns_zone: example.com
    name: www
    record_type: A
    records:
      - data: 192.0.2.10
        ttl: 300
      - data: 192.0.2.11
        ttl: 300
  delegate_to: localhost

- name: Remove the old TXT record set at the zone apex
  scaleway.scaleway.scaleway_dns_record_set:
    dns_zone: example.com
    name: ""
    record_type: TXT
    state: absent
  delegate_to: localhost
"""

RETURN = r"""
---
records:
  description: Existing matching records before the operation.
  returned: always
  type: list
  elements: dict
changes:
  description: Scaleway record changes applied or planned in check mode.
  returned: always
  type: list
  elements: dict
"""

from collections import Counter

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.scaleway.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_get_client_from_module,
)

try:
    from scaleway.domain.v2beta1 import DomainV2Beta1API
    from scaleway.domain.v2beta1.types import (
        Record,
        RecordChange,
        RecordChangeAdd,
        RecordChangeDelete,
        RecordType,
    )

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def _type_name(value):
    return getattr(value, "value", value).upper()


def _record_key(record):
    return (
        record["data"],
        record["ttl"],
        record.get("priority") or 0,
        record.get("comment") or "",
    )


def reconcile_records(existing, desired, name, record_type, state):
    """Return a minimal, record-ID-based PATCH plan for one exact record set."""
    matching = [
        record
        for record in existing
        if record["name"].lower() == name.lower()
        and record["type"].upper() == record_type.upper()
    ]
    if state == "absent":
        return [{"delete": {"id": record["id"]}} for record in matching]

    remaining = Counter(_record_key(record) for record in desired)
    changes = []
    for record in matching:
        key = _record_key(record)
        if remaining[key]:
            remaining[key] -= 1
        else:
            changes.append({"delete": {"id": record["id"]}})

    additions = []
    for record in desired:
        key = _record_key(record)
        if remaining[key]:
            additions.append(
                {
                    "name": name,
                    "type": record_type,
                    **{
                        field: value
                        for field, value in record.items()
                        if value is not None
                    },
                }
            )
            remaining[key] -= 1
    if additions:
        changes.append({"add": {"records": additions}})
    return changes


def list_matching_records(api, dns_zone, name, record_type, project_id=None):
    """Read every page, then filter exactly because the API name filter may vary."""
    params = dict(dns_zone=dns_zone, name=name, type_=RecordType[record_type])
    if project_id:
        params["project_id"] = project_id

    matching = []
    for record in api.list_dns_zone_records_all(**params):
        if (
            record.name.lower() != name.lower()
            or _type_name(record.type_) != record_type
        ):
            continue
        item = dict(
            id=record.id,
            name=record.name,
            type=_type_name(record.type_),
            data=record.data,
            ttl=record.ttl,
            priority=record.priority,
            comment=record.comment,
        )
        for field in (
            "geo_ip_config",
            "http_service_config",
            "weighted_config",
            "view_config",
        ):
            value = getattr(record, field, None)
            if value is not None:
                item["has_advanced_configuration"] = True
        matching.append(item)
    return matching


def _to_sdk_changes(changes):
    result = []
    for change in changes:
        if "delete" in change:
            result.append(
                RecordChange(
                    add=None,
                    set_=None,
                    delete=RecordChangeDelete(
                        id=change["delete"]["id"], id_fields=None
                    ),
                    clear=None,
                )
            )
            continue
        records = []
        for item in change["add"]["records"]:
            records.append(
                Record(
                    data=item["data"],
                    name=item["name"],
                    priority=item.get("priority", 0),
                    ttl=item["ttl"],
                    type_=RecordType[item["type"]],
                    id=None,
                    comment=item.get("comment"),
                    geo_ip_config=None,
                    http_service_config=None,
                    weighted_config=None,
                    view_config=None,
                )
            )
        result.append(
            RecordChange(
                add=RecordChangeAdd(records=records),
                set_=None,
                delete=None,
                clear=None,
            )
        )
    return result


def _diff_records(records, name, record_type):
    """Show the managed values without provider IDs or API default fields."""
    result = []
    for record in records:
        item = dict(
            name=name,
            type=record_type,
            data=record["data"],
            ttl=record["ttl"],
        )
        if record.get("priority"):
            item["priority"] = record["priority"]
        if record.get("comment"):
            item["comment"] = record["comment"]
        result.append(item)
    return sorted(result, key=_record_key)


def run_module(module):
    try:
        params = module.params
        record_type = params["record_type"].upper()
        record_name = params["name"].lower()
        dns_zone = params["dns_zone"].lower()
        if record_type not in RecordType.__members__:
            module.fail_json(msg="Unsupported DNS record type: %s" % record_type)
        desired = params["records"] or []
        if params["state"] == "present":
            if not desired:
                module.fail_json(msg="records must be nonempty when state=present")
            for record in desired:
                if record["ttl"] < 0 or (record.get("priority") or 0) < 0:
                    module.fail_json(msg="ttl and priority must be nonnegative")

        client = scaleway_get_client_from_module(module)
        api = DomainV2Beta1API(client)
        existing = list_matching_records(
            api,
            dns_zone,
            record_name,
            record_type,
            project_id=params["project_id"],
        )
        if params["state"] == "present":
            if any(record.get("has_advanced_configuration") for record in existing):
                module.fail_json(
                    msg="This record set contains advanced DNS records that this module cannot manage"
                )
        changes = reconcile_records(
            existing, desired, record_name, record_type, params["state"]
        )
        diff = dict(
            before=_diff_records(existing, record_name, record_type),
            after=(
                _diff_records(desired, record_name, record_type)
                if params["state"] == "present"
                else []
            ),
        )
        if changes and not module.check_mode:
            api.update_dns_zone_records(
                dns_zone=dns_zone,
                changes=_to_sdk_changes(changes),
                disallow_new_zone_creation=True,
            )
        module.exit_json(
            changed=bool(changes), records=existing, changes=changes, diff=diff
        )
    except ValueError as exc:
        module.fail_json(msg="Invalid DNS record type or value: %s" % exc)
    except Exception as exc:
        module.fail_json(msg="Failed to manage DNS record set: %s" % exc)


def main():
    argument_spec = scaleway_argument_spec()
    argument_spec.update(
        state=dict(type="str", choices=["present", "absent"], default="present"),
        dns_zone=dict(type="str", required=True),
        name=dict(type="str", required=True),
        record_type=dict(type="str", required=True),
        records=dict(
            type="list",
            elements="dict",
            options=dict(
                data=dict(type="str", required=True),
                ttl=dict(type="int", default=300),
                priority=dict(type="int"),
                comment=dict(type="str"),
            ),
        ),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))
    run_module(module)


if __name__ == "__main__":
    main()
