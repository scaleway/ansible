#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Scaleway Ansible contributors
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Manage one DNS record without replacing its neighbouring records."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: scaleway_dns_record
short_description: Manage one Scaleway DNS record
description:
  - Create, update, or delete one record in a Scaleway DNS zone.
  - Records with the same name and type are independent. Use C(record_id) to select an
    existing record when changing its data, or C(match_data) to select it by its old data.
  - Without either selector, the record is selected by its desired C(data). An ambiguous
    match fails instead of changing another record.
  - Unlike the Terraform resource, this module requires an existing zone by default.
version_added: "2.8.0"
author:
  - Scaleway Ansible contributors
extends_documentation_fragment:
  - scaleway.scaleway.scaleway
requirements:
  - scaleway >= 2.10.1
options:
  state:
    description: Whether the selected record should exist.
    type: str
    choices: [present, absent]
    default: present
  dns_zone:
    description: DNS zone containing the record.
    type: str
    required: true
  name:
    description:
      - Record name relative to the zone. C(@), an empty string, and the zone name
        itself select the apex.
    type: str
    default: ''
  record_type:
    description: DNS record type, for example C(A), C(MX), or C(TXT).
    type: str
    required: true
  data:
    description:
      - Desired record value. Required when C(state=present).
      - With C(state=absent), this selects the record if C(record_id) and C(match_data)
        are omitted.
    type: str
  record_id:
    description:
      - UUID of the particular existing record to update or delete.
      - The Terraform-style C(zone/UUID) form is also accepted if its zone matches C(dns_zone).
    type: str
  match_data:
    description:
      - Existing record value used to select a record while changing its C(data).
      - If this value is missing and the desired record does not already exist,
        the task fails rather than creating a second record.
    type: str
  ttl:
    description: Time to live in seconds (60 through 2592000).
    type: int
    default: 3600
  priority:
    description: Priority for types such as C(MX).
    type: int
    default: 0
  comment:
    description: Optional Scaleway record comment.
    type: str
  geo_ip:
    description: Return different data according to client geography.
    type: dict
    suboptions:
      matches:
        description: Geographic rules that override the default C(data).
        type: list
        elements: dict
        required: true
        suboptions:
          countries:
            description: Two-letter country codes matched by this rule.
            type: list
            elements: str
          continents:
            description: Two-letter continent codes matched by this rule.
            type: list
            elements: str
          data:
            description: Record value returned when this rule matches.
            type: str
            required: true
  http_service:
    description: Return IPs whose HTTP health check succeeds.
    type: dict
    suboptions:
      ips:
        description: Candidate IP addresses checked by the service.
        type: list
        elements: str
        required: true
      must_contain:
        description: Text required in a successful health-check response.
        type: str
        required: true
      url:
        description: HTTP or HTTPS URL used to check candidate IPs.
        type: str
        required: true
      user_agent:
        description: Optional HTTP User-Agent for the health check.
        type: str
      strategy:
        description: Strategy for choosing healthy IP addresses.
        type: str
        choices: [random, hashed, all]
        required: true
  view:
    description: Data selected by client subnet.
    type: list
    elements: dict
    suboptions:
      subnet:
        description: Client CIDR subnet to match.
        type: str
        required: true
      data:
        description: Record value returned for this subnet.
        type: str
        required: true
  weighted:
    description: IPs selected according to their weights.
    type: list
    elements: dict
    suboptions:
      ip:
        description: Candidate IP address.
        type: str
        required: true
      weight:
        description: Relative weight of this IP address.
        type: int
        required: true
  create_zone:
    description:
      - Allow Scaleway to create a missing DNS zone when adding a record.
      - This matches Terraform's automatic zone creation but is opt-in here.
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: Add one of several A records
  scaleway.scaleway.scaleway_dns_record:
    dns_zone: example.com
    name: www
    record_type: A
    data: 192.0.2.10
  delegate_to: localhost

- name: Change just that record's address using the ID returned above
  scaleway.scaleway.scaleway_dns_record:
    dns_zone: example.com
    name: www
    record_type: A
    record_id: "{{ result.record_id }}"
    data: 192.0.2.11
  delegate_to: localhost

- name: Remove one old address while keeping other www A records
  scaleway.scaleway.scaleway_dns_record:
    dns_zone: example.com
    name: www
    record_type: A
    data: 192.0.2.10
    state: absent
  delegate_to: localhost
"""

RETURN = r"""
---
record:
  description: Selected record as returned by Scaleway, or the desired record in check mode.
  returned: when found or state=present
  type: dict
record_id:
  description: UUID of the selected record, if known.
  returned: when found
  type: str
