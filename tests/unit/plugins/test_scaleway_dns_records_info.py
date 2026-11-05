"""Tests for paginated DNS record listing across projects and zones."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from ansible_collections.scaleway.scaleway.plugins.modules import (
    scaleway_dns_records_info as module_under_test,
)
from scaleway.domain.v2beta1.types import RecordType


def record(record_id, *, name="www", record_type=RecordType.A, data="192.0.2.1"):
    return SimpleNamespace(
        id=record_id,
        name=name,
        type_=record_type,
        data=data,
        ttl=300,
        priority=0,
        comment=None,
        geo_ip_config=None,
        http_service_config=None,
        weighted_config=None,
        view_config=None,
    )


def params(**overrides):
    result = dict(
        dns_zones=["example.com"],
        project_ids=None,
        project_id="project-1",
        organization_id=None,
        name=None,
        record_type=None,
    )
    result.update(overrides)
    return result


@pytest.mark.parametrize(
    "invalid,reason",
    [
        ({"dns_zones": []}, "dns_zones"),
        ({"dns_zones": ["*", "example.com"]}, "only entry"),
        ({"project_ids": ["*", "project-2"], "project_id": None}, "only entry"),
        ({"project_ids": ["project-2"]}, "cannot be combined"),
        ({"record_type": "unknown"}, "unsupported"),
    ],
)
def test_invalid_filters_fail_without_api_calls(invalid, reason):
    with pytest.raises(ValueError, match=reason):
        module_under_test._validate_filters(params(**invalid))


def test_project_wildcard_discovers_all_accessible_projects():
    client = MagicMock(default_project_id="default")
    account_api = MagicMock()
    account_api.list_projects_all.return_value = [
        SimpleNamespace(id="project-2"),
        SimpleNamespace(id="project-1"),
        SimpleNamespace(id="project-1"),
    ]
    project_ids = module_under_test._projects_to_query(
        client, account_api, params(project_id=None, project_ids=["*"])
    )
    assert project_ids == ["project-1", "project-2"]
    assert client.default_organization_id is None
    account_api.list_projects_all.assert_called_once_with(organization_id=None)


def test_default_project_is_used_if_no_project_ids():
    client = MagicMock(default_project_id="default")
    project_ids = module_under_test._projects_to_query(
        client, MagicMock(), params(project_id=None)
    )
    assert project_ids == ["default"]


def test_project_is_required_when_no_default_exists():
    client = SimpleNamespace(default_project_id=None)
    with pytest.raises(ValueError, match="set project_id"):
        module_under_test._projects_to_query(
            client, MagicMock(), params(project_id=None)
        )


def test_zone_wildcard_discovers_root_and_subzones():
    api = MagicMock()
    api.list_dns_zones_all.return_value = [
        SimpleNamespace(domain="example.com", subdomain=""),
        SimpleNamespace(domain="example.com", subdomain="Dev"),
    ]
    assert module_under_test._zones_to_query(api, "project-1", ["*"]) == [
        "dev.example.com",
        "example.com",
    ]
    api.list_dns_zones_all.assert_called_once_with(domain=None, project_id="project-1")


def test_listing_across_projects_and_zones_returns_every_page_without_duplicates():
    api = MagicMock()
    api.list_dns_zones_all.side_effect = [
        [SimpleNamespace(domain="example.com", subdomain="")],
        [SimpleNamespace(domain="example.com", subdomain="dev")],
    ]
    api.list_dns_zone_records_all.side_effect = [
        [record("a"), record("b", name="other")],
        [record("c", data="192.0.2.3")],
    ]

    records = module_under_test.list_records(api, ["project-1", "project-2"], ["*"])

    assert [(r["project_id"], r["dns_zone"], r["id"]) for r in records] == [
        ("project-1", "example.com", "b"),
        ("project-1", "example.com", "a"),
        ("project-2", "dev.example.com", "c"),
    ]
    assert api.list_dns_zone_records_all.call_args_list[0].kwargs == {
        "dns_zone": "example.com",
        "project_id": "project-1",
        "name": None,
    }


def test_name_and_type_filters_are_checked_exactly():
    api = MagicMock()
    api.list_dns_zone_records_all.return_value = [
        record("right", name="www", record_type=RecordType.A),
        record("wrong-name", name="www2", record_type=RecordType.A),
        record("wrong-type", name="www", record_type=RecordType.AAAA),
    ]
    results = module_under_test.list_records(
        api, ["project-1"], ["EXAMPLE.COM."], name="WWW.EXAMPLE.COM.", record_type="A"
    )
    assert [item["id"] for item in results] == ["right"]
    api.list_dns_zone_records_all.assert_called_once_with(
        dns_zone="example.com", project_id="project-1", name="www", type_=RecordType.A
    )


def test_empty_name_selects_apex_only():
    api = MagicMock()
    api.list_dns_zone_records_all.return_value = [
        record("apex", name=""),
        record("www", name="www"),
    ]
    results = module_under_test.list_records(
        api, ["project-1"], ["example.com"], name=""
    )
    assert [item["id"] for item in results] == ["apex"]


def test_run_module_has_no_mutating_calls():
    fake_module = MagicMock()
    fake_module.params = params()
    client = MagicMock(default_project_id="project-1")
    domain_api = MagicMock()
    domain_api.list_dns_zone_records_all.return_value = [record("record-1")]
    with patch.object(
        module_under_test, "scaleway_get_client_from_module", return_value=client
    ), patch.object(module_under_test, "AccountV3ProjectAPI"), patch.object(
        module_under_test, "DomainV2Beta1API", return_value=domain_api
    ):
        module_under_test.run_module(fake_module)
    fake_module.exit_json.assert_called_once()
    assert fake_module.exit_json.call_args.kwargs["changed"] is False
    assert fake_module.exit_json.call_args.kwargs["total_count"] == 1
    domain_api.update_dns_zone_records.assert_not_called()
