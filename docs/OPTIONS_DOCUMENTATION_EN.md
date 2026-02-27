# 📖 Eedomus Integration Configuration Options Documentation

This document explains each parameter available in the eedomus integration configuration interface.

## 🔧 Main Parameters

### api_host
**Type**: String (IP Address)
**Example**: `192.168.1.100`

The local IP address of your eedomus box. This address allows Home Assistant to communicate directly with your box to retrieve device states and send commands.

**Where to find it**:
- In your eedomus box web interface
- Section "Network" or "System Information"

**Example value**: `192.168.1.100`

---

### api_user
**Type**: String (Username)
**Example**: `your_email@example.com`

Your eedomus account API username. This username is required to authenticate requests sent to the eedomus box.

**Where to find it**:
1. Log in to your eedomus box web interface
2. Go to "My Account" > "API Credentials"
3. Copy the API username

**Important**: This username is different from your regular login email.

---

### api_secret
**Type**: String (Password)
**Example**: `your_api_password`

The API password associated with your eedomus account. This field is secured and masked in the interface.

**Where to find it**:
- In the same section as the API username ("My Account" > "API Credentials")

**Important**: This password is different from your regular login password.

---

### enable_api_eedomus
**Type**: Boolean
**Default value**: `True`

Enables or disables polling of your eedomus box local APIs. When enabled, Home Assistant can:
- Retrieve device states (sensors, actuators, etc.)
- Send commands to devices
- Synchronize states between eedomus and Home Assistant

**Recommendation**: Keep this option enabled for normal integration operation.

---

### enable_api_proxy
**Type**: Boolean
**Default value**: `False`

Enables the API proxy that allows your eedomus box to query Home Assistant and directly manipulate Home Assistant entities. This option enables:
- Triggering Home Assistant automations from eedomus scenarios
- Acting on Home Assistant entities from your eedomus box
- Integrating Home Assistant devices into eedomus scenarios

**Use cases**:
- Create an eedomus scenario that turns on a Home Assistant light
- Trigger a Home Assistant automation from an eedomus detector

---

### scan_interval
**Type**: Integer (seconds)
**Default value**: `300` (5 minutes)
**Recommended range**: `60-600`

Determines how frequently Home Assistant polls your eedomus box to update device states.

**Optimization**:
- **Short interval** (60-120s): Better responsiveness, but increases box load
- **Long interval** (300-600s): Less load, but less frequent updates
- **Recommended balance**: 300 seconds (5 minutes) for most installations

**Note**: Some devices (lights, switches) use webhooks for instant updates and don't depend on this interval.

---

### http_request_timeout
**Type**: Integer (seconds)
**Default value**: `10`
**Recommended range**: `5-30`

Determines the maximum wait time for an eedomus API response before considering the request failed.

**When to adjust**:
- **Increase** (15-30s): If your network is slow or unstable
- **Decrease** (5-10s): If you want faster failure detection

**Positioning**: This parameter is now placed right below `scan_interval` for better logical organization, as both are related to API requests.

---

### enable_set_value_retry
**Type**: Boolean
**Default value**: `True`

Enables automatic retry functionality when sending a value to a device fails (e.g., unauthorized value).

**How it works**:
1. First attempt with the requested value
2. If fails, uses the closest allowed value
3. Maximum number of attempts defined by `max_retries`

**Recommendation**: Keep enabled for better compatibility with devices having value constraints.

---

### max_retries
**Type**: Integer
**Default value**: `3`
**Recommended range**: `1-5`

Maximum number of attempts to send a value to a device in case of initial failure.

**Example**: If you try to set brightness to 45% but the device only accepts 0%, 25%, 50%, 75%, 100%, the integration will try:
1. 45% (fails)
2. 50% (closest allowed value)

---

### enable_webhook
**Type**: Boolean
**Default value**: `True`

Enables webhooks for bidirectional communication between eedomus and Home Assistant. Allows:
- Instant state refresh
- Triggering Home Assistant actions from eedomus
- More responsive integration

---

### api_proxy_disable_security
**Type**: Boolean
**Default value**: `False`

**⚠️ Use with caution**

Disables source IP address verification for API Proxy requests. Can be useful for:
- Local testing
- Allowing other local network machines

**Risk**: Disabling this security may expose your installation to unauthorized requests.

---

### php_fallback_enabled
**Type**: Boolean
**Default value**: `False`

Enables the use of a PHP script to bypass certain eedomus API limitations, particularly for setting values not listed in default options.

**Requires**: A working PHP web server on the same host as Home Assistant.

---

### php_fallback_script_name
**Type**: String
**Default value**: `"fallback.php"`

Name of the PHP script used for fallback. Must be placed in a directory accessible by your web server.

---

### php_fallback_timeout
**Type**: Integer (seconds)
**Default value**: `5`

Maximum wait time for the PHP fallback script response.

---

## 🎯 Best Practices

1. **Start with default values** for most parameters
2. **Adjust scan_interval** based on your responsiveness needs and box load
3. **Enable advanced options** (webhook, API proxy) only if needed
4. **Monitor logs** after changes to detect issues
5. **Test changes** one by one to identify impacts

## 📚 Additional Documentation

For more information about the eedomus integration:
- [Official Documentation](https://github.com/Dan4Jer/hass-eedomus)
- [Home Assistant Forum](https://community.home-assistant.io/)
- [GitHub Issues](https://github.com/Dan4Jer/hass-eedomus/issues)

---

*Automatically generated documentation - Last updated: 2026*
