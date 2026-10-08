"""Tests for reconciling one DNS record set without changing other records."""

import json
from contextlib import ExitStack
from enum import Enum
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from ansible_collections.scaleway.scaleway.plugins.modules import (
    scaleway_dns_record_set,
)
from scaleway.domain.v2beta1 import DomainV2Beta1API


class FakeRecordType(str, Enum):
    A = "A"
    AAAA = "AAAA"
    TXT = "TXT"


def record(record_id, data, *, name="www", record_type="A", ttl=300, **fields):
    return {
        "id": record_id,
        "name": name,
        "type": record_type,
        "data": data,
        "ttl": ttl,
        **fields,
    }


def desired(data, *, ttl=300, **fields):
    return {"data": data, "ttl": ttl, **fields}


def reconcile(existing, wanted, *, state="present", name="www", record_type="A"):
    return scaleway_dns_record_set.reconcile_records(
        existing, wanted, name, record_type, state
    )


def test_matching_rrset_is_idempotent_even_if_order_changes():
    existing = [
        record("a", "192.0.2.1", extra_api_field="ignored"),
        record("b", "192.0.2.2"),
    ]
    wanted = [desired("192.0.2.2"), desired("192.0.2.1")]

    assert reconcile(existing, wanted) == []


def test_api_defaults_for_optional_fields_do_not_cause_perpetual_updates():
    existing = [record("a", "192.0.2.1", priority=0, comment="")]

    assert reconcile(existing, [desired("192.0.2.1")]) == []


def test_dns_name_and_type_case_do_not_cause_updates():
    existing = [record("a", "192.0.2.1", name="WWW", record_type="a")]

    assert reconcile(existing, [desired("192.0.2.1")]) == []


def test_reconciliation_changes_only_missing_and_stale_members():
    existing = [
        record("keep", "192.0.2.1"),
        record("stale", "192.0.2.2"),
        record("other-name", "192.0.2.3", name="www2"),
        record("other-type", "unrelated", record_type="TXT"),
    ]
    wanted = [desired("192.0.2.1"), desired("192.0.2.4")]

    changes = reconcile(existing, wanted)

    assert {change["delete"]["id"] for change in changes if "delete" in change} == {
        "stale"
    }
    assert [change["add"]["records"] for change in changes if "add" in change] == [
        [{"name": "www", "type": "A", "data": "192.0.2.4", "ttl": 300}]
    ]
    assert len(changes) == 2


def test_metadata_change_replaces_only_affected_record():
    existing = [
        record("old", "mail.example.net.", record_type="MX", priority=10, ttl=300),
        record("keep", "backup.example.net.", record_type="MX", priority=20),
    ]
    wanted = [
        desired("mail.example.net.", ttl=600, priority=10),
        desired("backup.example.net.", priority=20),
    ]

    changes = reconcile(existing, wanted, record_type="MX")

    assert {change["delete"]["id"] for change in changes if "delete" in change} == {
        "old"
    }
    assert [change["add"]["records"] for change in changes if "add" in change] == [
        [
            {
                "name": "www",
                "type": "MX",
                "data": "mail.example.net.",
                "ttl": 600,
                "priority": 10,
            }
        ]
    ]
    assert len(changes) == 2


def test_duplicate_values_are_counted_not_collapsed():
    existing = [record("one", "192.0.2.1")]
    wanted = [desired("192.0.2.1"), desired("192.0.2.1")]

    changes = reconcile(existing, wanted)

    assert changes == [
        {"add": {"records": [{"name": "www", "type": "A", **desired("192.0.2.1")}]}}
    ]


def test_multiple_missing_values_use_one_add_change_in_desired_order():
    changes = reconcile(
        [],
        [desired("192.0.2.2"), desired("192.0.2.1")],
    )

    assert changes == [
        {
            "add": {
                "records": [
                    {"name": "www", "type": "A", **desired("192.0.2.2")},
                    {"name": "www", "type": "A", **desired("192.0.2.1")},
                ]
            }
        }
    ]


def test_apex_name_and_comment_are_part_of_the_desired_record():
    changes = reconcile(
        [],
        [desired("v=spf1 -all", comment="SPF policy")],
        name="",
        record_type="TXT",
    )

    assert changes == [
        {
            "add": {
                "records": [
                    {
                        "name": "",
                        "type": "TXT",
                        **desired("v=spf1 -all", comment="SPF policy"),
                    }
                ]
            }
        }
    ]


