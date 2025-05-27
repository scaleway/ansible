import tempfile
import os
import yaml
import pytest
import uuid
import json
from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes
from scaleway_core.profile import Profile

from scaleway.baremetal.v1.types import Server, IP, IPVersion, IPReverseStatus


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


@pytest.fixture(name="list_bare_metals")
def list_bare_metals_fixture():
    return [
        Server(
            id="bmc-12345678-1234-1234-1234-123456789012",
            organization_id="org-12345678-1234-1234-1234-123456789012",
            project_id="project-12345678-1234-1234-1234-123456789012",
            name="test-bare-metal",
            description="A test bare metal server",
            status="running",
            updated_at="2023-10-01T12:00:00Z",
            created_at="2023-10-01T10:00:00Z",
            offer_id="bmc-2xlarge",
            offer_name="bmc-2xlarge",
            tags=["prod", "platform2"],
            boot_type="local",
            zone="fr-par-1",
            ping_status="ping_running",
            domain="test.example.com",
            options=[],
            install=None,
            rescue_server=None,
            ips=[
                IP(
                    address="1.1.1.1",
                    reverse="test.example.com",
                    id="ip-12345678-1234-1234-1234-123456789012",
                    version=IPVersion.I_PV4,
                    reverse_status=IPReverseStatus.ACTIVE,
                    reverse_status_message="",
                ),
                IP(
                    address="192.168.0.1",
                    version=IPVersion.I_PV4,
                    reverse="test.internal",
                    id="ip-12345678-1234-1234-1234-123456789012",
                    reverse_status=IPReverseStatus.ACTIVE,
                    reverse_status_message="",
                ),
            ],
        ),
        Server(
            id="bmc-12345678-1234-1234-1234-123456789012",
            organization_id="org-12345678-1234-1234-1234-123456789012",
            project_id="project-12345678-1234-1234-1234-123456789012",
            name="test-bare-metal",
            description="A test bare metal server",
            status="stopped",
            updated_at="2023-10-01T12:00:00Z",
            created_at="2023-10-01T10:00:00Z",
            offer_id="bmc-2xlarge",
            offer_name="bmc-2xlarge",
            tags=["dev", "platform1"],
            boot_type="local",
            zone="fr-par-1",
            ping_status="ping_running",
            domain="test.example.com",
            options=[],
            install=None,
            rescue_server=None,
            ips=[
                IP(
                    address="1.1.1.1",
                    reverse="test.example.com",
                    id="ip-12345678-1234-1234-1234-123456789012",
                    version=IPVersion.I_PV4,
                    reverse_status=IPReverseStatus.ACTIVE,
                    reverse_status_message="",
                ),
                IP(
                    address="2001:db8::1",
                    version=IPVersion.I_PV6,
                    reverse="test.internal",
                    id="ip-12345678-1234-1234-1234-123456789012",
                    reverse_status=IPReverseStatus.ACTIVE,
                    reverse_status_message="",
                ),
            ],
        ),
    ]
