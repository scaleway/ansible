from __future__ import absolute_import, division, print_function

try:
    from scaleway.secret.v1beta1.api import SecretV1Beta1API
except ImportError:
    HAS_SCALEWAY_SDK = False

__metaclass__ = type


def get_secret_id(api: "SecretV1Beta1API", params: dict) -> str:
    """
    Get a secret id from a secret name or directly from the params dict
    Remove the secret_name from the params dict if any
    """
    secret_name = params.pop("secret_name", None)

    if params.get("secret_id") is None:
        secret = api.list_secrets(name=secret_name, scheduled_for_deletion=False)
        if len(secret.secrets) == 0:
            raise Exception(f"Secret with name {secret_name} was not found")

        return secret.secrets[0].id

    return params.get("secret_id")