def test_absent_removes_only_exact_name_and_type():
    existing = [
        record("target-1", "192.0.2.1"),
        record("target-2", "192.0.2.2"),
        record("other-name", "192.0.2.3", name="www2"),
        record("other-type", "unrelated", record_type="TXT"),
    ]

    changes = reconcile(existing, [], state="absent")

    assert {change["delete"]["id"] for change in changes} == {
        "target-1",
        "target-2",
    }
    assert len(changes) == 2


def test_absent_is_idempotent():
    assert (
        reconcile([record("other", "192.0.2.1", name="www2")], [], state="absent") == []
    )


def test_sdk_serializes_addressed_deletion_and_addition():
    changes = reconcile(
        [record("old-id", "192.0.2.1")],
        [desired("192.0.2.2")],
    )
    api = DomainV2Beta1API(MagicMock())
    api._request = MagicMock(side_effect=RuntimeError("stop before network"))
    with pytest.raises(RuntimeError, match="stop before network"):
        api.update_dns_zone_records(
            dns_zone="example.com",
            changes=scaleway_dns_record_set._to_sdk_changes(changes),
            disallow_new_zone_creation=True,
        )

    assert api._request.call_args.args[:2] == (
        "PATCH",
        "/domain/v2beta1/dns-zones/example.com/records",
    )
    payload = api._request.call_args.kwargs["body"]

    assert json.loads(json.dumps(payload)) == {
        "changes": [
            {"delete": {"id": "old-id"}},
            {
                "add": {
                    "records": [
                        {
                            "data": "192.0.2.2",
                            "name": "www",
                            "priority": 0,
                            "ttl": 300,
                            "type": "a",
                        }
                    ]
                }
            },
        ],
        "disallow_new_zone_creation": True,
    }


def test_listing_uses_all_pages_and_filters_exact_name_and_type():
    api = MagicMock()
    # The SDK's *_all method handles pagination. Its iterable can still contain
    # other names/types because the API's name filter need not be exact.
    api.list_dns_zone_records_all.return_value = iter(
        [
            SimpleNamespace(
                id="first",
                name="WWW",
                type_="A",
                data="192.0.2.1",
                ttl=300,
                priority=0,
                comment="",
            ),
            SimpleNamespace(
                id="other-name",
                name="www2",
                type_="A",
                data="192.0.2.2",
                ttl=300,
                priority=0,
                comment="",
            ),
            SimpleNamespace(
                id="other-type",
                name="www",
                type_="AAAA",
                data="2001:db8::1",
                ttl=300,
                priority=0,
                comment="",
            ),
            SimpleNamespace(
                id="second-page",
                name="www",
                type_="A",
                data="192.0.2.3",
                ttl=600,
                priority=0,
                comment="",
            ),
        ]
    )

    with patch.object(
        scaleway_dns_record_set, "RecordType", FakeRecordType, create=True
    ):
        result = scaleway_dns_record_set.list_matching_records(
            api, "example.com", "www", "A", project_id="project-id"
        )

    assert [item["id"] for item in result] == ["first", "second-page"]
    assert result[0]["data"] == "192.0.2.1"
    assert result[1]["ttl"] == 600
    api.list_dns_zone_records_all.assert_called_once()
    kwargs = api.list_dns_zone_records_all.call_args.kwargs
    assert kwargs["dns_zone"] == "example.com"
    assert kwargs["name"] == "www"
    assert str(kwargs["type_"]).split(".")[-1] == "A"
    assert kwargs["project_id"] == "project-id"


