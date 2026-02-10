#!/usr/bin/env python3
"""
Lab Cleanup Script - Reset Cisco devices to clean state between labs.

Dynamically removes lab configurations (VLANs, routing, ACLs, STP, etc.)
while preserving SSH, user accounts, and management connectivity.

Usage:
  python3 restore_ssh.py                    # Clean all devices
  python3 restore_ssh.py --devices 891 3560 # Clean specific devices
"""
import getpass
import re
import sys
import os
import time
import argparse
from netmiko import ConnectHandler

try:
    from inventory import DEVICES
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from inventory import DEVICES

# SSH key path
SSH_KEY_PATH = os.path.expanduser('~/.ssh/id_rsa_cisco')


def connect_to_device(device, password=None, use_keys=True):
    """Connect to a device with SSH key + password fallback."""
    base_params = {
        'device_type': device['device_type'],
        'host': device['host'],
        'username': 'admin',
        'timeout': 30,
        'conn_timeout': 20,
        'disabled_algorithms': {'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']},
    }

    net_connect = None
    if use_keys:
        key_params = base_params.copy()
        key_params['use_keys'] = True
        key_params['key_file'] = SSH_KEY_PATH
        key_params['allow_agent'] = True
        if password:
            key_params['password'] = password
            key_params['secret'] = password
        try:
            net_connect = ConnectHandler(**key_params)
        except Exception:
            print(f"  SSH key auth failed, falling back to password...")

    if net_connect is None and password:
        pwd_params = base_params.copy()
        pwd_params['password'] = password
        pwd_params['secret'] = password
        net_connect = ConnectHandler(**pwd_params)

    if net_connect is None:
        raise Exception("No authentication method available")

    net_connect.enable()
    return net_connect


def get_vlans_to_remove(net_connect, mgmt_vlan=99):
    """Get list of non-default VLANs to remove."""
    output = net_connect.send_command("show vlan brief")
    vlans_to_remove = []
    # Always preserve: VLAN 1 (default), management VLAN, and reserved VLANs
    preserved_vlans = {1, 1002, 1003, 1004, 1005}
    if mgmt_vlan:
        preserved_vlans.add(mgmt_vlan)
    for line in output.splitlines():
        match = re.match(r'^(\d+)\s+\S+', line.strip())
        if match:
            vlan_id = int(match.group(1))
            if vlan_id not in preserved_vlans:
                vlans_to_remove.append(vlan_id)
    return vlans_to_remove


def get_mgmt_vlan_ports(net_connect, mgmt_vlan=99):
    """Find physical ports assigned to the management VLAN."""
    if not mgmt_vlan:
        return set()
    output = net_connect.send_command("show vlan brief")
    mgmt_ports = set()
    in_mgmt_vlan = False
    for line in output.splitlines():
        # Match VLAN line: "99   Management                       active    Gi0/10, Gi0/11"
        match = re.match(r'^(\d+)\s+\S+\s+\S+\s+(.*)', line)
        if match:
            vlan_id = int(match.group(1))
            in_mgmt_vlan = (vlan_id == mgmt_vlan)
            if in_mgmt_vlan:
                ports_str = match.group(2).strip()
                if ports_str:
                    for port in ports_str.split(','):
                        mgmt_ports.add(port.strip().lower())
        elif in_mgmt_vlan and line.startswith(' '):
            # Continuation line with more ports
            for port in line.strip().split(','):
                port = port.strip().lower()
                if port:
                    mgmt_ports.add(port)
        else:
            in_mgmt_vlan = False
    return mgmt_ports


def expand_intf_name(short_name):
    """Expand abbreviated interface names (Gi0/1 -> gigabitethernet0/1)."""
    prefixes = {
        'gi': 'gigabitethernet',
        'fa': 'fastethernet',
        'te': 'tengigabitethernet',
        'et': 'ethernet',
        'po': 'port-channel',
    }
    lower = short_name.lower()
    for abbr, full in prefixes.items():
        if lower.startswith(abbr) and not lower.startswith(full):
            return full + lower[len(abbr):]
    return lower


def get_interfaces_to_reset(net_connect, mgmt_interface, mgmt_vlan=99):
    """Get list of non-management interfaces to reset.
    
    Preserves:
    - Management SVI (Vlan99, Vlan1)
    - Physical ports in the management VLAN
    - The management interface itself
    """
    # Find ports in management VLAN dynamically
    mgmt_ports = get_mgmt_vlan_ports(net_connect, mgmt_vlan)
    if mgmt_ports:
        print(f"  Management VLAN {mgmt_vlan} ports (preserved): {mgmt_ports}")
    
    # Build preserved set (all lowercase for comparison)
    preserved = {mgmt_interface.lower(), 'vlan1'}
    if mgmt_vlan:
        preserved.add(f'vlan{mgmt_vlan}'.lower())
    # Add expanded names of management ports
    for port in mgmt_ports:
        preserved.add(expand_intf_name(port))
    
    output = net_connect.send_command("show ip interface brief")
    interfaces = []
    for line in output.splitlines():
        match = re.match(r'^(\S+)\s+', line.strip())
        if match:
            intf = match.group(1)
            # Skip header lines
            if intf.lower() in ('interface', 'any'):
                continue
            # Skip all preserved interfaces
            if intf.lower() in preserved:
                continue
            if expand_intf_name(intf) in preserved:
                continue
            interfaces.append(intf)
    return interfaces