"""

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.scaleway.scaleway.plugins.module_utils.scaleway import (
    scaleway_argument_spec,
    scaleway_get_client_from_module,
)

try:
    from scaleway.domain.v2beta1 import DomainV2Beta1API
    from scaleway_core.api import ScalewayException
    from scaleway.domain.v2beta1.types import (
        Record,
        RecordChange,
        RecordChangeAdd,
        RecordChangeDelete,
        RecordChangeSet,
        RecordGeoIPConfig,
        RecordGeoIPConfigMatch,
        RecordHTTPServiceConfig,
        RecordHTTPServiceConfigStrategy,
        RecordType,
        RecordViewConfig,
        RecordViewConfigView,
        RecordWeightedConfig,
        RecordWeightedConfigWeightedIP,
    )

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False


def _name(value, dns_zone):
    """Use Terraform's relative-name and apex conventions."""
    value = value.rstrip(".").lower()
    dns_zone = dns_zone.rstrip(".").lower()
    if value in ("", "@", dns_zone):
        return ""
    suffix = "." + dns_zone
    return value[: -len(suffix)] if value.endswith(suffix) else value


def _data(value, record_type, dns_zone):
    """Compare API-normalized targets with Terraform-style input values."""
    value = value.strip()
    if record_type == "TXT":
        value = value.strip('"')
    if record_type == "MX":
        parts = value.split(" ", 1)
        if len(parts) == 2 and parts[0].isdigit():
            value = parts[1]
    if record_type in ("CNAME", "NS", "MX") and value == "@":
        return ""
    if record_type == "SRV":
        parts = value.split()
        if len(parts) == 3:
            parts.insert(1, "0")
        if len(parts) == 4:
            suffix = "." + dns_zone.rstrip(".").lower()
            target = parts[3].lower()
            if target.endswith(".") and target[:-1].endswith(suffix):
                parts[3] = target[: -len(suffix) - 1]
            return " ".join(parts)
    if record_type in ("CNAME", "NS", "MX") and value not in ("", "@", "."):
        value = value.lower().rstrip(".")
        if "." not in value:
            value += "." + dns_zone.rstrip(".").lower()
        value += "."
    return value


def _type(value):
    return getattr(value, "name", str(value).upper()).upper()


def _advanced(record):
    """Small canonical representation for comparison and check-mode diffs."""
    geo = getattr(record, "geo_ip_config", None)
    http = getattr(record, "http_service_config", None)
    views = getattr(record, "view_config", None)
    weighted = getattr(record, "weighted_config", None)
    result = {}
    if geo:
        result["geo_ip"] = {
            "matches": [
                {
                    "countries": sorted(match.countries or []),
                    "continents": sorted(match.continents or []),
                    "data": match.data,
                }
                for match in geo.matches
            ]
        }
    if http:
        result["http_service"] = {
            "ips": sorted(str(ip) for ip in http.ips),
            "must_contain": http.must_contain or "",
            "url": http.url,
            "user_agent": http.user_agent or "",
            "strategy": str(getattr(http.strategy, "value", http.strategy)),
        }
    if views:
        result["view"] = sorted(
            ({"subnet": str(view.subnet), "data": view.data} for view in views.views),
            key=lambda item: (item["subnet"], item["data"]),
        )
    if weighted:
        result["weighted"] = sorted(
            (
                {"ip": str(item.ip), "weight": item.weight}
                for item in weighted.weighted_ips
            ),
            key=lambda item: (item["ip"], item["weight"]),
        )
    return result


def _record_state(record, dns_zone):
    record_type = _type(record.type_)
    return {
        "id": record.id,
        "name": _name(record.name, dns_zone),
        "type": record_type,
        "data": _data(record.data, record_type, dns_zone),
        "ttl": record.ttl,
        "priority": record.priority or 0,
        "comment": record.comment or "",
        **_advanced(record),
    }


def _desired_state(params):
    result = {
        "name": _name(params["name"], params["dns_zone"]),
        "type": params["record_type"].upper(),
        "data": _data(
            params["data"], params["record_type"].upper(), params["dns_zone"]
        ),
        "ttl": params["ttl"],
        "priority": params["priority"],
        "comment": params["comment"] or "",
    }
    if params["geo_ip"] is not None:
        result["geo_ip"] = {
            "matches": [
                {
                    "countries": sorted(item.get("countries") or []),
                    "continents": sorted(item.get("continents") or []),
                    "data": item["data"],
                }
                for item in params["geo_ip"]["matches"]
            ]
        }
    if params["http_service"] is not None:
        item = params["http_service"]
        result["http_service"] = {
            "ips": sorted(item["ips"]),
            "must_contain": item["must_contain"],
            "url": item["url"],
            "user_agent": item.get("user_agent") or "",
            "strategy": item["strategy"],
        }
    if params["view"] is not None:
        result["view"] = sorted(
            params["view"], key=lambda item: (item["subnet"], item["data"])
        )
    if params["weighted"] is not None:
        result["weighted"] = sorted(
            params["weighted"], key=lambda item: (item["ip"], item["weight"])
        )
    return result