def test_check_mode_reports_change_without_calling_patch_api():
    module = MagicMock()
    module.params = {
        "state": "present",
        "dns_zone": "example.com",
        "name": "www",
        "record_type": "A",
        "records": [desired("192.0.2.1")],
        "project_id": None,
    }
    module.check_mode = True
    with ExitStack() as stack:
        stack.enter_context(
            patch.object(
                scaleway_dns_record_set, "RecordType", FakeRecordType, create=True
            )
        )
        api_class = stack.enter_context(
            patch.object(scaleway_dns_record_set, "DomainV2Beta1API", create=True)
        )
        stack.enter_context(
            patch.object(scaleway_dns_record_set, "scaleway_get_client_from_module")
        )
        stack.enter_context(
            patch.object(
                scaleway_dns_record_set, "list_matching_records", return_value=[]
            )
        )
        scaleway_dns_record_set.run_module(module)

    api_class.return_value.update_dns_zone_records.assert_not_called()
    module.fail_json.assert_not_called()
    assert module.exit_json.call_args.kwargs["changed"] is True
    assert module.exit_json.call_args.kwargs["changes"] == [
        {
            "add": {
                "records": [
                    {"name": "www", "type": "A", "data": "192.0.2.1", "ttl": 300}
                ]
            }
        }
    ]


def test_unchanged_run_does_not_report_a_diff():
    module = MagicMock()
    module.params = {
        "state": "present",
        "dns_zone": "example.com",
        "name": "www",
        "record_type": "A",
        "records": [desired("192.0.2.1")],
        "project_id": None,
    }
    module.check_mode = True
    with ExitStack() as stack:
        stack.enter_context(
            patch.object(
                scaleway_dns_record_set, "RecordType", FakeRecordType, create=True
            )
        )
        api_class = stack.enter_context(
            patch.object(scaleway_dns_record_set, "DomainV2Beta1API", create=True)
        )
        stack.enter_context(
            patch.object(scaleway_dns_record_set, "scaleway_get_client_from_module")
        )
        stack.enter_context(
            patch.object(
                scaleway_dns_record_set,
                "list_matching_records",
                return_value=[
                    record("existing-id", "192.0.2.1", priority=0, comment="")
                ],
            )
        )
        scaleway_dns_record_set.run_module(module)

    api_class.return_value.update_dns_zone_records.assert_not_called()
    result = module.exit_json.call_args.kwargs
    assert result["changed"] is False
    assert result["diff"]["before"] == result["diff"]["after"]


def test_listing_api_error_fails_instead_of_claiming_success():
    module = MagicMock()
    module.params = {
        "state": "present",
        "dns_zone": "example.com",
        "name": "www",
        "record_type": "A",
        "records": [desired("192.0.2.1")],
        "project_id": None,
    }
    module.check_mode = False
    with ExitStack() as stack:
        stack.enter_context(
            patch.object(
                scaleway_dns_record_set, "RecordType", FakeRecordType, create=True
            )
        )
        api_class = stack.enter_context(
            patch.object(scaleway_dns_record_set, "DomainV2Beta1API", create=True)
        )
        stack.enter_context(
            patch.object(scaleway_dns_record_set, "scaleway_get_client_from_module")
        )
        stack.enter_context(
            patch.object(
                scaleway_dns_record_set,
                "list_matching_records",
                side_effect=RuntimeError("API unavailable"),
            )
        )
        scaleway_dns_record_set.run_module(module)

    module.exit_json.assert_not_called()
    api_class.return_value.update_dns_zone_records.assert_not_called()
    assert "API unavailable" in module.fail_json.call_args.kwargs["msg"]


def test_absent_refuses_to_delete_advanced_record_it_cannot_represent():
    module = MagicMock()
    module.params = {
        "state": "absent",
        "dns_zone": "example.com",
        "name": "www",
        "record_type": "A",
        "records": None,
        "project_id": None,
    }
    module.check_mode = False
    module.fail_json.side_effect = SystemExit(1)
    with ExitStack() as stack:
        api_class = stack.enter_context(
            patch.object(scaleway_dns_record_set, "DomainV2Beta1API")
        )
        stack.enter_context(
            patch.object(scaleway_dns_record_set, "scaleway_get_client_from_module")
        )
        stack.enter_context(
            patch.object(
                scaleway_dns_record_set,
                "list_matching_records",
                return_value=[
                    record("advanced-id", "192.0.2.1", has_advanced_configuration=True)
                ],
            )
        )
        with pytest.raises(SystemExit):
            scaleway_dns_record_set.run_module(module)

    assert "advanced DNS records" in module.fail_json.call_args.kwargs["msg"]
    api_class.return_value.update_dns_zone_records.assert_not_called()
