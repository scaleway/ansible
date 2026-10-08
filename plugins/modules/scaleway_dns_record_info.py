#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Scaleway Ansible contributors
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Read one Scaleway DNS record without changing it."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_dns_record_info
short_description: Get one Scaleway DNS record
description:
  - Find a DNS record by its ID or by its zone, name, type, and data.
  - The module reads all result pages and fails if a value-based query is ambiguous.
version_added: "2.8.0"
author:
  - Scaleway Ansible contributors
extends_documentation_fragment:
  - scaleway.scaleway.scaleway
requirements:
  - scaleway >= 2.10.1
options:
  dns_zone:
    description:
      - Name of the DNS zone, such as C(example.com).
      - May be omitted only if C(record_id) has the C(zone/id) form.
    type: str
  record_id:
    description:
      - ID of the record, as a bare ID or C(zone/id).
      - Cannot be combined with C(name), C(record_type), or C(data).
    type: str
  name:
    description:
      - Record name relative to the zone. An empty string selects the zone apex.
      - Required when C(record_id) is absent.
    type: str
  record_type:
    description:
      - DNS record type, for example C(A), C(TXT), or C(MX).
      - Required when C(record_id) is absent.
    type: str
  data:
    description:
      - Exact record content. Required when C(record_id) is absent.
    type: str
"""

EXAMPLES = r"""
- name: Find a specific address
  scaleway.scaleway.scaleway_dns_record_info:
    dns_zone: example.com
    name: www
    record_type: A
    data: 192.0.2.10
  register: address
  delegate_to: localhost

- name: Find a record by its localized ID
  scaleway.scaleway.scaleway_dns_record_info:
    record_id: example.com/11111111-1111-1111-1111-111111111111
  register: address
  delegate_to: localhost
"""

RETURN = r"""
---
record:
  description: The matching record, including advanced DNS configuration if present.
  returned: success
  type: dict
  sample:
    id: 11111111-1111-1111-1111-111111111111
    localized_id: example.com/11111111-1111-1111-1111-111111111111
    dns_zone: example.com
    name: www
    type: A
    data: 192.0.2.10
    ttl: 300
"""

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.scaleway.scaleway.plugins.module_utils.dns_records import (
    normalize_dns_zone,
    normalize_record_data_for_match,
    normalize_record_name,
    record_to_dict,
)
from ansible_collections.scaleway.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_get_client_from_module,
)

try:
    from scaleway.domain.v2beta1 import DomainV2Beta1API
    from scaleway.domain.v2beta1.types import RecordType

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def _parse_selector(params):
    """Validate selectors and normalize an optional Terraform-style localized ID."""
    record_id = params["record_id"]
    zone = params["dns_zone"]
    if record_id is not None:
        if any(params[field] is not None for field in ("name", "record_type", "data")):
            raise ValueError(
                "record_id cannot be combined with name, record_type, or data"
            )
        if "/" in record_id:
            id_zone, record_id = record_id.split("/", 1)
            if not id_zone or not record_id or "/" in record_id:
                raise ValueError("record_id must have the form zone/id")
            id_zone = normalize_dns_zone(id_zone)
            if zone and normalize_dns_zone(zone) != id_zone:
                raise ValueError("dns_zone conflicts with the zone in record_id")
            zone = id_zone
        if not zone:
            raise ValueError("dns_zone is required for a bare record_id")
        if not record_id:
            raise ValueError("record_id cannot be empty")
        zone = normalize_dns_zone(zone)
        if not zone:
            raise ValueError("dns_zone cannot be empty")
        return zone, record_id, None, None, None

    if any(
        params[field] is None for field in ("dns_zone", "name", "record_type", "data")
    ):
        raise ValueError(
            "dns_zone, name, record_type, and data are required without record_id"
        )
    zone = normalize_dns_zone(zone)
    if not zone:
        raise ValueError("dns_zone cannot be empty")
    name = normalize_record_name(params["name"], zone)
    record_type = params["record_type"].upper()
    if record_type not in RecordType.__members__ or record_type == "UNKNOWN":
        raise ValueError("unsupported DNS record type: %s" % record_type)
    return zone, None, name, record_type, params["data"]


def lookup_record(
    api,
    *,
    dns_zone,
    record_id=None,
    name=None,
    record_type=None,
    data=None,
    project_id=None
):
    """Read all pages and select exactly one record."""
    query = dict(dns_zone=dns_zone, name=name, project_id=project_id)
    if record_id is not None:
        query["id"] = record_id
    else:
        query["type_"] = RecordType[record_type]
    # The generated SDK marks name as mandatory, but the API accepts its absence
    # for ID-based lookups, as used by the Terraform provider.
    candidates = api.list_dns_zone_records_all(**query)
    matches = []
    for record in candidates:
        if record_id is not None:
            if record.id == record_id:
                matches.append(record)
        elif (
            normalize_record_name(record.name, dns_zone) == name
            and getattr(record.type_, "name", str(record.type_)).upper() == record_type
            and normalize_record_data_for_match(record.data, record_type, dns_zone)
            == normalize_record_data_for_match(data, record_type, dns_zone)
        ):
            matches.append(record)
    if len(matches) > 1:
        raise ValueError(
            "more than one DNS record matches this selector; use record_id"
        )
    return matches[0] if matches else None


def run_module(module):
    try:
        dns_zone, record_id, name, record_type, data = _parse_selector(module.params)
    except ValueError as exc:
        module.fail_json(msg=str(exc))
        return

    try:
        client = scaleway_get_client_from_module(module)
        api = DomainV2Beta1API(client)
        project_id = module.params["project_id"] or client.default_project_id
        record = lookup_record(
            api,
            dns_zone=dns_zone,
            record_id=record_id,
            name=name,
            record_type=record_type,
            data=data,
            project_id=project_id,
        )
    except ValueError as exc:
        module.fail_json(msg=str(exc))
        return
    except Exception as exc:
        module.fail_json(msg="Failed to read DNS record: %s" % exc)
        return

    if record is None:
        module.fail_json(
            msg="No DNS record matches the supplied selector in %s" % dns_zone
        )
        return
    module.exit_json(changed=False, record=record_to_dict(record, dns_zone, project_id))


def main():
    argument_spec = scaleway_argument_spec()
    argument_spec.update(
        dns_zone=dict(type="str"),
        record_id=dict(type="str"),
        name=dict(type="str"),
        record_type=dict(type="str"),
        data=dict(type="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))
    run_module(module)


if __name__ == "__main__":
    main()
