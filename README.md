# IOS-XR Configuration Script

A Python script to apply configuration files to Cisco IOS-XR devices with variable substitution support.

## Dependencies

```bash
pip install netmiko
```

## Features

- Connect to IOS-XR devices via SSH
- Apply configuration files with variable substitution
- Dry-run mode (show commands without applying)
- Automatic backup of running configuration
- Commit configuration changes
- Logging of applied configuration and results

## Usage

### Basic Usage
```bash
python3 iosxr_apply_config.py --host 10.225.253.60 --config aaa_tls_cfg_template_vars.txt --username admin
```

### With Variable Substitution
```bash
python3 iosxr_apply_config.py \
  --host 10.225.253.60 \
  --config aaa_tls_cfg_template_vars.txt \
  --username admin \
  --var HOSTNAME=brc-8201-1.tmo.svs.com \
  --var DEVICE_IP=10.225.253.167 \
  --backup
```

### Dry Run (Test Mode)
```bash
python3 iosxr_apply_config.py \
  --host 10.225.253.60 \
  --config aaa_tls_cfg_template_vars.txt \
  --username admin \
  --var HOSTNAME=brc-8201-1.tmo.svs.com \
  --var DEVICE_IP=10.225.253.167 \
  --dry-run
```

### Using Hostname Shortcut
```bash
python3 iosxr_apply_config.py \
  --host 10.225.253.60 \
  --config aaa_tls_cfg_template_vars.txt \
  --username admin \
  --hostname brc-8201-1.tmo.svs.com \
  --var DEVICE_IP=10.225.253.167
```

## Variable Substitution

The script supports variable substitution in configuration files using `{VARIABLE_NAME}` format.

### Example Template File
```
crypto ca trustpoint SVS_KF_07OCT2025
 subject-name C=US,ST=NC,L=RTP,O=Cisco,OU=SVS,CN={HOSTNAME}
 subject-alternative-name IP:{DEVICE_IP},DNS:{HOSTNAME}
```

### Common Variables
- `{HOSTNAME}` - Device hostname/FQDN
- `{DEVICE_IP}` - Device management IP address
- Custom variables via `--var VARNAME=value`

## Command Line Options

- `--host` / `-H` - Device IP or hostname (required)
- `--config` / `-c` - Path to configuration file (required)
- `--username` / `-u` - SSH username (prompts if not provided)
- `--password` / `-p` - SSH password (prompts if not provided)
- `--var` - Variable substitution (format: VAR=value, can be used multiple times)
- `--hostname` - Shortcut to set HOSTNAME variable
- `--dry-run` - Show commands without applying them
- `--backup` - Save running-config backup before applying
- `--port` - SSH port (default: 22)
- `--fast-cli` - Enable Netmiko fast CLI mode

## Safety Notes

⚠️ **Important Safety Recommendations:**

1. **Always test in a lab environment first**
2. **Use `--dry-run` to preview changes**
3. **Use `--backup` to save current configuration**
4. **Have console access available in case of connectivity issues**
5. **Test rollback procedures beforehand**

## Output Files

The script creates the following files:
- `{hostname}_running_config_backup_{timestamp}.txt` - Backup of current config (if --backup used)
- `{hostname}_apply_log_{timestamp}.txt` - Log of applied configuration and results

## Example Workflow

1. **Prepare template**: Edit `aaa_tls_cfg_template_vars.txt` with variables
2. **Test with dry-run**:
   ```bash
   python3 iosxr_apply_config.py --host 10.225.253.60 --config aaa_tls_cfg_template_vars.txt --username admin --hostname brc-8201-1.tmo.svs.com --var DEVICE_IP=10.225.253.167 --dry-run
   ```
3. **Apply with backup**:
   ```bash
   python3 iosxr_apply_config.py --host 10.225.253.60 --config aaa_tls_cfg_template_vars.txt --username admin --hostname brc-8201-1.tmo.svs.com --var DEVICE_IP=10.225.253.167 --backup
   ```

## Troubleshooting

- **Connection issues**: Check SSH connectivity and credentials
- **Config errors**: Review the apply log file for detailed error messages
- **Variable issues**: Use `--dry-run` to verify variable substitution
- **Commit failures**: Check device logs and ensure configuration is valid