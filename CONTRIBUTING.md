# Contributing to Scaleway Ansible Collection

Thank you for contributing to the Scaleway Ansible Collection! This guide will help you set up your development environment and run tests properly.

## Repository Structure

The repository must be placed in the correct path for Ansible to recognize it:
```
ansible_collections/scaleway/scaleway/
```

## Environment Setup

### Virtual Environment
Always use a virtual environment when working on this project:
```bash
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
```

### Dependencies
Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Testing

### Integration Tests
Run integration tests with:
```bash
ansible-test integration scaleway_secret --requirements
```

**Note**: `ansible-test` does not read environment variables. For local testing with specific profiles, use `ansible-playbook` directly:
```bash
SCW_PROFILE=owner SCW_DEFAULT_REGION=fr-par SCW_CONFIG_PATH="/path/to/config.yml" ansible-playbook playbook.yaml
```

### Unit Tests
Run unit tests with:
```bash
ansible-test units --python-interpreter .venv/bin/python
```

**MacOS Users**: You may need to set this environment variable:
```bash
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```

**Important**: `ansible-test sanity` ignores the Python path argument, which is why you'll see import checks like:
```python
try:
    import scaleway
except ImportError:
    # handle import error
```

To test quickly your changes without writing a test you can export the collection path `export ANSIBLE_COLLECTIONS_PATH=/Users/gnoale/git/scaleway/ansible_collections`

## Development Guidelines

### Python Compatibility
- Be mindful of Python versions and dependencies
- The target system receives module code and is subject to your declared dependencies

### Type Hints
When using types from the Scaleway SDK in function signatures, wrap them in quotes to avoid import issues during validation:
```python
def example_function(client: "Client") -> str:
    pass
```


## Running Playbooks

Example playbook execution:
```yaml
---
- hosts: localhost
  tasks:
    - name: Create a secret
      scaleway.scaleway.scaleway_secret:
        name: "test-secret"
        protected: false
        state: present
      vars:
        ansible_python_interpreter: .venv/bin/python
```

Execute with:
```bash
SCW_PROFILE=owner SCW_DEFAULT_REGION=fr-par SCW_CONFIG_PATH="/path/to/config.yml" ansible-playbook playbook.yaml
```