def get_routing_protocols(net_connect):
    """Detect configured routing protocols."""
    protocols = []
    output = net_connect.send_command("show running-config | section ^router")
    for line in output.splitlines():
        match = re.match(r'^router\s+(\S+)\s*(.*)', line.strip())
        if match:
            proto = match.group(1)
            instance = match.group(2).strip()
            protocols.append(f"router {proto} {instance}".strip())
    return protocols


def get_acls(net_connect):
    """Get list of configured ACLs."""
    acls = []
    output = net_connect.send_command("show running-config | include ^ip access-list|^access-list")
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("ip access-list"):
            # ip access-list extended MY_ACL
            acls.append(f"no {line}")
        elif line.startswith("access-list"):
            # access-list 10 permit ...
            match = re.match(r'^access-list\s+(\d+)', line)
            if match:
                acl_num = match.group(1)
                entry = f"no access-list {acl_num}"
                if entry not in acls:
                    acls.append(entry)
    return acls


def get_static_routes(net_connect, mgmt_gateway='192.168.2.1'):
    """Get non-default static routes. Preserve default route and management gateway."""
    routes = []
    output = net_connect.send_command("show running-config | include ^ip route")
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("ip route"):
            continue
        # Preserve default route (0.0.0.0 0.0.0.0)
        if "0.0.0.0 0.0.0.0" in line:
            continue
        # Preserve any route pointing to management gateway
        if mgmt_gateway and mgmt_gateway in line:
            continue
        routes.append(f"no {line}")
    return routes


def get_nat_config(net_connect):
    """Get NAT configuration commands to remove."""
    cmds = []
    output = net_connect.send_command("show running-config | include ^ip nat")
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("ip nat"):
            cmds.append(f"no {line}")
    return cmds


def get_dhcp_pools(net_connect):
    """Get DHCP pool names to remove."""
    pools = []
    output = net_connect.send_command("show running-config | include ^ip dhcp pool")
    for line in output.splitlines():
        match = re.match(r'^ip dhcp pool\s+(\S+)', line.strip())
        if match:
            pools.append(f"no ip dhcp pool {match.group(1)}")
    return pools


def get_port_channels(net_connect):
    """Get port-channel interfaces."""
    channels = []
    output = net_connect.send_command("show running-config | include ^interface Port-channel")
    for line in output.splitlines():
        match = re.match(r'^interface\s+(Port-channel\d+)', line.strip())
        if match:
            channels.append(match.group(1))
    return channels


def cleanup_switch(net_connect, device):
    """Clean up a switch (L2 or L3)."""
    mgmt_intf = device.get('mgmt_interface', 'Vlan99')
    mgmt_vlan = device.get('mgmt_vlan', 99)
    cleanup_cmds = []

    # 1. Remove non-default VLANs (preserves VLAN 1 and management VLAN)
    vlans = get_vlans_to_remove(net_connect, mgmt_vlan)
    if vlans:
        print(f"  Removing {len(vlans)} VLANs: {vlans}")
        for vlan_id in vlans:
            cleanup_cmds.append(f"no vlan {vlan_id}")

    # 2. Get interfaces to reset (preserves management interface)
    interfaces = get_interfaces_to_reset(net_connect, mgmt_intf, mgmt_vlan)

    # 3. Remove port-channels first (before resetting member interfaces)
    port_channels = get_port_channels(net_connect)
    if port_channels:
        print(f"  Removing port-channels: {port_channels}")
        for pc in port_channels:
            cleanup_cmds.append(f"no interface {pc}")

    # 4. Reset interfaces to default
    if interfaces:
        print(f"  Resetting {len(interfaces)} interfaces to default")
        for intf in interfaces:
            cleanup_cmds.append(f"default interface {intf}")

    # 5. Remove STP customizations
    stp_output = net_connect.send_command("show running-config | include ^spanning-tree")
    if stp_output.strip():
        print(f"  Removing STP customizations")
        for line in stp_output.splitlines():
            line = line.strip()
            if line.startswith("spanning-tree"):
                cleanup_cmds.append(f"no {line}")

    # 6. L3 switch specific: remove routing protocols, ACLs
    if device.get('role') == 'l3_switch':
        protocols = get_routing_protocols(net_connect)
        if protocols:
            print(f"  Removing routing protocols: {protocols}")
            for proto in protocols:
                cleanup_cmds.append(f"no {proto}")

        acls = get_acls(net_connect)
        if acls:
            print(f"  Removing {len(acls)} ACLs")
            cleanup_cmds.extend(acls)

        static_routes = get_static_routes(net_connect)
        if static_routes:
            print(f"  Removing {len(static_routes)} static routes")
            cleanup_cmds.extend(static_routes)

    # 7. Remove DHCP snooping
    dhcp_output = net_connect.send_command("show running-config | include ^ip dhcp snooping")
    if dhcp_output.strip():
        print(f"  Removing DHCP snooping config")
        cleanup_cmds.append("no ip dhcp snooping")

    return cleanup_cmds


