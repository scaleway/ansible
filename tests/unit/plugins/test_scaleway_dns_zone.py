"""DNS zone lifecycle, exact lookup and list filtering."""

from contextlib import ExitStack
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ansible_collections.scaleway.scaleway.plugins.module_utils.dns_zone import (
    matching_zones,
    one_matching_zone,
    zone_to_dict,
)
from ansible_collections.scaleway.scaleway.plugins.modules import (
    scaleway_dns_zone,
    scaleway_dns_zone_info,
    scaleway_dns_zones_info,
)


class Exited(BaseException):
    def __init__(self, result):
        self.result = result


class Failed(BaseException):
    def __init__(self, result):
        self.result = result


class Module:
    def __init__(self, params, *, check_mode=False):
        self.params = params
        self.check_mode = check_mode

    def exit_json(self, **result):
        raise Exited(result)

    def fail_json(self, **result):
        raise Failed(result)


def zone(domain="example.com", subdomain="test", project_id="project-1"):
    return SimpleNamespace(
        domain=domain,
        subdomain=subdomain,
        project_id=project_id,
        ns=["ns1.example.net"],
        ns_default=["ns-default.example.net"],
        ns_master=[],
        status=SimpleNamespace(value="active"),
        message=None,
        updated_at=datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc),
        linked_products=[],
    )


def run(module_file, params, zones, *, check_mode=False, client_project="project-1"):
    api = MagicMock()
    api.list_dns_zones_all.return_value = zones
    api.create_dns_zone.return_value = zone()
    api.update_dns_zone.return_value = zone()
    client = SimpleNamespace(
        default_project_id=client_project, default_organization_id="org-1"
    )
    module = Module(params, check_mode=check_mode)
    with ExitStack() as stack:
        stack.enter_context(
            patch.object(
                module_file, "scaleway_get_client_from_module", return_value=client
            )
        )
        stack.enter_context(
            patch.object(module_file, "DomainV2Beta1API", return_value=api)
        )
        if module_file is scaleway_dns_zones_info:
            account_api = MagicMock()
            account_api.list_projects_all.return_value = [
                SimpleNamespace(id="project-1"),
                SimpleNamespace(id="project-2"),
            ]
            stack.enter_context(
                patch.object(
                    module_file, "AccountV3ProjectAPI", return_value=account_api
                )
            )
        with pytest.raises((Exited, Failed)) as result:
            module_file.run_module(module)
    return result.value, api, client


def test_zone_lookup_filters_subdomain_and_project_exactly():
    api = MagicMock()
    wanted = zone()
    api.list_dns_zones_all.return_value = [
        zone(subdomain="test2"),
        zone(project_id="project-2"),
        zone(domain="another.com"),
        wanted,
    ]

    assert matching_zones(api, "EXAMPLE.COM", "TEST", "project-1") == [wanted]
    api.list_dns_zones_all.assert_called_once_with(
        domain="EXAMPLE.COM", project_id="project-1"
    )


def test_ambiguous_zone_name_fails_closed_without_project_id():
    api = MagicMock()
    api.list_dns_zones_all.return_value = [zone(), zone(project_id="project-2")]

    with pytest.raises(ValueError, match="specify project_id"):
        one_matching_zone(api, "example.com", "test")


def test_zone_dict_exposes_terraform_attributes_and_root_name():
    result = zone_to_dict(zone(subdomain=""))

    assert result["id"] == "example.com"
    assert result["ns"] == ["ns1.example.net"]
    assert result["status"] == "active"
    assert result["updated_at"] == "2026-10-08T09:00:00+00:00"


def resource_params(state="present", *, project_id="project-1"):
    return {
        "domain": "example.com",
        "subdomain": "test",
        "project_id": project_id,
        "state": state,
        "current_subdomain": None,
    }


def test_existing_zone_is_idempotent():
    result, api, _ = run(scaleway_dns_zone, resource_params(), [zone()])

    assert isinstance(result, Exited)
    assert result.result["changed"] is False
    assert result.result["dns_zone"]["id"] == "test.example.com"
    api.create_dns_zone.assert_not_called()
    api.delete_dns_zone.assert_not_called()


def test_present_creates_only_missing_exact_zone():
    result, api, _ = run(
        scaleway_dns_zone,
        resource_params(),
        [zone(subdomain="other"), zone(project_id="project-2")],
    )

    assert isinstance(result, Exited)
    assert result.result["changed"] is True
    api.create_dns_zone.assert_called_once_with(
        domain="example.com", subdomain="test", project_id="project-1"
    )
    api.delete_dns_zone.assert_not_called()


def test_absent_deletes_only_exact_zone_with_project_id():
    result, api, _ = run(
        scaleway_dns_zone,
        resource_params("absent"),
        [zone(), zone(project_id="project-2")],
    )

    assert isinstance(result, Exited)
    assert result.result["changed"] is True
    assert result.result["deleted"] == "test.example.com"
    api.delete_dns_zone.assert_called_once_with(
        dns_zone="test.example.com", project_id="project-1"
    )


def test_absent_is_idempotent_when_zone_does_not_exist():
    result, api, _ = run(
        scaleway_dns_zone, resource_params("absent"), [zone(subdomain="other")]
    )

    assert isinstance(result, Exited)
    assert result.result["changed"] is False
    api.delete_dns_zone.assert_not_called()


def test_rename_existing_subdomain_uses_update_api():
    params = resource_params()
    params["current_subdomain"] = "old"
    result, api, _ = run(
        scaleway_dns_zone,
        params,
        [zone(subdomain="old")],
    )

    assert isinstance(result, Exited)
    assert result.result["changed"] is True
    api.update_dns_zone.assert_called_once_with(
        dns_zone="old.example.com", new_dns_zone="test", project_id="project-1"
    )
    api.create_dns_zone.assert_not_called()


