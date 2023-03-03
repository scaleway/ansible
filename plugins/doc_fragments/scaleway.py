# -*- coding: utf-8 -*-

# Copyright: (c), Ansible Project
# Copyright: (c), Nathanael Demacon (@quantumsheep)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment(object):
    # Standard documentation fragment
    DOCUMENTATION = r"""
options:
  profile:
    description:
      - The Scaleway profile to load. Leave empty to disable.
    type: str
    required: false
  config_file:
    description:
      - Path to the Scaleway configuration file. Leave empty to use the default path.
    type: str
    required: false
  access_key:
    description:
      - Scaleway API access key.
    type: str
    required: false
  secret_key:
    description:
      - Scaleway API secret key.
    type: str
    required: false
  api_url:
    description:
      - Scaleway API URL.
    type: str
    default: https://api.scaleway.com
  api_allow_insecure:
    description:
      - Allow insecure connection to Scaleway API.
    type: bool
    default: false
  user_agent:
    description:
      - User agent used by the Scaleway API client.
    type: str
"""