def cleanup_router(net_connect, device):
    """Clean up a router."""
    mgmt_intf = device.get('mgmt_interface', 'FastEthernet0')
    cleanup_cmds = []

    # 1. Remove routing protocols
    protocols = get_routing_protocols(net_connect)
    if protocols:
        print(f"  Removing routing protocols: {protocols}")
        for proto in protocols:
            cleanup_cmds.append(f"no {proto}")

    # 2. Remove ACLs
    acls = get_acls(net_connect)
    if acls:
        print(f"  Removing {len(acls)} ACLs")
        cleanup_cmds.extend(acls)

    # 3. Remove NAT config
    nat_cmds = get_nat_config(net_connect)
    if nat_cmds:
        print(f"  Removing NAT configuration")
        cleanup_cmds.extend(nat_cmds)

    # 4. Remove DHCP pools
    dhcp_cmds = get_dhcp_pools(net_connect)
    if dhcp_cmds:
        print(f"  Removing DHCP pools")
        cleanup_cmds.extend(dhcp_cmds)

    # 5. Remove static routes (preserves default route and management gateway)
    static_routes = get_static_routes(net_connect)
    if static_routes:
        print(f"  Removing {len(static_routes)} static routes")
        cleanup_cmds.extend(static_routes)

    # 6. Reset non-management interfaces
    interfaces = get_interfaces_to_reset(net_connect, mgmt_intf)
    if interfaces:
        print(f"  Resetting {len(interfaces)} interfaces to default")
        for intf in interfaces:
            cleanup_cmds.append(f"default interface {intf}")

    return cleanup_cmds


def cleanup_device(device, password=None, use_keys=True):
    """Clean up a single device."""
    print(f"\n{'='*60}")
    print(f"Cleaning {device['name']} ({device['host']})")
    print(f"{'='*60}")

    try:
        net_connect = connect_to_device(device, password, use_keys)
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return False

    try:
        # Generate cleanup commands based on device role
        role = device.get('role', 'l2_switch')
        if role == 'router':
            cleanup_cmds = cleanup_router(net_connect, device)
        else:
            cleanup_cmds = cleanup_switch(net_connect, device)

        if not cleanup_cmds:
            print(f"  ✓ {device['name']} is already clean - nothing to do")
            net_connect.disconnect()
            return True

        # Execute cleanup
        print(f"\n  Executing {len(cleanup_cmds)} cleanup commands...")
        output = net_connect.send_config_set(cleanup_cmds, cmd_verify=False)
        print(output)

        # Re-detect prompt (hostname may have changed if was set during lab)
        net_connect.set_base_prompt()

        # Save configuration
        print("  Saving configuration...")
        save_output = net_connect.send_command("write memory", read_timeout=15)
        print(f"  {save_output.strip()}")

        print(f"  ✓ Successfully cleaned {device['name']}")
        net_connect.disconnect()
        return True

    except Exception as e:
        print(f"  ✗ Failed to clean {device['name']}: {e}")
        try:
            net_connect.disconnect()
        except Exception:
            pass
        return False


def main():
    parser = argparse.ArgumentParser(description='Clean up Cisco lab devices between exercises')
    parser.add_argument('--devices', nargs='+', help='Filter devices by name (e.g., 891 3560)')
    args = parser.parse_args()

    # Filter devices if specified
    if args.devices:
        target_devices = [d for d in DEVICES if any(f.lower() in d['name'].lower() for f in args.devices)]
        if not target_devices:
            print(f"No devices found matching: {args.devices}")
            print(f"Available: {[d['name'] for d in DEVICES]}")
            return
    else:
        target_devices = DEVICES

    print("╔══════════════════════════════════════════════════════════╗")
    print("║        CCNA/CCNP Lab Cleanup Script                    ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"\nTarget devices: {[d['name'] for d in target_devices]}")
    print("\nThis will remove lab configs (VLANs, routing, ACLs, STP, etc.)")
    print("SSH, users, and management connectivity will be PRESERVED.")

    # Check SSH key
    has_ssh_key = os.path.exists(SSH_KEY_PATH)
    if has_ssh_key:
        print(f"\n✓ SSH key found: {SSH_KEY_PATH}")
        auth_choice = input("Use SSH key authentication? (y/n, default: y): ").strip().lower()
        use_keys = auth_choice != 'n'
    else:
        print(f"\nNo SSH key found. Using password authentication.")
        use_keys = False

    password = getpass.getpass("\nEnter admin password (needed for fallback/enable): ")

    confirm = input("\nProceed with cleanup? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Aborted.")
        return

    success = 0
    for device in target_devices:
        if cleanup_device(device, password, use_keys):
            success += 1

    print(f"\n{'='*60}")
    print(f"CLEANUP COMPLETE: {success}/{len(target_devices)} devices")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
