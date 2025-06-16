# Scaleway Community Collection

This collection contains modules and plugins for Ansible to automate the management of Scaleway infrastructure and services.

## Reach us

You can contact us on our [Slack community](https://slack.scaleway.com/).

## Inventory

* `scaleway.scaleway.scaleway`: dynamic inventory plugin for Scaleway's Instances, Elastic Metal and Apple Sillicon

**Usage example:**

**scw.yml**

```yaml
plugin: scaleway.scaleway.scaleway
profile: base-profile # your scaleway credentials profile
hostnames:
  - hostname
  - id
```

`ansible-inventory -i scw.yml --list` will list all the hosts from the dynamic inventory.


## Authentication and Environment variables

Authentication is handled with the `SCW_PROFILE` or the `SCW_ACCESS_KEY` and `SCW_SECRET_KEY` environment variables.

Please check this [documentation](https://www.scaleway.com/en/docs/scaleway-sdk/reference-content/scaleway-configuration-file/) for detailed instructions on how to configure your Scaleway credentials.

## Installing the collection

### Locally

You can clone this repository and install the collection locally with `ansible-galaxy collection install .`

### Galaxy

```sh
ansible-galaxy collection install scaleway.scaleway
```

You can also include it in a requirements.yml file and install it via `ansible-galaxy collection install -r requirements.yml`, using the format:

```yaml
---
collections:
  - name: scaleway.scaleway
```
Note that the python module dependencies are not installed by `ansible-galaxy`.
They can be manually installed using pip:

```sh
pip install -r requirements-scaleway.txt
```

Note that if you install the collection from Ansible Galaxy, it will not be upgraded automatically if you upgrade the Ansible package. To upgrade the collection to the latest available version, run the following command:

```sh
ansible-galaxy collection install scaleway.scaleway --upgrade
```

You can also install a specific version of the collection, for example, if you need to downgrade when something is broken in the latest version (please report an issue in this repository). Use the following syntax:

```sh
ansible-galaxy collection install scaleway.scaleway:==1.0.0
```


## Useful links

* [Scaleway](https://www.scaleway.com/)
* [Scaleway Developers Website](https://developers.scaleway.com/)
* [Ansible Documentation](https://docs.ansible.com/ansible/latest/index.html)
* [Ansible Code of Conduct](https://docs.ansible.com/ansible/latest/community/code_of_conduct.html)

## Licensing

GNU General Public License v3.0 or later.

See [LICENSE](https://www.gnu.org/licenses/gpl-3.0.txt) to see the full text.
