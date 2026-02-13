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
*   **Switches**: 2x 3850 (3850S1, 3850S2) and 2x 2960S (2960S-1, 2960S-2).
*   **Connections (Ring Topology)**:
    1.  **3850S1** [G1/0/1] <--> [G1/0/1] **3850S2**
    2.  **3850S2** [G1/0/2] <--> [G0/1] **2960S-2**
    3.  **2960S-2** [G0/2] <--> [G0/2] **2960S-1**
    4.  **2960S-1** [G0/1] <--> [G1/0/2] **3850S1**
*   **Trunks**: All inter-switch links should be configured as 802.1Q Trunks.

## Why VTP before STP?
*   **VTP (Layer 2 Management)**: Automatically synchronizes the VLAN database. While not strictly required for STP to function, it ensures that all switches "know" about the same VLANs, allowing STP to build a loop-free tree for each one consistently.
*   **STP (Layer 2 Loop Prevention)**: Runs independently for each VLAN (PVST+). By setting up VTP first, we ensure the infrastructure is ready before we start injecting traffic into new VLANs.

---

## Configuration Steps

### Phase 1: Pre-Connection Configuration (Standalone)
*Perform these steps on each switch via the management network BEFORE connecting the inter-switch cables.*

#### 1. Device Reset & Basic VTP
```ios
# On all switches
conf t
hostname 3850S1  # (Match your inventory: 3850S1, 3850S2, 2960S-1, 2960S-2)

# Set VTP Domain and Password
vtp domain CCNA
vtp password cisco

# Set Mode
# On 3850S1:
vtp mode server
# On others:
vtp mode client

# Pre-configure Trunk ports
interface range g1/0/1 - 2  # (Use correct port numbers for each switch)
  switchport trunk encapsulation dot1q
  switchport mode trunk
exit
```

#### 2. VLAN Creation (On VTP Server ONLY)
```ios
# On 3850S1
vlan 10
  name Sales
vlan 20
  name Engineering
```

---

### Phase 2: Physical Connectivity & Trunking
*Connect the inter-switch cables according to the Ring Topology.*

1.  **3850S1 [G1/0/1]** <--> **[G1/0/1] 3850S2**
2.  **3850S2 [G1/0/2]** <--> **[G0/1] 2960S-2**
3.  **2960S-2 [G0/2]** <--> **[G0/2] 2960S-1**
4.  **2960S-1 [G0/1]** <--> **[G1/0/2] 3850S1**

---

### Phase 3: Post-Connection Optimization (STP)
*Fine-tune the topology now that the links are active.*

#### 1. STP Root Election
```ios
# Root Primary (3850S1)
conf t
spanning-tree vlan 1,10,20 root primary

# Root Secondary (3850S2)
conf t
spanning-tree vlan 1,10,20 root secondary
```

#### 2. Wireshark Monitoring (Optional)
```ios
# On 3850S1
monitor session 1 source interface g1/0/1 both
monitor session 1 destination interface g1/0/10
```

---

## Validation & Monitoring

1.  **Verify VTP Sync**: `show vlan brief` on Client switches (VLAN 10/20 should appear).
2.  **Verify Trunks**: `show interfaces trunk` (Status should be "trunking").
3.  **Verify STP**: `show spanning-tree vlan 10`
    *   3850S1 should say: `"This bridge is the root"`
    *   Find the **Blocking (BLK)** port in the ring (usually on one of the 2960S switches).

### Real-Time Monitoring
```bash
python3 scripts/monitor_stp.py --vlan 10
```

## Cleanup
```bash
python3 scripts/restore_ssh.py
```
