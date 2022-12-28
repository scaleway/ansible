from ansible.plugins.inventory import BaseInventoryPlugin
from scaleway import Client
from scaleway.instance.v1 import InstanceV1API, ServerState

_ALLOWED_FILE_NAME_SUFFIXES = (
    "scaleway.yaml",
    "scaleway.yml",
    "scw.yaml",
    "scw.yml",
)


class InventoryModule(BaseInventoryPlugin):
    NAME = "community.scaleway.scaleway"

    def verify_file(self, path: str):
        if not super(InventoryModule, self).verify_file(path):
            return False

        if not path.endswith(_ALLOWED_FILE_NAME_SUFFIXES):
            self.display.vvv(
                "Skipping due to inventory source file name mismatch. "
                "The file name has to end with one of the following: "
                "scaleway.yaml, scaleway.yml, "
                "scw.yaml, scw.yml."
            )

            return False

        return True

    def parse(self, inventory, loader, path: str, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._read_config_data(path)

    def _read_config_data(self, path: str):
        client = Client.from_config_file_and_env()
        api = InstanceV1API(client)

        self.inventory.add_group("compute")
        for server in api.list_servers().servers:
            self.inventory.add_host(server.name, group="compute")

            if server.state != ServerState.RUNNING:
                self.display.warning(f"Server {server.name} is not running. Skipping.")
                continue

            if server.public_ip is None:
                self.display.warning(
                    f"Server {server.name} has no public IP address. Skipping."
                )
                continue

            self.inventory.set_variable(
                server.name, "ansible_host", server.public_ip.address
            )
