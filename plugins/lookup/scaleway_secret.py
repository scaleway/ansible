# -*- coding: utf-8 -*-
# Copyright: (c) 2025, Scaleway
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
name: scaleway_secret
author:
  - Guillaume Noale (@gnoale) <gnoale@scaleway.com>
short_description: Look up Scaleway secrets
description:
  - Look up Scaleway secret version data
options:
  _terms:
    description: The secret id or name for which to get the value(s).
    type: list
    elements: str
    required: true
  revision:
    description: The revision of the secret version to get the value(s).
    type: str
    default: latest
  attribute:
    description: The attribute of the secret version to get the value(s).
    choices:
      - data
      - description
      - revision
      - secret_id
"""

import uuid

from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError
from ..module_utils.scaleway import build_scaleway_client
from ..module_utils.scaleway_secret import get_secret_version, get_secret

HAS_SCALEWAY = True
try:
    from scaleway.secret.v1beta1.api import SecretV1Beta1API
    from scaleway import ScalewayException
except ImportError:
    HAS_SCALEWAY = False


def is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


class LookupModule(LookupBase):
    def run(self, terms, variables, **kwargs):
        if not HAS_SCALEWAY:
            raise AnsibleError("Scaleway SDK is not installed")

        self.set_options(var_options=variables, direct=kwargs)

        attribute = kwargs.get("attribute")

        client = build_scaleway_client()
        api = SecretV1Beta1API(client)

        results = []

        for term in terms:
            arguments = {"revision": kwargs.get("revision", "latest")}

            if is_uuid(term):
                arguments["secret_id"] = term
            else:
                try:
                    secret = get_secret(api, name=term)
                    arguments["secret_id"] = secret.id
                except ScalewayException as scw_exception:
                    raise AnsibleError(scw_exception)

            try:
                secret_version = get_secret_version(api, **arguments)
            except ScalewayException as scw_exception:
                raise AnsibleError(scw_exception)

            if attribute is not None:
                results.append(getattr(secret_version, attribute))
            else:
                results.append(secret_version.data)

        return results
