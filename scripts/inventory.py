# Device Inventory
# Shared by restore_ssh.py and restore_serial.py

DEVICES = [
    {
        'device_type': 'cisco_ios',
        'host': '192.168.2.11',
        'base_config': 'router_891.cfg',
        'name': 'Router 891'
    },
    {
        'device_type': 'cisco_ios',
        'host': '192.168.2.35',
        'base_config': 'switch_3560cx.cfg',
        'name': 'Switch 3560CX'
    },
    {
        'device_type': 'cisco_ios',
        'host': '192.168.2.29',
        'base_config': 'switch_2960cx.cfg',
        'name': 'Switch 2960CX'
    },
    {
        'device_type': 'cisco_ios',
        'host': '192.168.2.21',
        'base_config': 'switch_2960s.cfg',
        'name': 'Switch 2960S-1'
    },
    {
        'device_type': 'cisco_ios',
        'host': '192.168.2.22',
        'base_config': 'switch_2960s.cfg',
        'name': 'Switch 2960S-2'
    }
]
