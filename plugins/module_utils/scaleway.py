# -*- coding: utf-8 -*-
# Copyright (c) Ansible Project
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

from typing import Any, Dict

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule, env_fallback, missing_required_lib

try:
    from scaleway import Client

    from scaleway_core.profile.env import (
        ENV_KEY_SCW_ACCESS_KEY,
        ENV_KEY_SCW_API_URL,
        ENV_KEY_SCW_CONFIG_PATH,
        ENV_KEY_SCW_SECRET_KEY,
    )

    HAS_SCALEWAY_SDK = True
except ImportError:
    HAS_SCALEWAY_SDK = False

    ENV_KEY_SCW_CONFIG_PATH = "SCW_CONFIG_PATH"
    ENV_KEY_SCW_ACCESS_KEY = "SCW_ACCESS_KEY"
    ENV_KEY_SCW_SECRET_KEY = "SCW_SECRET_KEY"  # nosec B105
    ENV_KEY_SCW_API_URL = "SCW_API_URL"


def scaleway_argument_spec() -> Dict[str, Dict[str, Any]]:
    return dict(
        profile=dict(type="str", required=False),
        config_file=dict(
            type="str",
            required=False,
            fallback=(env_fallback, [ENV_KEY_SCW_CONFIG_PATH]),
        ),
        access_key=dict(
            required=False,
            fallback=(env_fallback, [ENV_KEY_SCW_ACCESS_KEY]),
            no_log=True,
        ),
        secret_key=dict(
            required=False,
            fallback=(env_fallback, [ENV_KEY_SCW_SECRET_KEY]),
            no_log=True,
        ),
        api_url=dict(
            fallback=(env_fallback, [ENV_KEY_SCW_API_URL]),
            default="https://api.scaleway.com",
        ),
        api_allow_insecure=dict(type="bool", default=False),
        user_agent=dict(type="str", required=False),
    )


def scaleway_waitable_resource_argument_spec() -> Dict[str, Dict[str, Any]]:
    return dict(
        wait=dict(type="bool", default=True),
        wait_timeout=dict(type="int", default=300),
    )


def scaleway_get_client_from_module(module: AnsibleModule):
    if not HAS_SCALEWAY_SDK:
        module.fail_json(missing_required_lib("scaleway"))

    config_file = module.params["config_file"]
    profile = module.params["profile"]
    access_key = module.params["access_key"]
    secret_key = module.params["secret_key"]
    api_url = module.params["api_url"]
    api_allow_insecure = module.params["api_allow_insecure"]
    user_agent = module.params["user_agent"]

    if profile:
        client = Client.from_config_file(
            filepath=config_file if config_file else None,
            profile_name=profile,
        )
    else:
        client = Client()

    if access_key:
        client.access_key = access_key

    if secret_key:
        client.secret_key = secret_key

    if api_url:
        client.api_url = api_url

    if api_allow_insecure:
        client.api_allow_insecure = api_allow_insecure

    if user_agent:
        client.user_agent = user_agent

    return client


def scaleway_pop_client_params(module: AnsibleModule) -> None:
    params = [
        "config_file",
        "profile",
        "access_key",
        "secret_key",
        "api_url",
        "api_allow_insecure",
        "user_agent",
    ]

    for param in params:
        if param in module.params:
            module.params.pop(param)


def scaleway_pop_waitable_resource_params(module: AnsibleModule) -> None:
    params = [
        "wait",
        "wait_timeout",
    ]

    for param in params:
        if param in module.params:
            module.params.pop(param)
