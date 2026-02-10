# Device Inventory
# Shared by all automation scripts
# role: 'router', 'l3_switch', or 'l2_switch'
# mgmt_interface: the management interface to preserve during cleanup
# mgmt_vlan: the management VLAN to preserve (never deleted)

DEVICES = [
    {
        'device_type': 'cisco_ios',
        'host': '192.168.2.11',
        'name': 'Router 891',
        'role': 'router',
        'mgmt_interface': 'FastEthernet8',
    },
    {
        'device_type': 'cisco_ios',
        'host': '192.168.2.35',
        'name': 'Switch 3560CX',
        'role': 'l3_switch',
        'mgmt_interface': 'Vlan99',
        'mgmt_vlan': 99,
    },
    {
        'device_type': 'cisco_ios',
        'host': '192.168.2.29',
        'name': 'Switch 2960CX',
        'role': 'l2_switch',
        'mgmt_interface': 'Vlan99',
        'mgmt_vlan': 99,
    },
    {
        'device_type': 'cisco_ios',
        'host': '192.168.2.21',
        'name': 'Switch 2960S-1',
        'role': 'l2_switch',
        'mgmt_interface': 'Vlan99',
        'mgmt_vlan': 99,
    },
    {
        'device_type': 'cisco_ios',
        'host': '192.168.2.22',
        'name': 'Switch 2960S-2',
        'role': 'l2_switch',
        'mgmt_interface': 'Vlan1',
    }
]
