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
    1.  **3850S1** [G1/0/25] <--> [G1/0/25] **3850S2**
    2.  **3850S2** [G1/0/26] <--> [G1/0/1] **2960S-1**
    3.  **2960S-1** [G1/0/2] <--> [G1/0/1] **2960S-2**
    4.  **2960S-2** [G1/0/2] <--> [G1/0/26] **3850S1** (Last Link to close loop)
*   **Trunks**: All inter-switch links should be configured as 802.1Q Trunks.

## Why VTP before STP?
*   **VTP (Layer 2 Management)**: Automatically synchronizes the VLAN database. While not strictly required for STP to function, it ensures that all switches "know" about the same VLANs, allowing STP to build a loop-free tree for each one consistently.
*   **STP (Layer 2 Loop Prevention)**: Runs independently for each VLAN (PVST+). By setting up VTP first, we ensure the infrastructure is ready before we start injecting traffic into new VLANs.

---

## Configuration Steps

---

### Phase 1: Pre-Connection Configuration (Standalone)
*Perform these steps on each switch via the management network BEFORE connecting the inter-switch cables.*

#### 1. Device Reset & Basic VTP
```ios
# On all switches
conf t
hostname 3850S1  # (Repeat for 3850S2, 2960S-1, 2960S-2)

# Set VTP Domain and Password
vtp domain CCNA
vtp password cisco

# Set Mode
# On 3850s:
vtp mode server
# On others:
vtp mode client

# Pre-configure Trunk ports
# On 3850s: Using G1/0/25 and G1/0/26 (centered for physical alignment)
interface range g1/0/25 - 26
  switchport mode trunk
exit

# On 2960S: Using G1/0/1 and G1/0/2 (as specified by user)
interface range g1/0/1 - 2
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

### Phase 2: Physical Connectivity & Trunking (Observation Ready)

#### 1. Establish the "Linear" Path (NO LOOP YET)
*Connect these 3 cables first. This creates a chain based on your rack layout.*
1.  **3850S1 [G1/0/25]** <--> **[G1/0/25] 3850S2** (Horizontal Top)
2.  **3850S2 [G1/0/26]** <--> **[G1/0/1] 2960S-1** (Vertical Right)
3.  **2960S-1 [G1/0/2]** <--> **[G1/0/1] 2960S-2** (Horizontal Bottom)

#### 2. Verify Open Path
*   Check `show interfaces trunk` on all switches.
*   Run the monitor: `python3 scripts/monitor_stp.py --vlan 10`. You should see all ports in `FWD` state.

---

### Phase 3: STP Convergence & Optimization

#### 1. The "Moment of Convergence" (TRIGGER THE LOOP)
*Prepare your Wireshark and Monitor script, then connect the final vertical cable on the left:*
*   **Final Cable**: **2960S-2 [G1/0/2]** <--> **[G1/0/26] 3850S1** (Vertical Left)
*   **Observation**: Watch the monitor script. You will see the new link go through `LIS` -> `LRN` -> `BLK`. This takes ~30-50 seconds with standard STP.

#### 2. STP Root Election (Manual Override)
*Once the loop is stable, force the topology down to the core.*
```ios
# Root Primary (3850S1)
conf t
spanning-tree vlan 1,10,20 root primary

# Root Secondary (3850S2)
conf t
spanning-tree vlan 1,10,20 root secondary
```

#### 3. Wireshark Monitoring (Detailed Analysis)
```ios
# Configure SPAN on 3850S1 (Assuming PC is on G1/0/30)
conf t
monitor session 1 source interface g1/0/25 both
monitor session 1 destination interface g1/0/30
```

---

## Validation & Monitoring

1.  **Verify VTP Sync**: `show vlan brief` on Client switches (VLAN 10/20 should appear).
2.  **Verify STP Topology**: `show spanning-tree vlan 10`
    *   3850S1: `"This bridge is the root"`
    *   Identify the **Alternate/Blocking (ALT/BLK)** port. Note which switch "lost" the election and blocked its port.
    *   Check for **TCN** traps in your terminal if any.

### Real-Time Monitoring
```bash
python3 scripts/monitor_stp.py --vlan 10
```

## Cleanup
```bash
python3 scripts/restore_ssh.py
```

### Real-Time Monitoring
```bash
python3 scripts/monitor_stp.py --vlan 10
```

## Cleanup
```bash
python3 scripts/restore_ssh.py
```