def _sdk_record(params):
    geo = params["geo_ip"]
    http = params["http_service"]
    view = params["view"]
    weighted = params["weighted"]
    return Record(
        data=_data(params["data"], params["record_type"].upper(), params["dns_zone"]),
        name=_name(params["name"], params["dns_zone"]),
        priority=params["priority"],
        ttl=params["ttl"],
        type_=RecordType[params["record_type"].upper()],
        id=None,
        comment=params["comment"],
        geo_ip_config=(
            RecordGeoIPConfig(
                matches=[
                    RecordGeoIPConfigMatch(
                        countries=item.get("countries") or [],
                        continents=item.get("continents") or [],
                        data=item["data"],
                    )
                    for item in geo["matches"]
                ],
                default=params["data"],
            )
            if geo is not None
            else None
        ),
        http_service_config=(
            RecordHTTPServiceConfig(
                ips=http["ips"],
                url=http["url"],
                strategy=RecordHTTPServiceConfigStrategy[http["strategy"].upper()],
                must_contain=http["must_contain"],
                user_agent=http.get("user_agent"),
            )
            if http is not None
            else None
        ),
        view_config=(
            RecordViewConfig(views=[RecordViewConfigView(**item) for item in view])
            if view is not None
            else None
        ),
        weighted_config=(
            RecordWeightedConfig(
                weighted_ips=[
                    RecordWeightedConfigWeightedIP(**item) for item in weighted
                ]
            )
            if weighted is not None
            else None
        ),
    )


def _select(records, params):
    """Select exactly one record; never guess among duplicate values."""
    record_type = params["record_type"].upper()
    name = _name(params["name"], params["dns_zone"])
    records = [
        record
        for record in records
        if _name(record.name, params["dns_zone"]) == name
        and _type(record.type_) == record_type
    ]
    if params["record_id"]:
        matches = [record for record in records if record.id == params["record_id"]]
    else:
        selector = (
            params["match_data"] if params["match_data"] is not None else params["data"]
        )
        if selector is None:
            raise ValueError(
                "record_id, match_data, or data is required to select a record"
            )
        selector = _data(selector, record_type, params["dns_zone"])
        matches = [
            record
            for record in records
            if _data(record.data, record_type, params["dns_zone"]) == selector
        ]
    if len(matches) > 1:
        raise ValueError("Multiple records match; specify record_id to select one")
    return matches[0] if matches else None


def _list_records(api, params):
    kwargs = {
        "dns_zone": params["dns_zone"].rstrip(".").lower(),
        "name": _name(params["name"], params["dns_zone"]),
        "type_": RecordType[params["record_type"].upper()],
    }
    if params["project_id"]:
        kwargs["project_id"] = params["project_id"]
    return list(api.list_dns_zone_records_all(**kwargs))


