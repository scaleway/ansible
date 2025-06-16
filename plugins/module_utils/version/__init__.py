import os
import sys

HAS_YAML = False
try:
    import yaml

    HAS_YAML = True
except ImportError:
    pass

__version__: str = "integration"

# Try to find galaxy.yml in different possible locations
possible_paths = [
    # Development environment
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "galaxy.yml"),
    # Runtime environment (when installed as collection)
    os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "..", "..", "..", "galaxy.yml"
    ),
    # Fallback to current directory
    "galaxy.yml",
]

for path in possible_paths:
    if os.path.isfile(path) and HAS_YAML:
        try:
            with open(path, "r") as file:
                config = yaml.safe_load(file)
                __version__ = config.get("version", "integration")
                break
        except yaml.YAMLError:
            continue
