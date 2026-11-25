import pytest
from unittest.mock import MagicMock
from ....plugins.module_utils.scaleway_secret import (
    get_secret,
    update_secret,
    SecretNotFound,
)


class TestScalewaySecretUtils:
    """Test the utility functions in scaleway_secret.py"""

    def test_get_secret_by_name_with_path(self):
        """Test getting a secret by name with a specific path"""
        mock_api = MagicMock()

        mock_secret = MagicMock()
        mock_secret.name = "test_secret"
        mock_secret.path = "/custom/path"
        mock_secret.id = "secret-id-123"
        mock_secret.description = "test description"

        mock_list_response = MagicMock()
        mock_list_response.secrets = [mock_secret]

        mock_api.list_secrets.return_value = mock_list_response

        result = get_secret(mock_api, name="test_secret", path="/custom/path")

        mock_api.list_secrets.assert_called_once_with(
            name="test_secret", scheduled_for_deletion=False, path="/custom/path"
        )

        assert result.name == "test_secret"
        assert result.path == "/custom/path"
        assert result.id == "secret-id-123"

    def test_get_secret_by_name_with_path_not_found(self):
        """Test getting a secret by name with path when secret doesn't exist"""
        mock_api = MagicMock()

        mock_list_response = MagicMock()
        mock_list_response.secrets = []

        mock_api.list_secrets.return_value = mock_list_response

        with pytest.raises(SecretNotFound) as exc_info:
            get_secret(mock_api, name="test_secret", path="/custom/path")

        assert "Secret test_secret not found at path /custom/path" in str(
            exc_info.value
        )

    def test_get_secret_by_name_without_path_not_found(self):
        """Test getting a secret by name without path when secret doesn't exist"""
        mock_api = MagicMock()

        mock_list_response = MagicMock()
        mock_list_response.secrets = []

        mock_api.list_secrets.return_value = mock_list_response

        with pytest.raises(SecretNotFound) as exc_info:
            get_secret(mock_api, name="test_secret")

        assert "Secret test_secret not found" in str(exc_info.value)

    def test_update_secret_with_path(self):
        """Test updating a secret with path parameter"""
        mock_api = MagicMock()

        existing_secret = MagicMock()
        existing_secret.name = "test_secret"
        existing_secret.path = "/custom/path"
        existing_secret.id = "secret-id-123"
        existing_secret.description = "old description"
        existing_secret.tags = ["old-tag"]

        mock_list_response = MagicMock()
        mock_list_response.secrets = [existing_secret]

        updated_secret = MagicMock()
        updated_secret.name = "test_secret"
        updated_secret.path = "/custom/path"
        updated_secret.id = "secret-id-123"
        updated_secret.description = "new description"
        updated_secret.tags = ["new-tag"]

        mock_api.list_secrets.return_value = mock_list_response
        mock_api.update_secret.return_value = updated_secret

        parameters = {
            "name": "test_secret",
            "path": "/custom/path",
            "description": "new description",
            "tags": ["new-tag"],
        }

        changed, local_model, remote_model = update_secret(mock_api, parameters)

        mock_api.list_secrets.assert_called_once_with(
            name="test_secret", scheduled_for_deletion=False, path="/custom/path"
        )

        mock_api.update_secret.assert_called_once()

        assert changed is True
        assert local_model.name == "test_secret"
        assert local_model.path == "/custom/path"
        assert local_model.description == "new description"

    def test_update_secret_with_path_no_changes(self):
        """Test updating a secret with path when no changes are needed"""
        mock_api = MagicMock()

        existing_secret = MagicMock()
        existing_secret.name = "test_secret"
        existing_secret.path = "/custom/path"
        existing_secret.id = "secret-id-123"
        existing_secret.description = "same description"
        existing_secret.tags = ["same-tag"]

        mock_list_response = MagicMock()
        mock_list_response.secrets = [existing_secret]

        mock_api.list_secrets.return_value = mock_list_response

        parameters = {
            "name": "test_secret",
            "path": "/custom/path",
            "description": "same description",
            "tags": ["same-tag"],
        }

        changed, local_model, remote_model = update_secret(mock_api, parameters)

        mock_api.list_secrets.assert_called_once_with(
            name="test_secret", scheduled_for_deletion=False, path="/custom/path"
        )

        mock_api.update_secret.assert_not_called()

        assert changed is False
        assert local_model.name == "test_secret"
        assert local_model.path == "/custom/path"

    def test_update_secret_with_path_check_mode(self):
        """Test updating a secret with path in check mode"""
        mock_api = MagicMock()

        existing_secret = MagicMock()
        existing_secret.name = "test_secret"
        existing_secret.path = "/custom/path"
        existing_secret.id = "secret-id-123"
        existing_secret.description = "old description"
        existing_secret.tags = ["old-tag"]

        mock_list_response = MagicMock()
        mock_list_response.secrets = [existing_secret]

        mock_api.list_secrets.return_value = mock_list_response

        parameters = {
            "name": "test_secret",
            "path": "/custom/path",
            "description": "new description",
            "tags": ["new-tag"],
        }

        changed, local_model, remote_model = update_secret(
            mock_api, parameters, check_mode=True
        )

        mock_api.list_secrets.assert_called_once_with(
            name="test_secret", scheduled_for_deletion=False, path="/custom/path"
        )

        mock_api.update_secret.assert_not_called()

        assert changed is False
        assert local_model.name == "test_secret"
        assert local_model.path == "/custom/path"
        assert local_model.description == "new description"

    def test_get_secret_by_id(self):
        """Test getting a secret by ID (should not use path)"""
        mock_api = MagicMock()

        mock_secret = MagicMock()
        mock_secret.name = "test_secret"
        mock_secret.path = "/some/path"
        mock_secret.id = "secret-id-123"

        mock_api.get_secret.return_value = mock_secret

        result = get_secret(mock_api, secret_id="secret-id-123")

        mock_api.get_secret.assert_called_once_with(secret_id="secret-id-123")
        mock_api.list_secrets.assert_not_called()

        assert result.name == "test_secret"
        assert result.path == "/some/path"
        assert result.id == "secret-id-123"

    def test_update_secret_path_change(self):
        """Test updating a secret's path parameter"""
        mock_api = MagicMock()

        existing_secret = MagicMock()
        existing_secret.name = "test_secret"
        existing_secret.path = "/old/path"
        existing_secret.id = "secret-id-123"
        existing_secret.description = "test description"

        mock_list_response = MagicMock()
        mock_list_response.secrets = [existing_secret]

        updated_secret = MagicMock()
        updated_secret.name = "test_secret"
        updated_secret.path = "/new/path"
        updated_secret.id = "secret-id-123"
        updated_secret.description = "test description"

        mock_api.list_secrets.return_value = mock_list_response
        mock_api.update_secret.return_value = updated_secret

        parameters = {
            "name": "test_secret",
            "path": "/new/path",
            "description": "test description",
        }

        changed, local_model, remote_model = update_secret(mock_api, parameters)

        mock_api.list_secrets.assert_called_once_with(
            name="test_secret", scheduled_for_deletion=False, path="/new/path"
        )

        mock_api.update_secret.assert_called_once()

        assert changed is True
        assert local_model.path == "/new/path"
        assert remote_model.path == "/old/path"

    def test_get_secret_path_filtering(self):
        """Test that path filtering works correctly when multiple secrets have same name"""
        mock_api = MagicMock()

        secret1 = MagicMock()
        secret1.name = "test_secret"
        secret1.path = "/path1"
        secret1.id = "secret-id-1"

        secret2 = MagicMock()
        secret2.name = "test_secret"
        secret2.path = "/path2"
        secret2.id = "secret-id-2"

        mock_list_response = MagicMock()
        mock_list_response.secrets = [secret1, secret2]

        mock_api.list_secrets.return_value = mock_list_response

        result = get_secret(mock_api, name="test_secret")
        assert result.id == "secret-id-1"

        mock_api.list_secrets.reset_mock()

        mock_list_response_filtered = MagicMock()
        mock_list_response_filtered.secrets = [secret2]
        mock_api.list_secrets.return_value = mock_list_response_filtered

        result = get_secret(mock_api, name="test_secret", path="/path2")
        assert result.id == "secret-id-2"
        mock_api.list_secrets.assert_called_once_with(
            name="test_secret", scheduled_for_deletion=False, path="/path2"
        )
