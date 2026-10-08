"""Registrar modules must never buy a domain without explicit authorization."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from scaleway.domain.v2beta1 import DomainV2Beta1RegistrarAPI
from ansible_collections.scaleway.scaleway.plugins.module_utils.dns_registration import (
    build_contact,
    find_registration_task,
    get_domain_or_none,
)
from ansible_collections.scaleway.scaleway.plugins.modules import (
    scaleway_domain_registration as registration_module,
)
from ansible_collections.scaleway.scaleway.plugins.modules import (
    scaleway_domain_registration_info as registration_info,
)


class ModuleExit(BaseException):
    def __init__(self, result):
        self.result = result


class ModuleFail(BaseException):
    def __init__(self, result):
        self.result = result


class MissingDomain(Exception):
    status_code = 404


class FakeModule:
    def __init__(self, *, check_mode=False, **overrides):
        self.params = dict(
            domain_names=["example.com"],
            state="present",
            duration_in_years=1,
            project_id="project-1",
            owner_contact_id=None,
            owner_contact=None,
            auto_renew=False,
            dnssec=False,
            confirm_purchase=False,
            wait=False,
            wait_timeout=60,
        )
        self.params.update(overrides)
        self.check_mode = check_mode

    def exit_json(self, **result):
        raise ModuleExit(result)

    def fail_json(self, **result):
        raise ModuleFail(result)


def domain(
    name="example.com",
    *,
    auto_renew="disabled",
    dnssec="disabled",
    project_id="project-1"
):
    return SimpleNamespace(
        domain=name,
        project_id=project_id,
        auto_renew_status=auto_renew,
        dnssec=SimpleNamespace(status=dnssec, ds_records=[]),
        status="active",
    )


def result_of(module, api):
    with pytest.raises(ModuleExit) as result:
        registration_module.run(module, api)
    return result.value.result


def test_missing_domain_check_mode_plans_purchase_without_billing():
    api = MagicMock()
    api.get_domain.side_effect = MissingDomain()

    result = result_of(FakeModule(check_mode=True), api)

    assert result["changed"] is True
    assert result["planned_actions"] == [
        {"action": "purchase", "domains": ["example.com"], "duration_in_years": 1}
    ]
    api.buy_domains.assert_not_called()


def test_missing_domain_requires_explicit_purchase_confirmation():
    api = MagicMock()
    api.get_domain.side_effect = MissingDomain()

    with pytest.raises(ModuleFail) as failure:
        registration_module.run(FakeModule(), api)

    assert "confirm_purchase=true" in failure.value.result["msg"]
    api.buy_domains.assert_not_called()


def test_missing_domain_requires_one_owner_contact():
    api = MagicMock()
    api.get_domain.side_effect = MissingDomain()

    with pytest.raises(ModuleFail) as failure:
        registration_module.run(FakeModule(confirm_purchase=True), api)

    assert "exactly one" in failure.value.result["msg"]
    api.buy_domains.assert_not_called()


def test_purchase_uses_only_missing_names_and_returns_task():
    api = MagicMock()
    api.get_domain.side_effect = [domain("owned.example"), MissingDomain()]
    api.buy_domains.return_value = SimpleNamespace(task_id="task-123")

    result = result_of(
        FakeModule(
            domain_names=["owned.example", "new.example"],
            owner_contact_id="contact-1",
            confirm_purchase=True,
            project_id="project-1",
        ),
        api,
    )

    api.buy_domains.assert_called_once_with(
        domains=["new.example"],
        duration_in_years=1,
        project_id="project-1",
        owner_contact_id="contact-1",
    )
    assert result["task_id"] == "task-123"
    assert result["pending"] is True


def test_existing_registration_is_idempotent():
    api = MagicMock()
    api.get_domain.return_value = domain()

    result = result_of(FakeModule(), api)

    assert result["changed"] is False
    assert result["planned_actions"] == []
    api.buy_domains.assert_not_called()
    api.enable_domain_dnssec.assert_not_called()


def test_existing_domain_updates_only_requested_features():
    api = MagicMock()
    api.get_domain.return_value = domain(auto_renew="disabled", dnssec="disabled")

    result = result_of(FakeModule(auto_renew=True, dnssec=True), api)

    assert [action["action"] for action in result["planned_actions"]] == [
        "enable_auto_renew",
        "enable_dnssec",
    ]
    api.enable_domain_auto_renew.assert_called_once_with(domain="example.com")
    api.enable_domain_dnssec.assert_called_once_with(domain="example.com")
    api.buy_domains.assert_not_called()


def test_absent_disables_renewal_but_does_not_cancel_domain_or_dnssec():
    api = MagicMock()
    api.get_domain.return_value = domain(auto_renew="enabled", dnssec="enabled")

    result = result_of(FakeModule(state="absent"), api)

    assert result["planned_actions"] == [
        {"domain": "example.com", "action": "disable_auto_renew"}
    ]
    api.disable_domain_auto_renew.assert_called_once_with(domain="example.com")
    api.disable_domain_dnssec.assert_not_called()
    api.buy_domains.assert_not_called()


def test_project_mismatch_is_rejected_before_mutation():
    api = MagicMock()
    api.get_domain.return_value = domain(project_id="another-project")

    with pytest.raises(ModuleFail) as failure:
        registration_module.run(FakeModule(project_id="project-1"), api)

    assert "belongs to project" in failure.value.result["msg"]
    api.buy_domains.assert_not_called()


def test_default_project_from_profile_prevents_cross_project_mutation():
    api = MagicMock()
    api.get_domain.return_value = domain(project_id="another-project")

    with pytest.raises(ModuleFail) as failure:
        registration_module.run(
            FakeModule(project_id=None, auto_renew=True),
            api,
            default_project_id="project-1",
        )

    assert "belongs to project" in failure.value.result["msg"]
    assert failure.value.result["changed"] is False
    api.enable_domain_auto_renew.assert_not_called()


def test_purchase_success_then_wait_failure_reports_billed_task():
    api = MagicMock()
    api.get_domain.side_effect = MissingDomain()
    api.list_tasks_all.return_value = []
    api.buy_domains.return_value = SimpleNamespace(task_id="paid-task")
    module = FakeModule(
        owner_contact_id="contact-1", confirm_purchase=True, wait=True, wait_timeout=1
    )

    with pytest.raises(ModuleFail) as failure:
        registration_module.run(module, api)

    assert failure.value.result["changed"] is True
    assert failure.value.result["task_id"] == "paid-task"
    assert "timed out waiting" in failure.value.result["msg"]


def test_pending_registration_task_is_not_purchased_again():
    api = MagicMock()
    api.get_domain.side_effect = MissingDomain()
    api.list_tasks_all.return_value = [
        SimpleNamespace(
            id="pending-task",
            domain="example.com",
            type_="create_domain",
            status="pending",
        )
    ]

    result = result_of(FakeModule(confirm_purchase=True), api)

    assert result["pending"] is True
    assert result["planned_actions"] == [
        {
            "action": "wait_for_registration",
            "domain": "example.com",
            "task_id": "pending-task",
        }
    ]
    api.buy_domains.assert_not_called()


def test_build_contact_maps_required_fields_and_registry_extension():
    contact = build_contact(
        dict(
            legal_form="individual",
            firstname="Ada",
            lastname="Lovelace",
            email="ada@example.com",
            phone_number="+33123456789",
            address_line_1="1 Test St",
            zip="75001",
            city="Paris",
            country="FR",
            extension_fr=dict(
                mode="individual", individual_info=dict(whois_opt_in=True)
            ),
        )
    )

    assert contact.legal_form.value == "individual"
    assert contact.extension_fr.mode.value == "individual"
    assert contact.extension_fr.individual_info.whois_opt_in is True


def test_sdk_serializes_purchase_and_inline_owner_contact_without_network():
    api = DomainV2Beta1RegistrarAPI(MagicMock())
    api._request = MagicMock(side_effect=RuntimeError("stop before network"))
    contact = build_contact(
        dict(
            legal_form="individual",
            firstname="Ada",
            lastname="Lovelace",
            email="ada@example.com",
            phone_number="+33123456789",
            address_line_1="1 Test St",
            zip="75001",
            city="Paris",
            country="FR",
        )
    )

    with pytest.raises(RuntimeError, match="stop before network"):
        api.buy_domains(
            domains=["example.com", "other.example"],
            duration_in_years=2,
            project_id="project-1",
            owner_contact=contact,
        )

    assert api._request.call_args.args[:2] == ("POST", "/domain/v2beta1/buy-domains")
    body = api._request.call_args.kwargs["body"]
    assert body["domains"] == ["example.com", "other.example"]
    assert body["duration_in_years"] == 2
    assert body["project_id"] == "project-1"
    assert body["owner_contact"]["legal_form"] == "individual"
    assert body["owner_contact"]["lang"] == "en_us"
    assert body["owner_contact"]["email"] == "ada@example.com"


def test_registration_info_uses_multi_domain_task_when_available():
    api = MagicMock()
    api.get_domain.return_value = domain()
    api.list_tasks_all.return_value = [
        SimpleNamespace(id="task-1", domain="example.com, other.example")
    ]

    result = registration_info.read_registration(api, "example.com", "project-1")

    assert result["changed"] is False
    assert result["domain_names"] == ["example.com", "other.example"]
    assert result["task_id"] == "task-1"
    api.list_tasks_all.assert_called_once_with(
        domain="example.com", project_id="project-1"
    )


def test_registration_info_handles_archived_task():
    api = MagicMock()
    api.get_domain.return_value = domain()
    api.list_tasks_all.return_value = []

    result = registration_info.read_registration(api, "example.com")

    assert result["task_id"] is None
    assert result["domain_names"] == ["example.com"]


def test_registration_info_rejects_other_project():
    api = MagicMock()
    api.get_domain.return_value = domain(project_id="another-project")

    with pytest.raises(ValueError, match="belongs to project"):
        registration_info.read_registration(api, "example.com", "project-1")
    api.list_tasks_all.assert_not_called()


def test_task_lookup_matches_exact_domain_not_partial_substring():
    api = MagicMock()
    api.list_tasks_all.return_value = [
        SimpleNamespace(id="wrong", domain="notexample.com"),
        SimpleNamespace(id="right", domain="Example.com, another.example"),
    ]

    assert find_registration_task(api, "example.com").id == "right"


def test_missing_domain_detection_only_swallows_404():
    api = MagicMock()
    api.get_domain.side_effect = MissingDomain()
    assert get_domain_or_none(api, "example.com") is None

    api.get_domain.side_effect = RuntimeError("network failure")
    with pytest.raises(RuntimeError, match="network failure"):
        get_domain_or_none(api, "example.com")