def run_module(module):
    params = dict(module.params)
    try:
        record_type = params["record_type"].upper()
        if params["record_id"] and "/" in params["record_id"]:
            id_zone, record_id = params["record_id"].split("/", 1)
            if (
                id_zone.rstrip(".").lower() != params["dns_zone"].rstrip(".").lower()
                or not record_id
                or "/" in record_id
            ):
                raise ValueError(
                    "record_id zone must match dns_zone and have the form zone/UUID"
                )
            params["record_id"] = record_id
        if record_type not in RecordType.__members__ or record_type == "UNKNOWN":
            raise ValueError("Unsupported DNS record type: %s" % record_type)
        if params["state"] == "present" and params["data"] is None:
            raise ValueError("data is required when state=present")
        if params["state"] == "absent" and not any(
            params[key] is not None for key in ("record_id", "match_data", "data")
        ):
            raise ValueError(
                "record_id, match_data, or data is required when state=absent"
            )
        if not 60 <= params["ttl"] <= 2592000 or params["priority"] < 0:
            raise ValueError("ttl must be 60..2592000 and priority must be nonnegative")
        if params["geo_ip"] is not None and not params["geo_ip"]["matches"]:
            raise ValueError("geo_ip.matches must contain at least one item")
        if params["http_service"] is not None and not params["http_service"]["ips"]:
            raise ValueError("http_service.ips must contain at least one IP")
        if params["weighted"] is not None and any(
            item["weight"] < 0 for item in params["weighted"]
        ):
            raise ValueError("weighted weights must be nonnegative")

        client = scaleway_get_client_from_module(module)
        api = DomainV2Beta1API(client)
        try:
            existing = _list_records(api, params)
        except ScalewayException as exc:
            if exc.status_code != 404 or (
                params["state"] == "present" and not params["create_zone"]
            ):
                raise
            existing = []
        selected = _select(existing, params)
        if selected is None and params["record_id"] and params["state"] == "present":
            raise ValueError("record_id was not found in this name, type, and zone")
        if selected is None and params["match_data"] and params["state"] == "present":
            # An already-updated record is still an idempotent success.
            updated_params = dict(params, match_data=None)
            selected = _select(existing, updated_params)
            if selected is None:
                raise ValueError(
                    "match_data was not found; refusing to add another record"
                )

        before = _record_state(selected, params["dns_zone"]) if selected else None
        after = _desired_state(params) if params["state"] == "present" else None
        changed = (
            selected is not None
            if params["state"] == "absent"
            else selected is None
            or {key: value for key, value in before.items() if key != "id"} != after
        )
        record_id = selected.id if selected else None

        if changed and not module.check_mode:
            if params["state"] == "absent":
                change = RecordChange(delete=RecordChangeDelete(id=record_id))
            elif selected is None:
                change = RecordChange(
                    add=RecordChangeAdd(records=[_sdk_record(params)])
                )
            else:
                change = RecordChange(
                    set_=RecordChangeSet(id=record_id, records=[_sdk_record(params)])
                )
            api.update_dns_zone_records(
                dns_zone=params["dns_zone"].rstrip(".").lower(),
                changes=[change],
                disallow_new_zone_creation=not params["create_zone"],
            )
            if params["state"] == "present" and selected is None:
                refreshed = _list_records(api, params)
                candidates = [
                    record
                    for record in refreshed
                    if _name(record.name, params["dns_zone"]) == after["name"]
                    and _type(record.type_) == after["type"]
                    and _data(record.data, after["type"], params["dns_zone"])
                    == after["data"]
                ]
                if record_id:
                    candidates = [
                        record for record in candidates if record.id == record_id
                    ]
                else:
                    previous_ids = {record.id for record in existing}
                    new_candidates = [
                        record for record in candidates if record.id not in previous_ids
                    ]
                    candidates = new_candidates or candidates
                if len(candidates) == 1:
                    record_id = candidates[0].id
                    after = {"id": record_id, **after}
        module.exit_json(
            changed=changed,
            record=after if params["state"] == "present" else None,
            record_id=record_id,
            diff={"before": before, "after": after},
        )
    except ValueError as exc:
        module.fail_json(msg=str(exc))
    except Exception as exc:
        module.fail_json(msg="Failed to manage DNS record: %s" % exc)


def main():
    argument_spec = scaleway_argument_spec()
    argument_spec.update(
        state=dict(type="str", choices=["present", "absent"], default="present"),
        dns_zone=dict(type="str", required=True),
        name=dict(type="str", default=""),
        record_type=dict(type="str", required=True),
        data=dict(type="str"),
        record_id=dict(type="str"),
        match_data=dict(type="str"),
        ttl=dict(type="int", default=3600),
        priority=dict(type="int", default=0),
        comment=dict(type="str"),
        geo_ip=dict(
            type="dict",
            options=dict(
                matches=dict(
                    type="list",
                    elements="dict",
                    required=True,
                    options=dict(
                        countries=dict(type="list", elements="str"),
                        continents=dict(type="list", elements="str"),
                        data=dict(type="str", required=True),
                    ),
                ),
            ),
        ),
        http_service=dict(
            type="dict",
            options=dict(
                ips=dict(type="list", elements="str", required=True),
                must_contain=dict(type="str", required=True),
                url=dict(type="str", required=True),
                user_agent=dict(type="str"),
                strategy=dict(
                    type="str", required=True, choices=["random", "hashed", "all"]
                ),
            ),
        ),
        view=dict(
            type="list",
            elements="dict",
            options=dict(
                subnet=dict(type="str", required=True),
                data=dict(type="str", required=True),
            ),
        ),
        weighted=dict(
            type="list",
            elements="dict",
            options=dict(
                ip=dict(type="str", required=True),
                weight=dict(type="int", required=True),
            ),
        ),
        create_zone=dict(type="bool", default=False),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[("geo_ip", "http_service", "view", "weighted")],
        supports_check_mode=True,
    )
    if not HAS_SCALEWAY_SDK:
        module.fail_json(msg=missing_required_lib("scaleway"))
    run_module(module)


if __name__ == "__main__":
    main()
