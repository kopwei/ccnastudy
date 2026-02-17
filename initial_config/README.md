# Initial Configuration

This guide covers the base setup for Cisco switches in the lab environment, including local user management, management port configuration, and AAA Radius authentication.

## 1. Local User Management
Configure a local administrative user for emergency access or standalone management.

```ios
conf t
# Create a local user with highest privilege level
username admin privilege 15 secret cisco_password

# Set the enable secret
enable secret cisco_enable_secret
```

## 2. Management Port Configuration (VLAN 1)
Configure the management IP address on the default VLAN.

```ios
conf t
interface vlan 1
 ip address 192.168.2.x 255.255.255.0  # Replace x with device IP
 no shutdown
exit

# Configure the default gateway
ip default-gateway 192.168.2.1
```

## 3. AAA Radius Authentication
Centrally manage switch access using a Radius server.

### Radius Server Setup (daloRADIUS)
We use [daloradius-docker](https://github.com/kopwei/daloradius-docker) as our Radius server.

#### Create Profile (Group)
1.  Log into daloRADIUS web interface.
2.  Go to **Management** -> **Profiles** -> **New Profile**.
3.  **Profile Name**: `cisco_admin`
4.  **Profile Submit**.

#### Add Vendor/Attributes for Cisco Privilege 15
1.  In the `cisco_admin` profile, go to **Attributes**.
2.  **Vendor**: `Cisco`
3.  **Attribute**: `Cisco-AVPair`
4.  **Value**: `shell:priv-lvl=15`
5.  **Type**: `Reply`

#### Add User
1.  Go to **Management** -> **Users** -> **New User**.
2.  **Username**: `labuser`, **Password**: `labpassword`, **Profile**: `cisco_admin`.

### Cisco Switch Configuration (CLI)
```ios
conf t
# Enable AAA
aaa new-model

# Define Radius Server
radius server DALORADIUS
 address ipv4 192.168.2.100 auth-port 1812 acct-port 1813
 key cisco_radius_secret

# Create AAA Methods
# "group radius local" means: Try Radius first, fallback to local database if Radius is unreachable
aaa authentication login default group radius local
aaa authorization exec default group radius local 
aaa authorization console

# Apply to VTY lines
line vty 0 15
 login authentication default
 authorization exec default
 transport input ssh
exit
```
