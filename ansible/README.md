# Ansible for CCNA Lab

This directory contains Ansible playbooks and inventory for managing your Cisco lab devices.

## Prerequisites

1. **Install Ansible** (in your virtual environment):
   ```bash
   source ../.venv/bin/activate
   uv pip install -r requirements.txt
   ```

2. **Install Cisco IOS Collection**:
   ```bash
   ansible-galaxy collection install cisco.ios
   ```

## Directory Structure

```
ansible/
├── ansible.cfg           # Ansible configuration
├── inventory/
│   └── hosts.ini        # Device inventory
├── playbooks/
│   ├── test_connectivity.yml      # Test SSH access
│   ├── backup_configs.yml         # Backup all configs
│   ├── restore_base_config.yml    # Restore to base state
│   └── lab01_vlan_stp.yml         # Lab 01 configuration
└── backups/             # Configuration backups (auto-created)
```

## Usage Examples

All commands should be run from the `ansible/` directory:
```bash
cd ansible
```

### 1. Test Connectivity
```bash
ansible-playbook playbooks/test_connectivity.yml
```

### 2. Backup Current Configurations
```bash
ansible-playbook playbooks/backup_configs.yml
```

### 3. Restore Base Configuration
```bash
ansible-playbook playbooks/restore_base_config.yml
```

### 4. Deploy Lab 01 Configuration
```bash
ansible-playbook playbooks/lab01_vlan_stp.yml
```

### 5. Run Ad-Hoc Commands
```bash
# Show version on all devices
ansible all -m cisco.ios.ios_command -a "commands='show version'"

# Show VLAN brief on switches
ansible switches -m cisco.ios.ios_command -a "commands='show vlan brief'"

# Show running config on router
ansible routers -m cisco.ios.ios_command -a "commands='show running-config'"
```

## Authentication

The inventory is configured to use SSH key authentication by default (`~/.ssh/id_ed25519`).

To use password authentication instead:
1. Edit `inventory/hosts.ini`
2. Comment out the `ansible_ssh_private_key_file` line
3. Uncomment the `ansible_password` and `ansible_become_password` lines
4. Set your password

## Tips

- Use `--check` for dry-run: `ansible-playbook playbooks/lab01_vlan_stp.yml --check`
- Run on specific hosts: `ansible-playbook playbooks/test_connectivity.yml --limit switch3560cx`
- Increase verbosity: `ansible-playbook playbooks/test_connectivity.yml -vvv`
