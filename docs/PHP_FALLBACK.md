# PHP Fallback Documentation

## 📁 Script Location

The `fallback.php` script is located in `docs/php/fallback.php`.

## 🔄 Purpose

The PHP fallback mechanism allows handling of rejected values by the eedomus API. When a value is rejected, the Python client can call this PHP script as a fallback to transform or map the value before retrying.

## 📋 Features

- Direct API calls to eedomus
- Simple and lightweight
- Error handling
- Parameter validation

## 🚀 Deployment

### Step 1: Copy the script

Copy `docs/php/fallback.php` to your eedomus box:

```bash
scp docs/php/fallback.php user@eedomus-box:/var/www/html/eedomus_fallback/
```

### Step 2: Configure the script

Make sure the script is accessible via HTTP and has proper permissions:

```bash
chmod 755 /var/www/html/eedomus_fallback/fallback.php
```

### Step 3: Configure the integration

In your Home Assistant configuration:

1. Enable PHP fallback in the integration settings
2. Set the script URL (e.g., `http://your-eedomus-box/eedomus_fallback/fallback.php`)
3. Configure the timeout if needed

## 📖 Script Parameters

The script accepts the following parameters:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `device_id` | string | ID of the device | `123456` |
| `value` | string | Value to set | `on` |

## 🔧 Configuration Options

In `configuration.yaml` or integration settings:

```yaml
eedomus:
  php_fallback_enabled: true
  php_fallback_script_name: "eedomus_fallback"
  php_fallback_timeout: 5
```

## 📝 Usage Example

When a value is rejected by the eedomus API:

1. The Python client detects the rejection
2. The client calls the PHP fallback script with the device ID and value
3. The PHP script attempts to set the value via the local eedomus API
4. The result is returned to the Python client

## 🛠️ Troubleshooting

### Script not found

- Verify the script is in the correct location on your eedomus box
- Check file permissions
- Ensure the web server has access to the script

### Connection errors

- Verify the script URL is correct
- Check network connectivity between Home Assistant and eedomus box
- Test the script URL in a browser

### API errors

- Check the eedomus API logs
- Verify the device ID exists
- Ensure the value is valid for the device type

## 📚 See Also

- [Main README](../README.md)
- [Integration Documentation](../docs/)
- [Eedomus API Documentation](https://doc.eedomus.com/)