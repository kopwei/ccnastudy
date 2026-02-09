# Network Architecture

This document describes the home lab setup for CCNA/CCNP study.

## Topology Diagram

```mermaid
graph TD
    UserPC[User PC / Router (192.168.2.0/24)] --> Netgear[Netgear 108Tv2 (Management Switch)]
    
    subgraph Management_Network
        Netgear
    end

    Netgear -- FE0 (192.168.2.11) --> Router[Cisco 891 Router]
    Netgear -- Ge10 (192.168.2.35, VLAN 99) --> Switch1[Cisco 3560CX Switch]
    Netgear -- Ge10 (192.168.2.29, VLAN 99) --> Switch2[Cisco 2960CX Switch]
    Netgear -- FE0 (192.168.2.21) --> Switch3[Cisco 2960S Switch 1]
    Netgear -- FE0 (192.168.2.22) --> Switch4[Cisco 2960S Switch 2]

    style Netgear fill:#f9f,stroke:#333,stroke-width:2px
    style Router fill:#ff9,stroke:#333,stroke-width:2px
    style Switch1 fill:#9cf,stroke:#333,stroke-width:2px
    style Switch2 fill:#9cf,stroke:#333,stroke-width:2px
    style Switch3 fill:#9cf,stroke:#333,stroke-width:2px
    style Switch4 fill:#9cf,stroke:#333,stroke-width:2px
```

## Device Inventory & IP Allocation

All devices are connected to the management network (192.168.2.0/24).
IP addresses are reserved via DHCP MAC binding on the main router.

| Device Name | Model | Management Port | IP Address | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Mgmt Switch** | Netgear 108Tv2 | - | *Active* | Connects all management ports |
| **Router** | Cisco 891 | FE0 | `192.168.2.11` | Gateway/Router |
| **Switch 1** | Cisco 3560CX | Ge10 | `192.168.2.35` | VLAN 99 Mgmt |
| **Switch 2** | Cisco 2960CX | Ge10 | `192.168.2.29` | VLAN 99 Mgmt |
| **Switch 3** | Cisco 2960S | FastEthernet 0 | `192.168.2.21` | 24 Ports |
| **Switch 4** | Cisco 2960S | FastEthernet 0 | `192.168.2.22` | 24 Ports |

## Connectivity Details

*   **Management Network**: 192.168.2.0/24
*   **SSH Access**: Enabled on all devices with a unified admin user/password.
*   **Method**:
    *   **Router & 2960S**: Connect via dedicated management port (FE0).
    *   **3560CX & 2960CX**: Connect via Ge10 port assigned to VLAN 99.

## Automation Constraints

*   Scripts utilize `netmiko` for SSH and `pyserial` for console access.
*   "Restore" scripts revert devices to a state where Management IP + SSH are accessible.
