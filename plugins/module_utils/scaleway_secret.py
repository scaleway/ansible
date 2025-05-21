from __future__ import absolute_import, division, print_function

from dataclasses import dataclass, field

from .model import model_diff

try:
    from scaleway.secret.v1beta1.api import SecretV1Beta1API
    from scaleway import ScalewayException
except ImportError:
    HAS_SCALEWAY_SDK = False

__metaclass__ = type


class SecretNotFound(Exception):
    pass


@dataclass
class Secret:
    """
    Model a Secret object with fields we support mutability for
    Excepted id and name which act as primary keys
    """

    name: str
    id: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)


def build_secret(parameters: dict) -> Secret:
    secret = Secret(name=parameters.get("name"))

    for k, v in parameters.items():
        if k in Secret.__dataclass_fields__:
            setattr(secret, k, v)

    return secret


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


def update_secret(
    api: "SecretV1Beta1API", parameters: dict, check_mode: bool = False
) -> tuple[bool, Secret, Secret]:
    """
    Update a secret by checking the difference between the source and destination object

    The source object is builded from the parameters and act as the source of truth
    The destination object is the object retrieved from the API

    If the diff is empty, return the destination object
    If the diff is not empty, try to update the secret with the updated values and return the source object for ansible to display the diff

    return changed, updated_model, current_model
    """
    destination_model = get_secret(api, name=parameters.get("name"))

    # build and diff source model with the api one
    source_model = build_secret(parameters)
    source_model.id = destination_model.id

    diff = model_diff(source_model, destination_model)
    if len(diff) == 0:
        return False, source_model, destination_model

    if check_mode:
        return False, source_model, destination_model

    updated_secret = api.update_secret(secret_id=destination_model.id, **diff)

    return True, build_secret(updated_secret.__dict__), destination_model


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


def build_diff(before_model: Secret, after_args: dict) -> dict:
    """
    Build an Ansible diff dictionary from a before and after model
    """
    after = build_secret(after_args)
    after.id = before_model.id
    return dict(
        before=before_model.__dict__,
        after=after.__dict__,
    )
