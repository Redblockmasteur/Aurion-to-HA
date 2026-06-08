# Mauria Calendar Integration for Home Assistant

This integration allows you to fetch and display your **Mauria calendar** events in Home Assistant.

## Features
- **UI Configuration**: Add the integration via the Home Assistant UI.
- **Authentication**: Securely store your Mauria credentials.
- **Calendar Events**: Fetch and display events from the Mauria API.
- **Automatic Updates**: Regularly poll the API for new events.

---

## Installation

### Method 1: HACS (Recommended)
1. Add this repository as a custom repository in HACS.
2. Install the integration via HACS.
3. Restart Home Assistant.

### Method 2: Manual
1. Copy the `custom_components/mauria_calendar` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

---

## Configuration

1. **Add the Integration**:
   - Go to **Settings > Devices & Services** in Home Assistant.
   - Click **Add Integration** and search for **Mauria Calendar**.
   - Enter your **Mauria username and password** when prompted.

2. **Configure Options (Optional)**:
   - After setup, you can adjust the **update interval** (default: 30 minutes).

---

## Sensor Attributes

The integration creates a sensor with the following attributes:

| Attribute | Description |
|-----------|-------------|
| `events` | List of calendar events (JSON array) |
| `last_updated` | Timestamp of the last update |

---

## Example Usage

### Automations

You can create automations based on calendar events. For example:

```yaml
automation:
  - alias: "Notify on new Mauria event"
    trigger:
      - platform: state
        entity_id: sensor.mauria_calendar_your_username
    action:
      - service: notify.notify
        data:
          message: "New event in Mauria calendar!"
```

### Templates

Extract event details using templates:

```yaml
sensor:
  - platform: template
    sensors:
      next_mauria_event:
        value_template: >
          {% if state_attr('sensor.mauria_calendar_your_username', 'events') | length > 0 %}
            {{ state_attr('sensor.mauria_calendar_your_username', 'events')[0].title }}
          {% else %}
            No events
          {% endif %}
```

---

## Troubleshooting

### Authentication Failed
- Verify your **username and password** are correct.
- Ensure your Mauria account has **API access enabled**.

### Connection Error
- Check your **internet connection**.
- Verify the Mauria API is **online** (https://api.mauria.app).

### No Events Showing
- Ensure your Mauria account has **calendar events**.
- Check the **update interval** in the integration options.

---

## Development

### Testing
1. Place the `custom_components/mauria_calendar` folder in your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration via the UI.

### Logging
Enable debug logging for this integration:

```yaml
logger:
  default: info
  logs:
    custom_components.mauria_calendar: debug
```

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## Credits

- **Author**: [Redblockmasteur](https://github.com/Redblockmasteur)
- **API**: [MauriaApp API-v2](https://github.com/MauriaApp/API-v2)
