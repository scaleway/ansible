# Scaleway Community Collection

This collection contains modules and plugins for Ansible to automate the management of Scaleway infrastructure and services.

## Reach us

You can contact us on our [Slack community](https://slack.scaleway.com/).

## Included content

* **Inventory**
  * quantumsheep.scaleway.scaleway: dynamic inventory plugin for Scaleway's Instances, Elastic Metal and Apple Sillicon

## Using this collection

### Installing the collection

Before using the Scaleway collection, you need to install it with the Ansible Galaxy CLI.

```sh
ansible-galaxy collection install quantumsheep.scaleway
```

You can also include it in a requirements.yml file and install it via `ansible-galaxy collection install -r requirements.yml`, using the format:

```yal
---
collections:
  - name: quantumsheep.scaleway
```

Note that if you install the collection from Ansible Galaxy, it will not be upgraded automatically if you upgrade the Ansible package. To upgrade the collection to the latest available version, run the following command:

```sh
ansible-galaxy collection install quantumsheep.scaleway --upgrade
```

You can also install a specific version of the collection, for example, if you need to downgrade when something is broken in the latest version (please report an issue in this repository). Use the following syntax:

```sh
ansible-galaxy collection install quantumsheep.scaleway:==1.0.0
```

## Useful links

* [Scaleway](https://www.scaleway.com/)
* [Scaleway Developers Website](https://developers.scaleway.com/)
* [Ansible Documentation](https://docs.ansible.com/ansible/latest/index.html)
* [Ansible Code of Conduct](https://docs.ansible.com/ansible/latest/community/code_of_conduct.html)

## Licensing

GNU General Public License v3.0 or later.

See [LICENSE](https://www.gnu.org/licenses/gpl-3.0.txt) to see the full text.
