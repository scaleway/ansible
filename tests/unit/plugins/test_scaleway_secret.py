import uuid
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic

from ....plugins.modules import (
    scaleway_secret,
    scaleway_secret_version,
)

import scaleway.secret.v1beta1.api as secret_api


# patch the exit_json method for every methods to avoid returning exit 0
@patch.object(basic.AnsibleModule, "exit_json", MagicMock())
class TestScalewaySecret:
    test_uuid = str(uuid.uuid4())

    @pytest.mark.parametrize(
        "set_module_args",
        [
            {
                "name": "test_secret",
                "project_id": test_uuid,
                "tags": ["test", "secret"],
                "description": "test_description",
                "protected": False,
            }
        ],
        indirect=True,
    )
    @patch.object(secret_api, "unmarshal_Secret")
    @patch.object(secret_api.SecretV1Beta1API, "_request")
    def test_create_with_project_id(
        self,
        mock_request,
        mock_unmarshal_secret,
        scaleway_config_profile,
        set_module_args,
    ):
        mock_unmarshal_secret.return_value = MagicMock()
        mock_request.return_value = MagicMock(status_code=201)
        scaleway_secret.main()
        mock_request.assert_called_once_with(
            "POST",
            f"/secret-manager/v1beta1/regions/{scaleway_config_profile.default_region}/secrets",
            body={
                "name": "test_secret",
                "tags": ["test", "secret"],
                "description": "test_description",
                "protected": False,
                "project_id": self.test_uuid,
            },
        )

    @pytest.mark.parametrize(
        "set_module_args",
        [
            {
                "name": "test_secret",
                "tags": ["test", "secret"],
                "description": "test_description",
                "protected": False,
            }
        ],
        indirect=True,
    )
    @patch.object(secret_api, "unmarshal_Secret")
    @patch.object(secret_api.SecretV1Beta1API, "_request")
    def test_create_with_default_project_id(
        self,
        mock_request,
        mock_unmarshal_secret,
        scaleway_config_profile,
        set_module_args,
    ):
        mock_unmarshal_secret.return_value = MagicMock()
        mock_request.return_value = MagicMock(status_code=201)
        scaleway_secret.main()
        mock_request.assert_called_once_with(
            "POST",
            f"/secret-manager/v1beta1/regions/{scaleway_config_profile.default_region}/secrets",
            body={
                "name": "test_secret",
                "tags": ["test", "secret"],
                "description": "test_description",
                "protected": False,
                "project_id": scaleway_config_profile.default_project_id,
            },
        )

    @pytest.mark.parametrize(
        "set_module_args",
        [
            {
                "name": "test_secret",
                "state": "absent",
            }
        ],
        indirect=True,
    )
    @patch.object(secret_api, "unmarshal_ListSecretsResponse")
    @patch.object(secret_api.SecretV1Beta1API, "_request")
    def test_delete_secret(
        self,
        mock_request,
        mock_unmarshal_list_secrets_response,
        scaleway_config_profile,
        set_module_args,
    ):
        class MockedSecret(MagicMock):
            id = self.test_uuid
            name = "test_secret"

            def __dict__(self):
                pass

        mock_unmarshal_list_secrets_response.return_value = MagicMock(
            secrets=[MockedSecret]
        )
        mock_request.side_effect = [
            MagicMock(status_code=200),  # list secret response
            MagicMock(status_code=204),  # delete secret response
        ]
        scaleway_secret.main()
        mock_request.assert_any_call(
            "DELETE",
            f"/secret-manager/v1beta1/regions/{scaleway_config_profile.default_region}/secrets/{self.test_uuid}",
        )


@patch.object(basic.AnsibleModule, "exit_json", MagicMock())
class TestScalewaySecretVersion:
    test_uuid = str(uuid.uuid4())

    @pytest.mark.parametrize(
        "set_module_args",
        [
            {
                "secret_id": test_uuid,
                "data": "test_data",
            }
        ],
        indirect=True,
    )
    @patch.object(secret_api, "unmarshal_SecretVersion")
    @patch.object(secret_api.SecretV1Beta1API, "_request")
    def test_create(
        self,
        mock_request,
        mock_unmarshal_secret_version,
        scaleway_config_profile,
        set_module_args,
    ):
        mock_unmarshal_secret_version.return_value = MagicMock()
        mock_request.side_effect = [
            MagicMock(status_code=200, id=self.test_uuid, name="test_secret"),
            MagicMock(status_code=201),
        ]

        scaleway_secret_version.main()
        mock_request.assert_called_once_with(
            "POST",
            f"/secret-manager/v1beta1/regions/{scaleway_config_profile.default_region}/secrets/{self.test_uuid}/versions",
            body={
                "data": "dGVzdF9kYXRh",
            },
        )

    @pytest.mark.parametrize(
        "set_module_args",
        [
            {
                "secret_name": "test_secret",
                "data": "test_data",
            }
        ],
        indirect=True,
    )
    @patch.object(secret_api, "unmarshal_SecretVersion")
    @patch.object(secret_api.SecretV1Beta1API, "_request")
    @patch.object(secret_api.SecretV1Beta1API, "list_secrets")
    def test_create_with_name(
        self,
        mock_list_secrets,
        mock_request,
        mock_unmarshal_secret_version,
        scaleway_config_profile,
        set_module_args,
    ):
        class MockedSecret(MagicMock):
            id = self.test_uuid
            name = "test_secret"

            def __dict__(self):
                pass

        mock_list_secrets.return_value = MagicMock(secrets=[MockedSecret])
        mock_unmarshal_secret_version.return_value = MagicMock()
        mock_request.return_value = MagicMock(status_code=201)
        scaleway_secret_version.main()
        mock_request.assert_called_once_with(
            "POST",
            f"/secret-manager/v1beta1/regions/{scaleway_config_profile.default_region}/secrets/{self.test_uuid}/versions",
            body={
                "data": "dGVzdF9kYXRh",
            },
        )

    @pytest.mark.parametrize(
        "set_module_args",
        [
            {
                "secret_name": "test_secret",
                "state": "absent",
                "revision": "latest",
            }
        ],
        indirect=True,
    )
    @patch.object(secret_api, "unmarshal_ListSecretsResponse")
    @patch.object(secret_api.SecretV1Beta1API, "_request")
    def test_delete_secret_version(
        self,
        mock_request,
        mock_unmarshal_list_secrets_response,
        scaleway_config_profile,
        set_module_args,
    ):
        class MockedSecret(MagicMock):
            id = self.test_uuid
            name = "test_secret"

            def __dict__(self):
                pass

        mock_unmarshal_list_secrets_response.return_value = MagicMock(
            secrets=[MockedSecret]
        )
        mock_request.side_effect = [
            MagicMock(status_code=200),  # list secret response
            MagicMock(status_code=204),  # delete secret response
        ]
        scaleway_secret_version.main()
        mock_request.assert_any_call(
            "DELETE",
            f"/secret-manager/v1beta1/regions/{scaleway_config_profile.default_region}/secrets/{self.test_uuid}/versions/latest",
        )
