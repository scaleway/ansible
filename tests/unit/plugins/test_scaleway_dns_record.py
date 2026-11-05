"""A single DNS record must not alter its siblings or drift after a second run."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from ansible_collections.scaleway.scaleway.plugins.modules import scaleway_dns_record
from scaleway.domain.v2beta1 import DomainV2Beta1API


def params(**overrides):
    result = {
        "state": "present",
        "dns_zone": "example.com",
        "name": "www",
        "record_type": "A",
        "data": "192.0.2.10",
        "record_id": None,
        "match_data": None,
        "ttl": 3600,
        "priority": 0,
        "comment": None,
        "geo_ip": None,
        "http_service": None,
        "view": None,
        "weighted": None,
        "create_zone": False,
        "project_id": None,
    }
    result.update(overrides)
    return result


def record(record_id, data, **overrides):
    fields = {
        "id": record_id,
        "name": "www",
        "type_": "A",
        "data": data,
        "ttl": 3600,
        "priority": 0,
        "comment": None,
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


class Finished(SystemExit):
    def __init__(self, result):
        self.result = result


class FakeModule:
    def __init__(self, module_params, check_mode=False):
        self.params = module_params
        self.check_mode = check_mode

    def exit_json(self, **result):
        raise Finished(result)

    def fail_json(self, **result):
        raise ValueError(result["msg"])


def run(module_params, records, check_mode=False):
    api = MagicMock()
    api.list_dns_zone_records_all.side_effect = [records, records]
    with patch.object(
        scaleway_dns_record, "DomainV2Beta1API", return_value=api
    ), patch.object(
        scaleway_dns_record, "scaleway_get_client_from_module", return_value=MagicMock()
    ), pytest.raises(Finished) as result:
        scaleway_dns_record.run_module(FakeModule(module_params, check_mode))
    return result.value.result, api


def test_exact_data_selects_one_record_without_changing_siblings():
    output, api = run(
        params(), [record("chosen", "192.0.2.10"), record("other", "192.0.2.11")]
    )
    assert output["changed"] is False
    assert output["record_id"] == "chosen"
    api.update_dns_zone_records.assert_not_called()


def test_duplicate_data_is_rejected_instead_of_guessing():
    with pytest.raises(ValueError, match="Multiple records match"):
        run(params(), [record("one", "192.0.2.10"), record("two", "192.0.2.10")])


def test_record_id_targets_only_one_update():
    module_params = params(record_id="example.com/chosen", data="192.0.2.12")
    output, api = run(
        module_params, [record("chosen", "192.0.2.10"), record("other", "192.0.2.11")]
    )
    assert output["changed"] is True
    change = api.update_dns_zone_records.call_args.kwargs["changes"][0]
    assert change.set_.id == "chosen"
    assert change.set_.records[0].data == "192.0.2.12"
    assert change.delete is None


def test_missing_value_adds_one_record_without_deleting_siblings():
    output, api = run(params(), [record("other", "192.0.2.11")])
    assert output["changed"] is True
    change = api.update_dns_zone_records.call_args.kwargs["changes"][0]
    assert change.add.records[0].data == "192.0.2.10"
    assert change.delete is None
    assert change.set_ is None


def test_auto_create_zone_is_an_explicit_opt_in():
    api = MagicMock()
    api.list_dns_zone_records_all.side_effect = [
        scaleway_dns_record.ScalewayException(
            SimpleNamespace(status_code=404, text="missing zone")
        ),
        [],
    ]
    with patch.object(
        scaleway_dns_record, "DomainV2Beta1API", return_value=api
    ), patch.object(
        scaleway_dns_record, "scaleway_get_client_from_module", return_value=MagicMock()
    ), pytest.raises(Finished) as result:
        scaleway_dns_record.run_module(FakeModule(params(create_zone=True)))
    assert result.value.result["changed"] is True
    assert (
        api.update_dns_zone_records.call_args.kwargs["disallow_new_zone_creation"]
        is False
    )


def test_absent_deletes_one_id_and_check_mode_does_not_write():
    module_params = params(state="absent", data="192.0.2.10")
    output, api = run(
        module_params, [record("chosen", "192.0.2.10"), record("other", "192.0.2.11")]
    )
    assert output["changed"] is True
    change = api.update_dns_zone_records.call_args.kwargs["changes"][0]
    assert change.delete.id == "chosen"
    checked, check_api = run(
        module_params, [record("chosen", "192.0.2.10")], check_mode=True
    )
    assert checked["changed"] is True
    check_api.update_dns_zone_records.assert_not_called()


def test_missing_old_data_will_not_add_a_duplicate():
    with pytest.raises(ValueError, match="match_data was not found"):
        run(params(match_data="192.0.2.9"), [record("other", "192.0.2.11")])


def test_dynamic_configuration_is_compared_and_targets_id():
    module_params = params(
        geo_ip={
            "matches": [
                {"countries": ["FR"], "continents": ["EU"], "data": "192.0.2.11"}
            ]
        }
    )
    current = record("chosen", "192.0.2.10")
    output, api = run(module_params, [current])
    assert output["changed"] is True
    change = api.update_dns_zone_records.call_args.kwargs["changes"][0]
    assert change.set_.id == "chosen"
    assert change.set_.records[0].geo_ip_config.default == "192.0.2.10"


def test_existing_geo_ip_configuration_is_idempotent():
    module_params = params(
        geo_ip={
            "matches": [
                {"countries": ["FR"], "continents": ["EU"], "data": "192.0.2.11"}
            ]
        }
    )
    current = record(
        "chosen",
        "192.0.2.10",
        geo_ip_config=scaleway_dns_record.RecordGeoIPConfig(
            matches=[
                scaleway_dns_record.RecordGeoIPConfigMatch(
                    countries=["FR"], continents=["EU"], data="192.0.2.11"
                )
            ],
            default="192.0.2.10",
        ),
    )

    output, api = run(module_params, [current])

    assert output["changed"] is False
    api.update_dns_zone_records.assert_not_called()


@pytest.mark.parametrize(
    "field,value,sdk_field",
    [
        (
            "geo_ip",
            {
                "matches": [
                    {
                        "countries": ["FR"],
                        "continents": ["EU"],
                        "data": "192.0.2.11",
                    }
                ]
            },
            "geo_ip_config",
        ),
        (
            "http_service",
            {
                "ips": ["192.0.2.11"],
                "must_contain": "ok",
                "url": "https://example.com/health",
                "strategy": "hashed",
            },
            "http_service_config",
        ),
        ("view", [{"subnet": "192.0.2.0/24", "data": "192.0.2.11"}], "view_config"),
        ("weighted", [{"ip": "192.0.2.11", "weight": 2}], "weighted_config"),
    ],
)
def test_sdk_serializes_each_dynamic_configuration(field, value, sdk_field):
    change = scaleway_dns_record.RecordChange(
        add=scaleway_dns_record.RecordChangeAdd(
            records=[scaleway_dns_record._sdk_record(params(**{field: value}))]
        )
    )
    api = DomainV2Beta1API(MagicMock())
    api._request = MagicMock(side_effect=RuntimeError("stop before network"))
    with pytest.raises(RuntimeError, match="stop before network"):
        api.update_dns_zone_records(
            dns_zone="example.com",
            changes=[change],
            disallow_new_zone_creation=True,
        )
    body = json.loads(json.dumps(api._request.call_args.kwargs["body"]))
    assert sdk_field in body["changes"][0]["add"]["records"][0]


def test_mx_txt_srv_and_apex_normalization():
    assert scaleway_dns_record._name("@", "example.com") == ""
    assert scaleway_dns_record._name("WWW.Example.com.", "example.com") == "www"
    assert (
        scaleway_dns_record._data("10 mail.example.com.", "MX", "example.com")
        == "mail.example.com."
    )
    assert scaleway_dns_record._data('"hello"', "TXT", "example.com") == "hello"
    assert (
        scaleway_dns_record._data("10 443 web.example.com.", "SRV", "example.com")
        == "10 0 443 web"
    )
