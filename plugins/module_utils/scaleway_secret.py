from __future__ import absolute_import, division, print_function

from .model import Model, Secret, SecretVersion

try:
    from scaleway.secret.v1beta1.api import SecretV1Beta1API
    from scaleway import ScalewayException
except ImportError:
    HAS_SCALEWAY_SDK = False


class SecretNotFound(Exception):
    pass


def build_secret(parameters: dict) -> Secret:
    return Secret.build_model(parameters)


def build_secret_version(parameters: dict) -> SecretVersion:
    return SecretVersion.build_model(parameters)


def get_secret(api: "SecretV1Beta1API", **kwargs) -> Secret:
    """
    Get a secret by secret_id or name
    """
    if "secret_id" in kwargs:
        secret = api.get_secret(secret_id=kwargs["secret_id"])

    elif "name" in kwargs:
        secrets = api.list_secrets(name=kwargs["name"], scheduled_for_deletion=False)

        if len(secrets.secrets) == 0:
            raise SecretNotFound(f"Secret {kwargs['name']} not found")

        secret = secrets.secrets[0]

    else:
        raise SecretNotFound("No secret_id or name provided")

    return build_secret(secret.__dict__)


def get_secret_version(api: "SecretV1Beta1API", **kwargs) -> SecretVersion:
    """
    Get a secret version by secret_id and revision
    """
    revision = kwargs.get("revision", "latest")
    secret_version = api.get_secret_version(
        secret_id=kwargs["secret_id"], revision=revision
    )

    secret_version_access = api.access_secret_version(
        secret_id=kwargs["secret_id"],
        revision=revision,
    )

    return build_secret_version(
        {**secret_version.__dict__, "data": secret_version_access.data}
    )


def update_secret(
    api: "SecretV1Beta1API", parameters: dict, check_mode: bool = False
) -> tuple[bool, Secret, Secret]:
    """
    Update a secret by checking the difference between the local and remote object

    The local object is builded from the parameters and act as the source of truth
    The remote object is retrieved from the API

    return changed, local_model, remote_model
    """
    remote_model = get_secret(api, name=parameters.get("name"))

    # build and diff source model with the api one
    local_model = build_secret(parameters)
    local_model.id = remote_model.id

    diff = local_model.diff(remote_model)
    if len(diff) == 0:
        return False, local_model, remote_model

    if check_mode:
        return False, local_model, remote_model

    updated_secret = api.update_secret(secret_id=remote_model.id, **diff)

    return True, build_secret(updated_secret.__dict__), remote_model


def is_duplicate(scw_exception: "ScalewayException") -> bool:
    """
    Inspect the content of raw Scaleway API json response to determine if the error is due to a duplicate secret
    """
    if scw_exception.status_code == 400:
        return (
            scw_exception.response.json()["details"][0]["help_message"]
            == "cannot have same secret name in same path"
        )
    return False


def build_ansible_diff(remote_model: Model, local_model: Model) -> dict:
    """
    Build an Ansible diff dictionary from a before and after model
    """
    return dict(
        before=remote_model.__dict__,
        after=local_model.__dict__,
    )
