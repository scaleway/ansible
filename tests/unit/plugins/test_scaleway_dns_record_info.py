"""Tests for exact, read-only DNS record lookups."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from ansible_collections.scaleway.scaleway.plugins.module_utils.dns_records import (
    record_to_dict,
)
from ansible_collections.scaleway.scaleway.plugins.modules import (
    scaleway_dns_record_info as module_under_test,
)
from scaleway.domain.v2beta1.types import (
    RecordGeoIPConfig,
    RecordGeoIPConfigMatch,
    RecordType,
)


def record(record_id, data, *, name="www", record_type=RecordType.A, **extra):
    return SimpleNamespace(
        id=record_id,
        name=name,
        type_=record_type,
        data=data,
        ttl=300,
        priority=0,
        comment=None,
        geo_ip_config=extra.get("geo_ip_config"),
        http_service_config=None,
        weighted_config=None,
        view_config=None,
    )


def params(**overrides):
    result = dict(
        dns_zone="example.com",
        record_id=None,
        name="www",
        record_type="A",
        data="192.0.2.1",
        project_id="project-1",
    )
    result.update(overrides)
    return result


def test_selector_accepts_localized_record_id_without_dns_zone():
    selector = module_under_test._parse_selector(
        params(
            dns_zone=None,
            record_id="EXAMPLE.COM./record-1",
            name=None,
            record_type=None,
            data=None,
        )
    )
    assert selector == ("example.com", "record-1", None, None, None)


def test_selector_normalizes_fqdn_to_relative_name():
    selector = module_under_test._parse_selector(params(name="WWW.Example.COM."))
    assert selector == ("example.com", None, "www", "A", "192.0.2.1")


def test_selector_accepts_empty_apex_name():
    selector = module_under_test._parse_selector(params(name=""))
    assert selector[2] == ""


@pytest.mark.parametrize(
    "invalid,reason",
    [
        ({"record_id": "record-1"}, "cannot be combined"),
        (
            {
                "dns_zone": None,
                "record_id": "record-1",
                "name": None,
                "record_type": None,
                "data": None,
            },
            "dns_zone is required",
        ),
        (
            {
                "dns_zone": "other.com",
                "record_id": "example.com/record-1",
                "name": None,
                "record_type": None,
                "data": None,
            },
            "conflicts",
        ),
        ({"record_type": "INVALID"}, "unsupported"),
        ({"data": None}, "required"),
    ],
)
def test_selector_rejects_invalid_or_ambiguous_inputs(invalid, reason):
    with pytest.raises(ValueError, match=reason):
        module_under_test._parse_selector(params(**invalid))


def test_lookup_by_id_uses_id_filter_and_reads_all_pages():
    api = MagicMock()
    wanted = record("record-2", "192.0.2.2")
    api.list_dns_zone_records_all.return_value = [
        record("record-1", "192.0.2.1"),
        wanted,
    ]

    found = module_under_test.lookup_record(
        api, dns_zone="example.com", record_id="record-2", project_id="project-1"
    )

    assert found is wanted
    api.list_dns_zone_records_all.assert_called_once_with(
        dns_zone="example.com", name=None, project_id="project-1", id="record-2"
    )


def test_lookup_by_values_filters_exactly_when_api_returns_superset():
    api = MagicMock()
    wanted = record("record-2", "192.0.2.1")
    api.list_dns_zone_records_all.return_value = [
        record("wrong-name", "192.0.2.1", name="www2"),
        record("wrong-type", "192.0.2.1", record_type=RecordType.AAAA),
        record("wrong-data", "192.0.2.2"),
        wanted,
    ]

    found = module_under_test.lookup_record(
        api,
        dns_zone="example.com",
        name="www",
        record_type="A",
        data="192.0.2.1",
        project_id="project-1",
    )

    assert found is wanted
    api.list_dns_zone_records_all.assert_called_once_with(
        dns_zone="example.com",
        name="www",
        project_id="project-1",
        type_=RecordType.A,
    )


@pytest.mark.parametrize(
    "record_type,api_data,input_data",
    [
        (RecordType.CNAME, "service.example.com.", "service"),
        (RecordType.NS, "ns.example.net.", "NS.EXAMPLE.NET"),
        (RecordType.MX, "10 mail.example.com.", "mail"),
        (RecordType.MX, "0 .", "."),
        (RecordType.TXT, '"v=spf1 -all"', "v=spf1 -all"),
        (RecordType.SRV, "10 0 443 service.example.com.", "10 443 service"),
    ],
)
def test_lookup_handles_api_normalized_dns_data(record_type, api_data, input_data):
    api = MagicMock()
    wanted = record("record-1", api_data, record_type=record_type)
    api.list_dns_zone_records_all.return_value = [wanted]

    found = module_under_test.lookup_record(
        api,
        dns_zone="example.com",
        name="www",
        record_type=record_type.name,
        data=input_data,
    )

    assert found is wanted


def test_lookup_by_values_refuses_duplicate_content():
    api = MagicMock()
    api.list_dns_zone_records_all.return_value = [
        record("one", "192.0.2.1"),
        record("two", "192.0.2.1"),
    ]
    with pytest.raises(ValueError, match="more than one"):
        module_under_test.lookup_record(
            api, dns_zone="example.com", name="www", record_type="A", data="192.0.2.1"
        )


def test_record_output_includes_advanced_configuration():
    geo = RecordGeoIPConfig(
        matches=[
            RecordGeoIPConfigMatch(countries=["FR"], continents=[], data="192.0.2.1")
        ],
        default="192.0.2.2",
    )
    result = record_to_dict(
        record("record-1", "", geo_ip_config=geo), "example.com", "project-1"
    )
    assert result["geo_ip_config"] == {
        "matches": [{"countries": ["FR"], "continents": [], "data": "192.0.2.1"}],
        "default": "192.0.2.2",
    }


def test_run_module_is_read_only_and_returns_record():
    fake_module = MagicMock()
    fake_module.params = params()
    client = MagicMock(default_project_id="project-default")
    api = MagicMock()
    api.list_dns_zone_records_all.return_value = [record("record-1", "192.0.2.1")]
    with patch.object(
        module_under_test, "scaleway_get_client_from_module", return_value=client
    ), patch.object(module_under_test, "DomainV2Beta1API", return_value=api):
        module_under_test.run_module(fake_module)
    fake_module.exit_json.assert_called_once()
    assert fake_module.exit_json.call_args.kwargs["changed"] is False
    assert fake_module.exit_json.call_args.kwargs["record"]["id"] == "record-1"
    api.update_dns_zone_records.assert_not_called()


def test_run_module_fails_when_record_is_missing():
    fake_module = MagicMock()
    fake_module.params = params()
    client = MagicMock(default_project_id="project-1")
    api = MagicMock()
    api.list_dns_zone_records_all.return_value = []
    with patch.object(
        module_under_test, "scaleway_get_client_from_module", return_value=client
    ), patch.object(module_under_test, "DomainV2Beta1API", return_value=api):
        module_under_test.run_module(fake_module)
    assert "No DNS record" in fake_module.fail_json.call_args.kwargs["msg"]
