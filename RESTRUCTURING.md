# Network Automation Repository Restructuring Plan

## Goal
Transform the flat script-based repository into a modular, scalable automation framework.

## Current vs Proposed Structure

### Current Structure (Flat)
```text
ccnastudy/
├── scripts/
│   ├── inventory.py       (Mixed Data & Logic)
│   ├── monitor_stp.py     (Hardcoded imports)
│   ├── restore_ssh.py     (Monolithic script)
│   └── ...
├── ansible/
│   └── playbooks/         (Scattered YAML)
└── ssh_config_for_lab     (Root Config)
```

### Proposed Modular Structure
```text
ccnastudy/
├── flake.nix               # Environment Definition
├── inventory/              # Single Source of Truth
│   ├── hosts.yml           # Ansible Inventory
│   └── devices.py          # Python Inventory (Loadable Module)
├── lib/                    # Shared Python Library
│   └── netauto/
│       ├── __init__.py
│       ├── connection.py   # SSH/Netmiko wrappers
│       └── utils.py        # Helpers (STP parsing, etc.)
├── bin/                    # Executable Entry Points
│   ├── monitor-stp         # Wrapper around lib
│   └── restore-lab         # Wrapper around lib
├── playbooks/              # Organized Ansible
│   ├── site.yml            # Main playbook
│   ├── roles/              # Reusable roles
│   └── setup_lab.yml       # Specific tasks
└── labs/                   # Documentation remains here
```

## Migration Steps

1.  **Environment**: Activate Nix shell (`nix develop`).
2.  **Inventory**:
    *   Create `inventory/hosts.yml` (Ansible format).
    *   Refactor `scripts/inventory.py` to `inventory/devices.py`.
3.  **Library Extraction**:
    *   Create `lib/netauto/`.
    *   Move connection logic from `monitor_stp.py` to `lib/netauto/connection.py`.
    *   Move cleanup logic from `restore_ssh.py` to `lib/netauto/tasks.py`.
4.  **Scripts Update**:
    *   Update scripts to import from `lib.netauto` and `inventory`.
    *   Move scripts to `bin/` (or keep in `scripts/` but cleaner).
5.  **Ansible Organization**:
    *   Move playbooks to `playbooks/` root or categorized subdirs.

## Benefits
*   **Decoupling**: Config is separate from Code.
*   **Reusability**: Core logic can be used by both Python scripts and custom Ansible modules.
*   **Maintainability**: Easier to test individual components in `lib/`.
