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

## Lookup

* `scaleway.scaleway.scaleway_secret`: lookup plugin for Scaleway's Secrets

**Usage example:**

```yaml
- hosts: localhost

  vars:
    secret_versions: "{{ lookup('scaleway.scaleway.scaleway_secret', 'secret-epic-lumiere', 'test') }}"

  tasks:
    - name: Debug secret versions
      ansible.builtin.debug:
        msg: "{{ secret_versions | split(',') | map('b64decode') }}"
```

will print the secret's secret data as a list:

```shell
ok: [localhost] => {
    "msg": [
        "test",
        "abcd"
    ]
}
```

## Domains and DNS

The DNS modules correspond to the Domains and DNS resources, data sources, and list resources in the Scaleway Terraform provider:

| Terraform object | Ansible modules |
| --- | --- |
| `scaleway_domain_record` | `scaleway_dns_record`, `scaleway_dns_record_info`, `scaleway_dns_records_info` |
| `scaleway_domain_zone` | `scaleway_dns_zone`, `scaleway_dns_zone_info`, `scaleway_dns_zones_info` |
| `scaleway_domain_registration` | `scaleway_domain_registration`, `scaleway_domain_registration_info` |

`scaleway_dns_record` manages **one record** and supports Geo IP, HTTP service, view, and weighted configurations. Use `record_id` (or `match_data`, the old value) when changing a record's value. The older `scaleway_dns_record_set` manages the **entire set** of records sharing a name and type, so its desired list must include every member that should remain.

Domain registration purchases incur charges and require `confirm_purchase: true`. With `state: absent`, the registration module disables automatic renewal; it does not cancel ownership. DNS zone deletion removes the zone's records. Each module's options and examples are available through `ansible-doc scaleway.scaleway.<module_name>`.


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
