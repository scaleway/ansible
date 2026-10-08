# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Scaleway Ansible contributors
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Small, shared helpers for Scaleway DNS record modules."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
import re


def normalize_dns_zone(value):
    """Use the DNS zone spelling expected by the API."""
    return value.strip().rstrip(".").lower()


def normalize_record_name(value, dns_zone):
    """Accept both relative and fully-qualified record names."""
    name = value.strip().rstrip(".").lower()
    if name == "@" or name == dns_zone:
        return ""
    suffix = "." + dns_zone
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return name


def _normalize_target_fqdn(value, dns_zone):
    target = value.strip()
    if target in ("", "@"):
        return ""
    if target == ".":
        return "."  # RFC 7505 null MX target
    target = target.lower().rstrip(".")
    if "." in target:
        return target + "."
    return "%s.%s." % (target, dns_zone)


def _normalize_srv_data(value, dns_zone):
    parts = value.split()
    if len(parts) >= 4:
        priority, weight, port, target = parts[:4]
    elif len(parts) == 3:
        priority, port, target = parts
        weight = "0"
    else:
        return value
    target = target.lower()
    zone_suffix = "." + dns_zone + "."
    if target.endswith(zone_suffix):
        target = target[: -len(zone_suffix)]
    return " ".join((priority, weight, port, target))


def normalize_record_data_for_match(data, record_type, dns_zone):
    """Match API-normalized values against Terraform-style record content."""
    value = data.strip()
    if record_type == "TXT":
        return value.strip('"')
    if record_type == "MX":
        # The API may prepend the MX priority even though it is also a field.
        value = re.sub(r"^[0-9]+\s+", "", value, count=1)
    if record_type in ("CNAME", "NS", "MX"):
        return _normalize_target_fqdn(value, dns_zone)
    if record_type == "SRV":
        return _normalize_srv_data(value, dns_zone)
    return value


def _json_value(value):
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {
            field.name: _json_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def record_to_dict(record, dns_zone, project_id=None):
    """Return every supported DNS record setting as an Ansible-safe dictionary."""
    record_type = getattr(record.type_, "name", str(record.type_)).upper()
    name = record.name
    fqdn = dns_zone if name in ("", "@") else "%s.%s" % (name, dns_zone)
    return dict(
        id=record.id,
        localized_id="%s/%s" % (dns_zone, record.id),
        dns_zone=dns_zone,
        project_id=project_id,
        name=name,
        fqdn=fqdn,
        type=record_type,
        data=record.data,
        ttl=record.ttl,
        priority=record.priority,
        comment=record.comment,
        geo_ip_config=_json_value(record.geo_ip_config),
        http_service_config=_json_value(record.http_service_config),
        weighted_config=_json_value(record.weighted_config),
        view_config=_json_value(record.view_config),
    )