def test_rename_fails_when_source_and_target_both_exist():
    params = resource_params()
    params["current_subdomain"] = "old"
    result, api, _ = run(
        scaleway_dns_zone,
        params,
        [zone(subdomain="old"), zone()],
    )

    assert isinstance(result, Failed)
    assert "Both source and destination" in result.result["msg"]
    api.update_dns_zone.assert_not_called()


def test_rename_does_not_create_zone_when_source_is_missing():
    params = resource_params()
    params["current_subdomain"] = "old"
    result, api, _ = run(scaleway_dns_zone, params, [])

    assert isinstance(result, Failed)
    assert "Source DNS zone does not exist" in result.result["msg"]
    api.create_dns_zone.assert_not_called()


def test_root_zone_deletion_is_rejected_before_api_call():
    params = resource_params("absent")
    params["subdomain"] = ""
    result, api, _ = run(scaleway_dns_zone, params, [zone(subdomain="")])

    assert isinstance(result, Failed)
    assert "root DNS zone" in result.result["msg"]
    api.delete_dns_zone.assert_not_called()


@pytest.mark.parametrize("state,zones", [("present", []), ("absent", [zone()])])
def test_check_mode_reports_change_without_writing(state, zones):
    result, api, _ = run(
        scaleway_dns_zone, resource_params(state), zones, check_mode=True
    )

    assert isinstance(result, Exited)
    assert result.result["changed"] is True
    if state == "present":
        assert result.result["diff"]["before"] is None
    else:
        assert result.result["diff"]["after"] is None
    api.create_dns_zone.assert_not_called()
    api.delete_dns_zone.assert_not_called()


def test_zone_mutation_requires_project_id():
    result, api, _ = run(
        scaleway_dns_zone,
        resource_params(project_id=None),
        [],
        client_project=None,
    )

    assert isinstance(result, Failed)
    assert "project_id" in result.result["msg"]
    api.list_dns_zones_all.assert_not_called()


def test_zone_info_reads_exact_zone_without_writing():
    result, api, _ = run(
        scaleway_dns_zone_info,
        {"domain": "example.com", "subdomain": "test", "project_id": "project-1"},
        [zone(), zone(subdomain="other")],
    )

    assert isinstance(result, Exited)
    assert result.result["changed"] is False
    assert result.result["dns_zone"]["id"] == "test.example.com"
    api.create_dns_zone.assert_not_called()


def test_zone_info_fails_on_missing_zone():
    result, _, _ = run(
        scaleway_dns_zone_info,
        {"domain": "example.com", "subdomain": "test", "project_id": "project-1"},
        [],
    )

    assert isinstance(result, Failed)
    assert "was not found" in result.result["msg"]


def list_params(**overrides):
    params = {
        "domains": ["example.com"],
        "project_ids": None,
        "project_id": "project-1",
        "organization_id": None,
        "dns_zones": None,
        "created_after": None,
        "created_before": None,
        "updated_after": None,
        "updated_before": None,
    }
    params.update(overrides)
    return params


def test_list_zones_filters_exact_names_and_deduplicates():
    api = MagicMock()
    api.list_dns_zones_all.return_value = [
        zone(),
        zone(),
        zone(subdomain="other"),
        zone(domain="other.com"),
    ]

    result = scaleway_dns_zones_info.list_zones(
        api,
        ["example.com"],
        ["project-1"],
        ["test.example.com"],
        {"created_after": None},
    )

    assert [item["id"] for item in result] == ["test.example.com"]
    api.list_dns_zones_all.assert_called_once_with(
        domain="example.com",
        project_id="project-1",
        dns_zones=["test.example.com"],
        created_after=None,
    )


def test_wildcard_domains_and_projects_enumerate_accessible_projects():
    result, api, client = run(
        scaleway_dns_zones_info,
        list_params(domains=["*"], project_ids=["*"], project_id=None),
        [zone(), zone(domain="another.com", project_id="project-2")],
    )

    assert isinstance(result, Exited)
    assert result.result["changed"] is False
    assert len(result.result["dns_zones"]) == 2
    assert client.default_organization_id is None
    assert api.list_dns_zones_all.call_args.kwargs["domain"] == ""
    assert {
        call.kwargs["project_id"] for call in api.list_dns_zones_all.call_args_list
    } == {
        "project-1",
        "project-2",
    }


def test_multiple_projects_and_domains_issue_all_requests():
    api = MagicMock()
    api.list_dns_zones_all.return_value = []
    scaleway_dns_zones_info.list_zones(
        api,
        ["example.com", "another.com"],
        ["project-1", "project-2"],
        None,
        {},
    )

    assert api.list_dns_zones_all.call_count == 4


def test_rfc3339_date_filters_are_passed_to_sdk():
    result, api, _ = run(
        scaleway_dns_zones_info,
        list_params(created_after="2026-10-08T09:00:00Z"),
        [],
    )

    assert isinstance(result, Exited)
    assert api.list_dns_zones_all.call_args.kwargs["created_after"] == datetime(
        2026, 10, 8, 9, 0, tzinfo=timezone.utc
    )


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"domains": []}, "domains"),
        ({"domains": ["*", "example.com"]}, "domains"),
        ({"project_ids": ["*", "project-1"]}, "project_ids"),
        ({"created_after": "yesterday"}, "created_after"),
        ({"updated_before": "2026-10-08T09:00:00"}, "updated_before"),
    ],
)
def test_invalid_list_filter_fails_before_api_call(changes, expected):
    result, api, _ = run(scaleway_dns_zones_info, list_params(**changes), [])

    assert isinstance(result, Failed)
    assert expected in result.result["msg"]
    api.list_dns_zones_all.assert_not_called()
