# CCNA/CCNP Study Labs

This repository contains documentation, lab scenarios, and automation scripts for managing a Cisco Home Lab environment.

## Project Structure

*   **`docs/`**: Network architecture diagrams and IP allocation tables.
    *   [Network Architecture](docs/architecture.md)
*   **`labs/`**: Study labs and configurations.
    *   [Lab 01: Basic VLAN & STP](labs/lab01_basic_vlan_stp/README.md)
*   **`scripts/`**: Automation tools for resetting and configuring devices.

## Automation Scripts

The `scripts/` directory contains tools to help reset the lab environment to a clean state.

### Prerequisites

Install the required Python libraries:
```bash
pip install -r scripts/requirements.txt
```

### 1. Network Restore (`restore_ssh.py`)
Use this script when devices are accessible via the management network (SSH). It reverts devices to a base configuration.

**Usage:**
```bash
python3 scripts/restore_ssh.py
```
*Note: You may need to update `scripts/inventory.py` with your current credentials if they differ from the defaults.*

### 2. Serial Console Restore (`restore_serial.py`)
Use this script if you are locked out of a device. Connect your console cable and use this interactive tool to push a base configuration line-by-line.

**Usage:**
```bash
python3 scripts/restore_serial.py
```
Follow the on-screen prompts to select the device and serial port.

## Lab Workflow
1.  Read the lab objectives in `labs/`.
2.  Configure your devices according to the lab instructions.
3.  Upon completion, run `scripts/restore_ssh.py` to reset the environment for the next study session.
