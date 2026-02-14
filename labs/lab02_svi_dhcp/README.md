# Lab 02: Inter-VLAN Routing (SVI) & DHCP

## Purpose
In this lab, we will upgrade our Layer 2 network to a **Layer 3** network. We will configure the core switch (`3850S1`) to route traffic between VLANs using **Switch Virtual Interfaces (SVIs)** and serve IP addresses via **DHCP**.

## Study Points
*   **Layer 3 Switching**: Enabling IP routing on a switch.
*   **SVI (Switch Virtual Interface)**: Configuring Layer 3 interfaces for VLANs.
*   **DHCP Server**: Configuring a Cisco IOS device as a DHCP server.
*   **Inter-VLAN Routing Verification**: Pinging between different VLANs.

## Topology
*   **Physical**: Same as Lab 01 (Ring Topology).
*   **Logical**:
    *   **3850S1**: Acts as the "Core" Router and Gateway.
    *   **VLAN 10 (Sales)**: `192.168.10.0/24`, Gateway: `.1`
    *   **VLAN 20 (Engineering)**: `192.168.20.0/24`, Gateway: `.1`

## Configuration Steps

### Phase 1: Layer 2 Infrastructure (Prepare the Foundation)
*Since Lab 01 cleanup removed all VLANs and Trunks, we must rebuild the Layer 2 network first.*

#### 1. Configure VTP and Trunks (On All Switches)
```ios
# On 3850S1, 3850S2, 2960S-1, 2960S-2
conf t
vtp domain CCNA
vtp password cisco
vtp mode client      # (Set 3850S1 to 'server' in next step)

# Re-enable Trunking on Inter-switch links
interface range g1/0/25 - 26  # (Adjust for 2960S ports: g1/0/1-2)
  switchport mode trunk
exit
```

#### 2. Create VLANs (On VTP Server 3850S1 Only)
```ios
# On 3850S1
vtp mode server
vlan 10
  name Sales
vlan 20
  name Engineering
exit
```

### Phase 2: Layer 3 Configuration (The New Stuff)

#### 1. Enable Layer 3 Routing (On 3850S1 ONLY)
By default, the 3850 acts as a Layer 2 switch. We must enable routing globally.

```ios
# On 3850S1
conf t
ip routing
```

### 2. Configure SVIs (Gateways)
Create the Layer 3 interfaces that will serve as Default Gateways for the endpoints.

```ios
# On 3850S1
interface Vlan10
  description Gateway for Sales
  ip address 192.168.10.1 255.255.255.0
  no shutdown
exit

interface Vlan20
  description Gateway for Engineering
  ip address 192.168.20.1 255.255.255.0
  no shutdown
exit
```

### 3. Configure DHCP Server
Configure the 3850S1 to assign IP addresses to devices in these VLANs.

```ios
# On 3850S1
ip dhcp excluded-address 192.168.10.1 192.168.10.9
ip dhcp excluded-address 192.168.20.1 192.168.20.9

ip dhcp pool Sales_Pool
  network 192.168.10.0 255.255.255.0
  default-router 192.168.10.1
  dns-server 8.8.8.8
exit

ip dhcp pool Eng_Pool
  network 192.168.20.0 255.255.255.0
  default-router 192.168.20.1
  dns-server 8.8.8.8
exit
```

### 4. Client Verification Setup
Since we don't have PCs, we will use the **Access Switches (2960s)** as clients to test routing.

**Configure 2960S-1 as a "Sales" client (VLAN 10):**
```ios
# On 2960S-1
conf t
interface Vlan10
  ip address 192.168.10.11 255.255.255.0
  no shutdown
  exit
ip default-gateway 192.168.10.1
```

**Configure 2960S-2 as an "Engineering" client (VLAN 20):**
```ios
# On 2960S-2
conf t
interface Vlan20
  ip address 192.168.20.22 255.255.255.0
  no shutdown
  exit
ip default-gateway 192.168.20.1
```

## Verification
1.  **Ping Gateway**:
    *   From 2960S-1: `ping 192.168.10.1` (Should be !!!!!)
    *   From 2960S-2: `ping 192.168.20.1` (Should be !!!!!)

2.  **Ping Across VLANs (The Real Test)**:
    *   From **2960S-1 (VLAN 10)**, ping **2960S-2 (VLAN 20)**:
    *   `ping 192.168.20.22`
    *   **Success** means 3850S1 is correctly routing packets between VLAN 10 and VLAN 20.

## Cleanup
When finished:
```bash
python3 scripts/restore_ssh.py
```
