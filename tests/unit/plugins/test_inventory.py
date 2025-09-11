from ....plugins.inventory import scaleway as scaleway_inventory
from ....plugins.inventory.scaleway import _Filters

from unittest.mock import patch
from scaleway.baremetal.v1.api import BaremetalV1API
from scaleway import Client


class TestInventory:
    @patch.object(BaremetalV1API, "list_servers_all")
    @patch.object(scaleway_inventory.InventoryModule, "_get_client")
    def test_get_elastic_metal(
        self,
        mocked_get_client,
        mocked_list_server_all,
        list_bare_metals,
        scaleway_config_profile,
    ):
        mocked_list_server_all.return_value = list_bare_metals
        inventory = scaleway_inventory.InventoryModule()
        mocked_client = Client.from_profile(scaleway_config_profile)

        instances = inventory._get_elastic_metal(
            mocked_client, _Filters(zones=["fr-par"])
        )
        mocked_list_server_all.assert_called_once_with(zone="fr-par", tags=None)
        assert len(instances) == 2
        assert instances[0].public_ipv4 == ["1.1.1.1", "192.168.0.1"]
        assert instances[0].public_ipv6 == []
        assert instances[1].public_ipv4 == ["1.1.1.1"]
        assert instances[1].public_ipv6 == ["2001:db8::1"]

    def test_get_host_groups(self):
        inventory = scaleway_inventory.InventoryModule()
        host = scaleway_inventory._Host(
            id="123",
            tags=["tag1", "tag2", "some-tag", " white spaced-tag "],
            zone="fr-par",
            state="running",
            hostname="test",
        )
        groups = inventory.get_host_groups(host)
        assert groups == {"tag1", "tag2", "fr_par", "some_tag", "white_spaced_tag"}
