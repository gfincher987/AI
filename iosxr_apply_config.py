#!/usr/bin/env python3
"""
iosxr_apply_config.py

Simple utility to connect to a Cisco IOS‑XR device and apply a configuration file.

Features:
- Prompt for connection info (host, username, password) or accept CLI args
- Optional dry-run mode (shows commands without applying)
- Optional running-config backup to a local file before applying
- Applies config using Netmiko and runs a `commit` on IOS‑XR

Notes:
- This script uses Netmiko (pip install netmiko)
- Test in a lab before running in production.
"""

import argparse
import getpass
import sys
import time
from netmiko import ConnectHandler

def read_config_file(path, variables=None):
    """Read config file and optionally substitute variables."""
    with open(path, 'r') as f:
        lines = [line.rstrip('\n') for line in f if line.strip() != '']
    
    if variables:
        # Substitute variables in format ${VAR_NAME} or {VAR_NAME}
        substituted_lines = []
        for line in lines:
            new_line = line
            for var_name, var_value in variables.items():
                # Support both ${VAR} and {VAR} formats
                new_line = new_line.replace(f"${{{var_name}}}", str(var_value))
                new_line = new_line.replace(f"{{{var_name}}}", str(var_value))
            substituted_lines.append(new_line)
        return substituted_lines
    
    return lines

def save_backup(connection, host):
    try:
        print("Saving running-config backup...")
        output = connection.send_command("show running-config")
        filename = f"{host}_running_config_backup_{int(time.time())}.txt"
        with open(filename, 'w') as f:
            f.write(output)
        print(f"Backup saved to {filename}")
        return filename
    except Exception as e:
        print(f"Failed to save backup: {e}")
        return None

def apply_config(connection, config_lines, dry_run=False):
    """Apply a list of config lines to an IOS-XR device and commit."""
    if dry_run:
        print("Dry-run mode - the following commands would be sent:")
        for l in config_lines:
            print(l)
        return {'success': True, 'output': 'DRY_RUN'}

    # Enter configure mode and send commands
    try:
        print("Entering configuration mode and sending config lines...")
        # Use send_config_set but avoid exiting config mode so we can commit explicitly
        cfg_output = connection.send_config_set(config_lines, exit_config_mode=False, enter_config_mode='configure')

        # Commit the candidate configuration
        print("Committing configuration...")
        commit_output = connection.send_command('commit', expect_string=r'#', delay_factor=2)

        # Exit configuration mode
        connection.send_command('exit')

        return {'success': True, 'output': cfg_output + '\n' + commit_output}
    except Exception as e:
        return {'success': False, 'output': str(e)}

def main():
    parser = argparse.ArgumentParser(description='Apply an IOS-XR configuration file to a device')
    parser.add_argument('--host', '-H', required=True, help='Device IP/hostname')
    parser.add_argument('--username', '-u', help='Username (will prompt if omitted)')
    parser.add_argument('--password', '-p', help='Password (will prompt if omitted)')
    parser.add_argument('--port', type=int, default=22, help='SSH port (default 22)')
    parser.add_argument('--config', '-c', required=True, help='Path to config file to apply')
    parser.add_argument('--dry-run', action='store_true', help='Show commands only, do not apply')
    parser.add_argument('--backup', action='store_true', help='Save running-config backup before applying')
    parser.add_argument('--fast-cli', action='store_true', help='Enable Netmiko fast_cli (default: disabled)')
    parser.add_argument('--var', action='append', help='Variable substitution in format VAR=value (can be used multiple times)')
    parser.add_argument('--hostname', help='Device hostname for CN variable (shortcut for --var HOSTNAME=value)')

    args = parser.parse_args()

    username = args.username or input('Username: ')
    password = args.password or getpass.getpass('Password: ')

    # Build variables dictionary
    variables = {}
    if args.var:
        for var_assignment in args.var:
            if '=' not in var_assignment:
                print(f"Invalid variable format: {var_assignment}. Use VAR=value")
                sys.exit(1)
            var_name, var_value = var_assignment.split('=', 1)
            variables[var_name] = var_value
    
    # Add hostname as HOSTNAME variable if provided
    if args.hostname:
        variables['HOSTNAME'] = args.hostname
    
    # Auto-detect some common variables from device info
    if 'HOSTNAME' not in variables:
        variables['HOSTNAME'] = args.host  # Default to IP/hostname if not specified

    try:
        config_lines = read_config_file(args.config, variables if variables else None)
    except Exception as e:
        print(f"Failed to read config file: {e}")
        sys.exit(1)

    if variables:
        print(f"Using variables: {variables}")

    device = {
        'device_type': 'cisco_xr',
        'host': args.host,
        'username': username,
        'password': password,
        'port': args.port,
        'fast_cli': args.fast_cli is True,
    }

    print(f"Connecting to {args.host}...")
    try:
        conn = ConnectHandler(**device)
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(2)

    backup_file = None
    if args.backup and not args.dry_run:
        backup_file = save_backup(conn, args.host)

    result = apply_config(conn, config_lines, dry_run=args.dry_run)

    if result['success']:
        print('Configuration applied successfully' if not args.dry_run else 'Dry-run complete')
    else:
        print(f"Configuration failed: {result['output']}")

    # Save apply output to a log file
    try:
        logname = f"{args.host}_apply_log_{int(time.time())}.txt"
        with open(logname, 'w') as lf:
            lf.write('--- Config applied (or dry-run) ---\n')
            for l in config_lines:
                lf.write(l + '\n')
            lf.write('\n--- Result ---\n')
            lf.write(result['output'])
        print(f"Apply log saved to {logname}")
    except Exception as e:
        print(f"Failed to write log file: {e}")

    conn.disconnect()

if __name__ == '__main__':
    main()
