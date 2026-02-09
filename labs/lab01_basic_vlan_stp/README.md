# Lab 01: Basic Connectivity, VLANs, and STP

## Purpose
The goal of this lab is to establish basic Layer 2 connectivity between the switches, configure VLANs, and observe Spanning Tree Protocol (STP) behavior. This forms the foundation for more advanced routing labs.

## Study Points
*   VLAN (Virtual LAN) creation and assignment.
*   802.1Q Trunking configuration.
*   VTP (VLAN Trunking Protocol) modes (Server/Client/Transparent).
*   STP (Spanning Tree Protocol) root bridge election and port states.
*   CDP/LLDP neighbor discovery.

## Topology
*   **Switches**: Use all 4 switches (3560CX, 2960CX, 2x 2960S).
*   **Connections**: Ensure trunk links are established between all switches (full mesh or ring if cabling permits, otherwise daisy chain).

## Configuration Steps

### 1. VLAN Cleanup (Pre-lab)
*   Ensure all previous non-management VLANs are removed.
*   Ensure VTP revision number is lower or reset (change domain name to reset).

### 2. VTP Configuration
*   Configure VTP Domain: `CCNA`
*   Configure 3560CX as VTP Server.
*   Configure others as VTP Clients.

### 3. VLAN Creation
*   On the VTP Server, create:
    *   VLAN 10: Name `Sales`
    *   VLAN 20: Name `Engineering`
    *   VLAN 99: Name `Management` (Should already exist)

### 4. Port Assignment
*   Assign `Sales` to ports 1-5 on 2960S switches.
*   Assign `Engineering` to ports 6-10 on 2960S switches.
*   Configure Uplink ports as 802.1Q Trunks.

### 5. STP Optimization
*   Configure 3560CX as the **Root Bridge** for VLAN 10 and 20 (`spanning-tree vlan 10,20 root primary`).
*   Configure 2960CX as the **Secondary Root** (`spanning-tree vlan 10,20 root secondary`).

## Validation
1.  **Check VLANs**: `show vlan brief` (Verify 10, 20 exist on all Client switches).
2.  **Check Trunks**: `show interfaces trunk` (Verify allowed VLANs and native VLAN).
3.  **Check STP**: `show spanning-tree vlan 10` (Verify 3560CX is "This bridge is the root").
4.  **Connectivity**: Ping between SVIs (if created) or hosts in the same VLAN.

## Troubleshooting
*   **VLANs not syncing**: Check VTP domain name (case sensitive), password, and trunk mode.
*   **STP weirdness**: Check for Etherchannel misconfigurations or mismatching native VLANs.

## Cleanup
Run the `restore_ssh.py` script to reset devices to the base management configuration.
