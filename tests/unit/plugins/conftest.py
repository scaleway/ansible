import tempfile
import os
import yaml
import pytest
import uuid
import json
from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes
from scaleway_core.profile import Profile


@pytest.fixture()
def set_module_args(request):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({"ANSIBLE_MODULE_ARGS": request.param})
    basic._ANSIBLE_ARGS = to_bytes(args)
    # ansible-core 2.19 require this to be set when tests run in the CI
    # this is the file I assume it needs to resolve as decoders
    # .venv/lib/python3.13/site-packages/ansible/module_utils/_internal/_json/_profiles/__pycache__/_module_modern_c2m.cpython-313.pyc
    # I couldn't reproduce the issue locally though
    try:
        basic._ANSIBLE_PROFILE = "modern"
    except AttributeError:
        pass


@pytest.fixture(name="scaleway_config_profile")
def create_temporary_scaleway_config() -> Profile:
    # Create a temporary config file with the default project id that will be attached to the client
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
        config_file = tmp.name
        sample_uuid = str(uuid.uuid4())
        yaml.dump(
            {
                "access_key": "SCWXXXXXXXXXXXXXXXXX",
                "secret_key": sample_uuid,
                "default_project_id": sample_uuid,
                "default_region": "fr-par",
                "default_organization_id": sample_uuid,
            },
            tmp,
        )

        os.environ["SCW_CONFIG_PATH"] = config_file
        return Profile.from_config_file(config_file)
