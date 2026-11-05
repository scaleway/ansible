"""Shared helpers for Scaleway registrar domain modules."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum


def to_dict(value):
    """Convert SDK objects, enums and dates into Ansible JSON values."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {
            field.name: to_dict(getattr(value, field.name)) for field in fields(value)
        }
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_dict(item) for item in value]
    return value


def is_not_found(error):
    """The SDK raises ScalewayException for a missing registrar domain."""
    return getattr(error, "status_code", None) == 404


def get_domain_or_none(api, domain):
    try:
        return api.get_domain(domain=domain)
    except Exception as error:
        if is_not_found(error):
            return None
        raise


def find_registration_task(api, domain, project_id=None, pending_only=False):
    """Find a task for one domain, including a multi-domain registration task."""
    kwargs = {"domain": domain}
    if project_id:
        kwargs["project_id"] = project_id
    for task in api.list_tasks_all(**kwargs):
        names = [item.strip().lower() for item in (task.domain or "").split(",")]
        if domain.lower() not in names:
            continue
        if pending_only:
            task_type = getattr(task.type_, "value", task.type_)
            status = getattr(task.status, "value", task.status)
            if task_type != "create_domain" or status not in (
                "new",
                "waiting_payment",
                "pending",
            ):
                continue
        return task
    return None


def build_contact(data):
    """Expand the contact fields supported by Terraform's registration block."""
    from scaleway.domain.v2beta1.types import (
        ContactExtensionEU,
        ContactExtensionFR,
        ContactExtensionFRAssociationInfo,
        ContactExtensionFRCodeAuthAfnicInfo,
        ContactExtensionFRDunsInfo,
        ContactExtensionFRIndividualInfo,
        ContactExtensionFRMode,
        ContactExtensionFRTrademarkInfo,
        ContactExtensionNL,
        ContactExtensionNLLegalForm,
        ContactLegalForm,
        NewContact,
    )
    from scaleway.std.types import LanguageCode

    required = (
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
    missing = [key for key in required if not data.get(key)]
    if missing:
        raise ValueError("owner_contact is missing: " + ", ".join(missing))

    optional = (
        "company_name",
        "email_alt",
        "fax_number",
        "address_line_2",
        "vat_identification_code",
        "company_identification_code",
        "state",
    )
    kwargs = {key: data[key] for key in required if key != "legal_form"}
    kwargs.update({key: data[key] for key in optional if data.get(key) is not None})
    kwargs.update(
        legal_form=ContactLegalForm[data["legal_form"].upper()],
        lang=LanguageCode[(data.get("lang") or "en_us").upper()],
        resale=bool(data.get("resale", False)),
        whois_opt_in=bool(data.get("whois_opt_in", False)),
    )

    fr = data.get("extension_fr")
    if fr:
        fr_kwargs = {"mode": ContactExtensionFRMode[fr["mode"].upper()]}
        fr_children = (
            ("individual_info", ContactExtensionFRIndividualInfo),
            ("duns_info", ContactExtensionFRDunsInfo),
            ("association_info", ContactExtensionFRAssociationInfo),
            ("trademark_info", ContactExtensionFRTrademarkInfo),
            ("code_auth_afnic_info", ContactExtensionFRCodeAuthAfnicInfo),
        )
        for key, cls in fr_children:
            if fr.get(key):
                child = dict(fr[key])
                if key == "association_info" and child.get("publication_jo"):
                    child["publication_jo"] = datetime.fromisoformat(
                        child["publication_jo"].replace("Z", "+00:00")
                    )
                fr_kwargs[key] = cls(**child)
        kwargs["extension_fr"] = ContactExtensionFR(**fr_kwargs)

    eu = data.get("extension_eu")
    if eu:
        kwargs["extension_eu"] = ContactExtensionEU(**eu)
    nl = data.get("extension_nl")
    if nl:
        kwargs["extension_nl"] = ContactExtensionNL(
            legal_form=ContactExtensionNLLegalForm[nl["legal_form"].upper()],
            legal_form_registration_number=nl["legal_form_registration_number"],
        )
    return NewContact(**kwargs)
