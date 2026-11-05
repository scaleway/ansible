# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Scaleway Ansible contributors
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Shared, exact DNS zone lookup for the Domains and DNS modules."""

from __future__ import absolute_import, division, print_function


def zone_name(domain, subdomain):
    """Build the API's full zone name, including the apex case."""
    return f"{subdomain}.{domain}" if subdomain else domain


def _canonical_name(value):
    return value.rstrip(".").lower()


def matching_zones(api, domain, subdomain, project_id=None):
    """Filter every page exactly; the API's domain filter can return subzones."""
    zones = api.list_dns_zones_all(domain=domain, project_id=project_id)
    return [
        zone
        for zone in zones
        if _canonical_name(zone.domain) == _canonical_name(domain)
        and _canonical_name(zone.subdomain) == _canonical_name(subdomain)
        and (project_id is None or zone.project_id == project_id)
    ]


def one_matching_zone(api, domain, subdomain, project_id=None):
    """Return a single exact zone, or fail closed if identity is ambiguous."""
    zones = matching_zones(api, domain, subdomain, project_id)
    if len(zones) > 1:
        raise ValueError(
            f"More than one DNS zone matches {zone_name(domain, subdomain)}; specify project_id"
        )
    return zones[0] if zones else None


def zone_to_dict(zone):
    """Expose the fields returned by the Terraform zone resource/data source."""
    status = getattr(zone.status, "value", zone.status)
    linked_products = [getattr(item, "value", item) for item in zone.linked_products]
    return {
        "id": zone_name(zone.domain, zone.subdomain),
        "domain": zone.domain,
        "subdomain": zone.subdomain,
        "project_id": zone.project_id,
        "ns": list(zone.ns),
        "ns_default": list(zone.ns_default),
        "ns_master": list(zone.ns_master),
        "status": status,
        "message": zone.message,
        "updated_at": zone.updated_at.isoformat() if zone.updated_at else None,
        "linked_products": linked_products,
    }
